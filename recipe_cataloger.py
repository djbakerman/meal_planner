#!/usr/bin/env python3
"""
Recipe Cataloger - Extracts and catalogs recipes from cookbook images
Uses Ollama vision models or Claude API to analyze cookbook pages and extract structured recipe data.

Supports multiple cookbook formats:
- Simple layouts (1-2 recipes per page)
- Complex layouts with photos, stories, multi-page recipes
- Various metadata: nutrition, prep time, macros, dietary info
"""

import json
import os
import sys
import base64
import argparse
import re
import tempfile
from pathlib import Path
from datetime import datetime
import requests
from typing import Optional, List, Dict, Any

from backend import config, llm, image as img_utils


def preprocess_image_for_text(image_path: str) -> Optional[str]:
    """Delegate to backend."""
    return img_utils.preprocess_image_for_text(image_path)


# Helper functions delegated to backend
# encode_image_to_base64 and get_image_media_type removed, used directly from img_utils or inside analyze_image


def analyze_image(image_path: str, prompt: str, model: str, api_key: str = None, 
                  backup_model: str = None) -> Optional[str]:
    """
    Analyze an image using either Claude API or Ollama based on the model name.
    """
    # Check if it's a Claude model
    is_claude = llm.is_claude_model(model)
    
    if is_claude:
        if not api_key:
            print("Error: Claude API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key")
            return None
        
        # Check file size - Claude has 5MB limit on the BASE64 encoded image
        file_size = os.path.getsize(image_path)
        # Base64 encoded size approx file_size * 4/3
        estimated_base64_size = int(file_size * 4 / 3)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        
        if estimated_base64_size >= max_size:
            if backup_model:
                print(f"  ⚠️  File too large for Claude ({file_size / 1024 / 1024:.1f}MB -> ~{estimated_base64_size / 1024 / 1024:.1f}MB base64), using backup model: {backup_model}")
                # Fallback to Ollama
                try:
                    image_b64 = img_utils.encode_image_to_base64(image_path)
                    return llm.query_ollama(prompt, backup_model, images=[image_b64])
                except Exception as e:
                    print(f"Error encoding image for backup model: {e}")
                    return None
            else:
                print(f"  ⚠️  File too large for Claude ({file_size / 1024 / 1024:.1f}MB -> ~{estimated_base64_size / 1024 / 1024:.1f}MB base64). Use --backup-model to specify fallback.")
                return None
        
        # Encode image for Claude
        try:
            image_b64 = img_utils.encode_image_to_base64(image_path)
            media_type = img_utils.get_image_media_type(image_path)
            images = [{"media_type": media_type, "data": image_b64}]
            
            return llm.query_claude(prompt, model, api_key, images=images)
        except Exception as e:
            print(f"Error preparing image for Claude: {e}")
            return None
            
    else:
        # Use Ollama
        try:
            image_b64 = img_utils.encode_image_to_base64(image_path)
            return llm.query_ollama(prompt, model, images=[image_b64])
        except Exception as e:
            print(f"Error preparing image for Ollama: {e}")
            return None


def parse_json_response(response: str) -> Optional[dict]:
    """Safely parse JSON from model response."""
    return llm.parse_json_response(response)


def analyze_extraction_failure(image_path: str, model: str, api_key: str, 
                                classification: dict, extraction_result: dict) -> dict:
    """
    When a recipe is detected but not properly extracted, ask Claude to diagnose why.
    
    Args:
        image_path: Path to the image
        model: Model to use (should be Claude for best results)
        api_key: API key
        classification: The classification result
        extraction_result: The failed/partial extraction result
    
    Returns:
        Diagnostic analysis dict
    """
    
    # Build context about what happened
    context = f"""
CONTEXT: Our recipe extraction script detected a recipe page but failed to properly extract the recipe(s).

CLASSIFICATION RESULT:
- Page type: {classification.get('type')}
- Recipes visible: {classification.get('recipe_names_visible', [])}
- Has recipe start: {classification.get('has_recipe_start')}
- Has continuation: {classification.get('has_recipe_continuation')}

EXTRACTION RESULT:
- Complete recipes extracted: {len(extraction_result.get('recipes', []))}
- Partial recipe: {extraction_result.get('partial_recipe', {}).get('name', 'None') if extraction_result.get('partial_recipe') else 'None'}
- Recipe names found: {[r.get('name') for r in extraction_result.get('recipes', [])]}

THE PROBLEM: We detected recipe(s) but extracted {len(extraction_result.get('recipes', []))} complete recipe(s).
"""

    prompt = f"""{context}

Please analyze this cookbook page image and help diagnose the extraction failure:

1. WHAT RECIPES ARE VISIBLE?
   - List all recipe titles/names you can see
   - For each: is it complete (has title, ingredients, AND instructions) or partial?

2. WHY MIGHT EXTRACTION HAVE FAILED?
   - Is there text from a PREVIOUS recipe continuing at the top? (e.g., step "5." before any title)
   - Are there multiple recipes side-by-side that might have been missed?
   - Is the layout unusual in any way?
   - Are ingredients or instructions cut off?

3. WHAT SHOULD THE CORRECT EXTRACTION BE?
   - For each complete recipe visible, provide:
     - Name
     - Number of ingredients
     - Number of instruction steps
     - Any special notes (continuation, partial, etc.)

4. RECOMMENDATIONS:
   - What specific changes to our prompts or logic might help?
   - Are there edge cases we're not handling?

Respond in JSON format:
{{
    "recipes_visible": [
        {{
            "name": "recipe name",
            "is_complete": true/false,
            "has_continuation_from_previous": true/false,
            "continues_to_next_page": true/false,
            "ingredient_count": number,
            "instruction_count": number,
            "notes": "any observations"
        }}
    ],
    "failure_reasons": ["list of likely reasons extraction failed"],
    "continuation_text_at_top": "any text that appears to continue from previous page, or null",
    "layout_description": "description of the page layout",
    "recommendations": ["list of specific recommendations to fix extraction"],
    "correct_extraction_summary": "what the extraction SHOULD have returned"
}}
"""

    response = analyze_image(image_path, prompt, model, api_key)
    
    if response:
        parsed = parse_json_response(response)
        if parsed:
            return parsed
        else:
            return {
                "error": "Failed to parse diagnostic response",
                "raw_response": response[:1000]
            }
    
    return {"error": "Failed to get diagnostic response"}


def print_diagnostic_report(diagnostic: dict):
    """Print a formatted diagnostic report."""
    print("\n" + "=" * 60)
    print("🔍 EXTRACTION FAILURE DIAGNOSTIC REPORT")
    print("=" * 60)
    
    # Recipes visible
    recipes = diagnostic.get("recipes_visible", [])
    print(f"\n📋 Recipes Detected ({len(recipes)}):")
    for r in recipes:
        status = "✅ Complete" if r.get("is_complete") else "⚠️ Partial"
        cont_from = " [continues from prev]" if r.get("has_continuation_from_previous") else ""
        cont_to = " [continues to next]" if r.get("continues_to_next_page") else ""
        print(f"   • {r.get('name', 'Unknown')} - {status}{cont_from}{cont_to}")
        print(f"     Ingredients: {r.get('ingredient_count', '?')}, Steps: {r.get('instruction_count', '?')}")
        if r.get("notes"):
            print(f"     Notes: {r.get('notes')}")
    
    # Continuation text
    cont_text = diagnostic.get("continuation_text_at_top")
    if cont_text:
        print(f"\n⚡ Continuation from previous page:")
        print(f"   \"{cont_text[:100]}{'...' if len(str(cont_text)) > 100 else ''}\"")
    
    # Failure reasons
    reasons = diagnostic.get("failure_reasons", [])
    if reasons:
        print(f"\n❌ Likely Failure Reasons:")
        for reason in reasons:
            print(f"   • {reason}")
    
    # Layout
    layout = diagnostic.get("layout_description")
    if layout:
        print(f"\n📐 Layout: {layout}")
    
    # Recommendations
    recs = diagnostic.get("recommendations", [])
    if recs:
        print(f"\n💡 Recommendations:")
        for rec in recs:
            print(f"   • {rec}")
    
    # Summary
    summary = diagnostic.get("correct_extraction_summary")
    if summary:
        print(f"\n✅ Expected Result: {summary}")
    
    print("\n" + "=" * 60)


def classify_page(image_path: str, model: str, api_key: str = None, backup_model: str = None) -> dict:
    """
    Classify what type of cookbook page this is with detailed analysis.
    
    Returns dict with:
    - type: 'chapter', 'recipe', 'recipe_partial', 'article', 'photo', 'other'
    - has_recipe_start: bool - does a new recipe start on this page?
    - has_recipe_continuation: bool - does a recipe continue from previous page?
    - page_numbers: list of page numbers if visible
    """
    prompt = """Analyze this cookbook page image carefully. Determine what type of content it shows.

Respond in this exact JSON format:
{
    "type": "one of: chapter, recipe, recipe_partial, article, photo, other",
    "has_recipe_start": true/false (does a NEW recipe title and ingredients START on this page?),
    "has_recipe_continuation": true/false (see below for how to determine this),
    "recipe_names_visible": ["list any recipe titles/names you can see"],
    "page_numbers": [list of page numbers visible, as integers] or [],
    "total_pages": total book pages if shown (e.g., from "page 5 of 200") or null,
    "confidence": "high/medium/low"
}

HOW TO DETECT has_recipe_continuation:
Set this to TRUE if you see ANY of these signs that content continues from a previous page:
- An instruction step that does NOT start with "1" at the very top of the page (e.g., seeing "5." or "3." at the top)
- Text that starts mid-sentence at the top
- Instructions appearing ABOVE or BEFORE a recipe title
- A step number > 1 appearing before any recipe title on the page

Example: If you see "5. Bake in oven for 15 minutes. Serve." at the top of the page, that's a continuation!

Page type definitions:
- "chapter": A chapter/section title page listing recipe names (table of contents style)
- "recipe": A page with complete or substantial recipe content (title, ingredients, AND instructions)
- "recipe_partial": A page showing ONLY part of a recipe (just instructions continuing, or just a photo with recipe name)
- "article": Text-heavy page with stories, tips, or information but NO recipe ingredients/instructions
- "photo": Primarily a food photo with minimal or no recipe text
- "other": Anything else (intro pages, blank, etc.)

Important: 
- A recipe page must have BOTH ingredients AND at least some instructions visible
- If you only see a photo and recipe title (no ingredients), that's "photo" or "recipe_partial"
- If you see instructions but no ingredients (continued from previous page), that's "recipe_partial"
- A page can have BOTH has_recipe_continuation=true AND has_recipe_start=true (previous recipe ends, new one starts)

Respond with ONLY the JSON, no other text."""

    response = analyze_image(image_path, prompt, model, api_key, backup_model)
    
    result = {
        "type": "other",
        "has_recipe_start": False,
        "has_recipe_continuation": False,
        "recipe_names_visible": [],
        "page_numbers": [],
        "total_pages": None,
        "confidence": "low"
    }
    
    if response:
        parsed = parse_json_response(response)
        if parsed:
            result.update(parsed)
        else:
            # Fallback: try to determine type from text response
            response_lower = response.lower()
            if "chapter" in response_lower:
                result["type"] = "chapter"
            elif "recipe" in response_lower:
                result["type"] = "recipe"
            elif "article" in response_lower:
                result["type"] = "article"
            elif "photo" in response_lower:
                result["type"] = "photo"
    
    return result


def extract_chapter_info(image_path: str, model: str, api_key: str = None, backup_model: str = None) -> dict:
    """Extract chapter information and recipe list from a chapter/TOC page."""
    
    prompt = """Analyze this cookbook chapter or table of contents page. Extract the following information and respond in valid JSON format only:

{
    "chapter_number": "the chapter number if visible (e.g., 'Chapter Two', '2', etc.) or null",
    "chapter_title": "the chapter title/name (e.g., 'Breakfast', 'Leafy Salads', 'Appetizers') or null",
    "recipe_list": ["list of recipe names mentioned on this page - extract ALL of them exactly as written"],
    "notes": "any other relevant information about this chapter"
}

Important:
- Extract ALL recipe names you can see listed
- Keep recipe names EXACTLY as written (preserve capitalization)
- The chapter title is usually the largest text or heading
- If you can't determine something, use null
- Respond with ONLY the JSON, no other text"""

    response = analyze_image(image_path, prompt, model, api_key, backup_model)
    
    if response:
        parsed = parse_json_response(response)
        if parsed:
            return parsed
        else:
            return {
                "chapter_number": None,
                "chapter_title": None,
                "recipe_list": [],
                "notes": f"Failed to parse response: {response[:200]}",
                "raw_response": response
            }
    
    return {"error": "Failed to analyze image"}


def extract_recipes(image_path: str, model: str, current_chapter: dict = None, 
                   pending_recipe: dict = None, max_retries: int = 2, api_key: str = None,
                   backup_model: str = None, classification: dict = None) -> dict:
    """
    Extract recipe details from a recipe page.
    
    Args:
        image_path: Path to image
        model: Ollama model name
        current_chapter: Current chapter context
        pending_recipe: Partial recipe from previous page that may continue here
        max_retries: Number of retry attempts with different prompts
        api_key: API key for Claude models
        backup_model: Fallback model for large files
        classification: Page classification result (used to know expected recipe count)
    
    Returns dict with:
        - recipes: list of complete recipes
        - partial_recipe: recipe that continues to next page (if any)
    """
    
    chapter_context = ""
    if current_chapter and current_chapter.get("chapter_title"):
        chapter_context = f"These recipes are from the chapter: {current_chapter.get('chapter_title', 'Unknown')}\n"
    
    continuation_context = ""
    if pending_recipe:
        continuation_context = f"""
NOTE: A recipe "{pending_recipe.get('name', 'Unknown')}" may continue from the previous page.
If you see instructions continuing without a recipe title, they belong to this recipe.
"""

    # Multiple prompts - try different approaches if first fails to get all recipes
    prompts = [
        # Primary prompt - emphasizes scanning BOTH sides
        f"""{chapter_context}{continuation_context}IMPORTANT: This cookbook page may show MULTIPLE recipes. Some pages have 2, 3, 4, or even 5 short recipes.
Scan the ENTIRE image carefully from TOP to BOTTOM on BOTH the LEFT and RIGHT sides.

Extract ALL recipes shown. For EACH recipe provide this JSON format:
{{
    "recipes": [
        {{
            "name": "exact recipe name/title",
            "is_complete": true/false (see COMPLETION RULES below),
            "is_continuation": true/false (see CONTINUATION RULES below),
            "meal_type": "breakfast/lunch/dinner/any (see classification rules below)",
            "dish_role": "main/side/sub_recipe (see classification rules below)",
            "serves": "serving size (e.g., '4', '6-8') or null",
            "prep_time": "prep time if shown (e.g., '10 minutes') or null",
            "cook_time": "cooking time if shown or null", 
            "total_time": "total time if shown or null",
            "calories": "calorie number only, e.g., '143' or '350' or null",
            "protein": "protein grams, e.g., '8g' or '24g' or null",
            "carbs": "carb grams, e.g., '21g' or '15g' or null",
            "fat": "fat grams, e.g., '3g' or '12g' or null",
            "dietary_info": ["ONLY dietary restriction tags like 'DAIRY-FREE', 'VEGAN', 'GLUTEN-FREE', 'NUT-FREE', 'VEGETARIAN' - NOT macros/calories"],
            "description": "the intro paragraph describing the recipe, if any",
            "ingredients": [
                "ingredient 1 with amount",
                "ingredient 2 with amount"
            ],
            "sub_recipes": [
                {{
                    "name": "name of sub-recipe like 'Sriracha Vinaigrette' or 'Barbecue Ranch Dressing'",
                    "ingredients": ["ingredient 1", "ingredient 2"],
                    "instructions": ["preparation steps for the sub-recipe"]
                }}
            ],
            "instructions": [
                "step 1",
                "step 2"
            ],
            "tips": ["any tips, variations, DIY notes, or substitutions mentioned"],
            "nutrition_full": "full nutrition line as a string, e.g., '143 CALORIES | 8 GRAMS PROTEIN | 21 GRAMS CARBOHYDRATES | 3 GRAMS FAT'"
        }}
    ],
    "has_continuation": true/false (does a recipe continue onto the NEXT page?)
}}

MEAL TYPE CLASSIFICATION (meal_type):
- "breakfast": Traditional morning foods - eggs, pancakes, waffles, oatmeal, breakfast burritos, bacon dishes, smoothie bowls
- "lunch": Midday foods - sandwiches, wraps, lighter salads, soups, quick meals
- "dinner": Evening/hearty meals - steaks, roasts, pasta mains, substantial proteins, hearty stews
- "any": Versatile dishes that work for multiple meals - many salads, grain bowls, some soups
Use your judgment based on ingredients, portion size, and traditional eating patterns (not what someone COULD eat, but what's typical).

DISH ROLE CLASSIFICATION (dish_role):
- "main": The primary dish/entrée - substantial, could be the star of the meal
- "side": Accompaniment - vegetables, slaws, smaller salads, side dishes
- "sub_recipe": A COMPONENT that goes into another recipe - dressings, vinaigrettes, sauces, marinades, spice blends, rubs
  (Note: If it's a dressing/sauce shown as part of a larger recipe, keep it in sub_recipes array AND classify the main recipe appropriately)

CRITICAL: 
- Scan BOTH the LEFT side AND RIGHT side of the image, TOP to BOTTOM
- There may be 1, 2, 3, 4, or even 5+ recipes visible - extract ALL of them
- Short recipes (just a few ingredients and steps) are common - don't skip them
- Look for recipe TITLES/HEADINGS - each heading marks a new recipe
- Include ALL ingredients for EACH recipe
- Look for VARIATION TIP, DIY, or SUBSTITUTION notes at the bottom
- dietary_info should ONLY contain tags like DAIRY-FREE, VEGAN, GLUTEN-FREE - NOT calories or macros
- Put calorie/protein/carb/fat numbers in their respective fields

SUB-RECIPES ARE CRITICAL - DO NOT MISS THEM:
- Sub-recipes are dressings, vinaigrettes, sauces, marinades shown WITHIN a main recipe
- They are often in COLORED BOXES or SHADED SECTIONS (gray, olive, tan backgrounds)
- They have their OWN name (e.g., "Cilantro-Lime Vinaigrette", "Kalamata Feta Vinaigrette", "Barbecue Ranch Dressing")
- They have their OWN ingredient list
- They may have their OWN instructions
- Put these in the "sub_recipes" array of the PARENT recipe, NOT as separate recipes
- Example: "Cilantro-Lime Avocado Shrimp Salad" should have sub_recipes: [{{name: "Cilantro-Lime Vinaigrette", ingredients: [...]}}]

COMPLETION RULES (is_complete):
Set is_complete=FALSE if ANY of these are true:
- Instructions are CUT OFF at the bottom of the page (sentence doesn't end, or no clear ending like "Serve" or "Enjoy")
- You see text going off the edge of the visible area
- The recipe clearly continues (e.g., "continued on next page")
- Instructions seem incomplete (e.g., batter is made but never baked)
Set is_complete=TRUE only if the recipe has a clear ending (final step like "Serve immediately", "Enjoy!", or a complete final instruction)

CONTINUATION RULES (is_continuation):
Set is_continuation=TRUE if ANY of these are true:
- The FIRST text you see is mid-instruction (not starting with step 1 or a title)
- Instructions at the TOP of the page don't start with "1."
- Text begins mid-sentence
- There's no recipe title/heading before the first instructions
Set is_continuation=FALSE if the recipe starts fresh with a title and step 1

Respond with ONLY valid JSON.""",

        # Retry prompt - more explicit about two-column layout
        f"""{chapter_context}This appears to be a TWO-COLUMN cookbook layout. 

LEFT COLUMN: Contains one recipe
RIGHT COLUMN: Contains another recipe

Extract BOTH recipes completely. Include:
- Recipe names (titles at top of each column)
- All ingredients listed under each recipe
- Any sub-recipes (dressings, sauces) shown in boxes
- Instructions numbered at bottom
- Tips/variations in colored text
- Macros: calories, protein, carbs, fat as SEPARATE fields (just the numbers)
- dietary_info: ONLY restriction tags like VEGAN, GLUTEN-FREE (NOT macros)

JSON format:
{{"recipes": [{{recipe1}}, {{recipe2}}], "has_continuation": false}}

Each recipe needs: name, meal_type (breakfast/lunch/dinner/any), dish_role (main/side/sub_recipe), serves, calories, protein, carbs, fat, dietary_info, ingredients, sub_recipes, instructions, tips.

Respond with ONLY JSON.""",

        # Third retry - for pages with large photos
        f"""{chapter_context}This page has a LARGE FOOD PHOTOGRAPH taking up significant space. IGNORE THE PHOTO COMPLETELY.

Focus ONLY on the TEXT areas of the page. Look for:
1. RECIPE TITLE - usually in large/bold text
2. INGREDIENTS LIST - look for measurements like cups, tablespoons, teaspoons, ounces, pounds
3. NUMBERED INSTRUCTIONS - steps 1, 2, 3, etc.
4. SERVING INFO - "Serves 4" or similar
5. NUTRITION INFO - calories, protein, carbs, fat (often at bottom)
6. PREP/COOK TIME - "Prep time: X minutes"

The recipe text might be in a SINGLE COLUMN next to the photo, or wrapped around it.

Extract the recipe in this JSON format:
{{
    "recipes": [
        {{
            "name": "exact recipe title",
            "meal_type": "breakfast/lunch/dinner/any",
            "dish_role": "main/side/sub_recipe", 
            "serves": "serving size",
            "prep_time": "prep time if shown",
            "cook_time": "cooking time if shown",
            "calories": "calorie number only",
            "protein": "protein grams",
            "carbs": "carb grams", 
            "fat": "fat grams",
            "dietary_info": ["DAIRY-FREE", "VEGAN", etc - only dietary tags],
            "ingredients": ["ingredient 1 with amount", "ingredient 2 with amount", ...],
            "instructions": ["step 1", "step 2", ...],
            "tips": ["any tips or variations"]
        }}
    ],
    "has_continuation": false
}}

READ ALL THE TEXT CAREFULLY - don't let the photo distract you. Respond with ONLY valid JSON.""",
    ]
    
    best_result = {"recipes": [], "partial_recipe": None}
    
    for attempt, prompt in enumerate(prompts[:max_retries + 1]):
        response = analyze_image(image_path, prompt, model, api_key, backup_model)
        
        if response:
            parsed = parse_json_response(response)
            if parsed:
                recipes = parsed.get("recipes", [])
                
                # Process this attempt if:
                # 1. We found more recipes than before, OR
                # 2. We still have 0 recipes (keep trying different prompts)
                current_count = len(best_result.get("recipes", []))
                if len(recipes) > current_count or current_count == 0:
                    # Process recipes
                    complete_recipes = []
                    partial = None
                    
                    for recipe in recipes:
                        # Add chapter info
                        if current_chapter:
                            recipe["chapter"] = current_chapter.get("chapter_title")
                            recipe["chapter_number"] = current_chapter.get("chapter_number")
                        
                        # Handle continuations
                        if recipe.get("is_continuation") and pending_recipe:
                            # Merge with pending recipe
                            merged = merge_recipes(pending_recipe, recipe)
                            if recipe.get("is_complete", True):
                                complete_recipes.append(merged)
                            else:
                                partial = merged
                        elif recipe.get("is_continuation") and not pending_recipe:
                            # Marked as continuation but no pending recipe - save it anyway
                            # This happens when a recipe looks like a continuation (e.g., step 5 at top)
                            # but we don't have the previous page
                            recipe["note"] = "Detected as continuation but no previous page context"
                            recipe["is_continuation"] = False  # Reset since we're treating it as standalone
                            if recipe.get("is_complete", True):
                                complete_recipes.append(recipe)
                            else:
                                partial = recipe
                        elif recipe.get("is_complete", True):
                            complete_recipes.append(recipe)
                        else:
                            partial = recipe
                    
                    # Only update best_result if we actually found something
                    # (or if this is our first attempt)
                    if len(complete_recipes) > 0 or partial is not None or attempt == 0:
                        best_result = {
                            "recipes": complete_recipes,
                            "partial_recipe": partial,
                            "attempt": attempt + 1
                        }
                    
                    # Determine expected recipe count from classification if available
                    expected_count = len(classification.get("recipe_names_visible", [])) if classification else 0
                    
                    # Only return early if we found ALL expected recipes (or 3+ if unknown)
                    # This prevents stopping too early on pages with many short recipes
                    found_count = len(complete_recipes) + (1 if partial else 0)
                    
                    if expected_count > 0:
                        # We know how many to expect - only return if we got them all
                        if found_count >= expected_count:
                            return best_result
                    else:
                        # Unknown expected count - be conservative, only return early if we found 3+
                        if len(complete_recipes) >= 3:
                            return best_result
    
    # If no recipes found, try with preprocessed image (enhanced contrast/sharpness)
    if not best_result.get("recipes") and img_utils.PIL_AVAILABLE:
        print("  🔄 Retrying with enhanced image preprocessing...")
        preprocessed_path = img_utils.preprocess_image_for_text(image_path)
        
        if preprocessed_path:
            try:
                # Use the photo-heavy prompt with preprocessed image
                photo_prompt = f"""{chapter_context}This page has a LARGE FOOD PHOTOGRAPH. IGNORE THE PHOTO - focus ONLY on TEXT.

Extract the recipe from the text areas. Look for:
- RECIPE TITLE (large/bold text) - DO NOT invent a title if you don't see one clearly
- INGREDIENTS (measurements: cups, tbsp, tsp, oz, lb)
- NUMBERED INSTRUCTIONS (1, 2, 3...)
- SERVES/SERVINGS info
- PREP TIME / COOK TIME
- NUTRITION (calories, protein, carbs, fat)

IMPORTANT: 
- Only extract recipes you can CLEARLY see on the page
- If you only see instructions without a title, this may be a CONTINUATION of a previous recipe
- DO NOT hallucinate or invent recipe names - if unsure, return empty recipes array
- If the page only shows continuation instructions (no title, no ingredients), return: {{"recipes": [], "has_continuation": true}}

JSON format:
{{
    "recipes": [{{
        "name": "recipe title - MUST be visible on page",
        "meal_type": "breakfast/lunch/dinner/any",
        "dish_role": "main/side/sub_recipe",
        "serves": "servings",
        "prep_time": "prep time",
        "cook_time": "cook time",
        "calories": "calories only",
        "protein": "protein grams",
        "carbs": "carb grams",
        "fat": "fat grams",
        "dietary_info": [],
        "ingredients": ["ingredient 1", "ingredient 2", ...],
        "instructions": ["step 1", "step 2", ...],
        "tips": []
    }}],
    "has_continuation": false
}}

Respond with ONLY valid JSON."""
                
                response = analyze_image(preprocessed_path, photo_prompt, model, api_key, backup_model)
                
                if response:
                    parsed = parse_json_response(response)
                    if parsed and parsed.get("recipes"):
                        recipes = parsed["recipes"]
                        complete_recipes = []
                        
                        for recipe in recipes:
                            if current_chapter:
                                recipe["chapter"] = current_chapter.get("chapter_title")
                                recipe["chapter_number"] = current_chapter.get("chapter_number")
                            recipe["preprocessed"] = True
                            complete_recipes.append(recipe)
                        
                        best_result = {
                            "recipes": complete_recipes,
                            "partial_recipe": None,
                            "attempt": "preprocessed"
                        }
                        print(f"  ✅ Preprocessing helped! Extracted {len(complete_recipes)} recipe(s)")
            finally:
                # Clean up temp file
                if os.path.exists(preprocessed_path):
                    os.remove(preprocessed_path)
    
    # If no recipes found through normal parsing, return empty
    if not best_result.get("recipes"):
        best_result["recipes"] = []
    
    return best_result


def merge_recipes(recipe1: dict, recipe2: dict) -> dict:
    """Merge two partial recipes (e.g., from consecutive pages)."""
    merged = recipe1.copy()
    
    # Extend lists
    for key in ["ingredients", "instructions", "tips", "dietary_info"]:
        if key in recipe2 and recipe2[key]:
            if key not in merged:
                merged[key] = []
            merged[key].extend(recipe2[key])
    
    # Extend sub_recipes
    if "sub_recipes" in recipe2 and recipe2["sub_recipes"]:
        if "sub_recipes" not in merged:
            merged["sub_recipes"] = []
        merged["sub_recipes"].extend(recipe2["sub_recipes"])
    
    # Take non-null values from recipe2 for scalar fields
    for key in ["serves", "prep_time", "cook_time", "total_time", "calories", 
                "protein", "carbs", "fat", "description", "nutrition_full"]:
        if recipe2.get(key) and not merged.get(key):
            merged[key] = recipe2[key]
    
    # Mark as complete if recipe2 is complete
    merged["is_complete"] = recipe2.get("is_complete", True)
    merged["is_continuation"] = False  # Reset since we've merged
    
    # Track source images
    if "source_images" not in merged:
        merged["source_images"] = [merged.get("source_image", "unknown")]
    if recipe2.get("source_image"):
        merged["source_images"].append(recipe2["source_image"])
    
    return merged


def extract_partial_recipe(image_path: str, model: str, pending_recipe: dict, api_key: str = None,
                          backup_model: str = None) -> dict:
    """Extract continuation of a recipe from a partial page."""
    
    prompt = f"""This page shows the CONTINUATION of a recipe from the previous page.
The recipe name is: "{pending_recipe.get('name', 'Unknown')}"

IMPORTANT: This is NOT a new recipe - it is the ENDING/CONTINUATION of an existing recipe.
Look for:
1. Any remaining ingredient list items (if ingredients continued from previous page)
2. Remaining instruction steps (might start with step 3, 4, 5, etc. - NOT step 1)
3. Any tips, variations, DIY notes, or substitutions mentioned at the bottom
4. Per serving nutrition information

DO NOT:
- Create a new recipe name
- Treat this as a new recipe
- Include content from other recipes that might be on the page

Respond in JSON:
{{
    "additional_ingredients": ["any additional ingredients if the list continues"],
    "additional_instructions": ["step N", "step N+1", ... (continuing from where previous page left off)],
    "additional_tips": ["any tips, variations, DIY notes mentioned"],
    "nutrition_per_serving": "full nutrition line if shown",
    "is_complete": true/false (does this recipe fully end on this page, or continue further?)
}}

Only extract content that clearly belongs to the continuing recipe "{pending_recipe.get('name', 'Unknown')}".
If you see a completely different recipe title, ignore it - only extract the continuation content.
Respond with ONLY valid JSON."""

    response = analyze_image(image_path, prompt, model, api_key, backup_model)
    
    if response:
        parsed = parse_json_response(response)
        if parsed:
            # Merge into pending recipe
            if parsed.get("additional_ingredients"):
                if "ingredients" not in pending_recipe:
                    pending_recipe["ingredients"] = []
                pending_recipe["ingredients"].extend(parsed["additional_ingredients"])
            
            if parsed.get("additional_instructions"):
                if "instructions" not in pending_recipe:
                    pending_recipe["instructions"] = []
                pending_recipe["instructions"].extend(parsed["additional_instructions"])
            
            if parsed.get("additional_tips"):
                if "tips" not in pending_recipe:
                    pending_recipe["tips"] = []
                pending_recipe["tips"].extend(parsed["additional_tips"])
            
            if parsed.get("nutrition_per_serving"):
                pending_recipe["nutrition_full"] = parsed["nutrition_per_serving"]
            
            pending_recipe["is_complete"] = parsed.get("is_complete", True)
    
    return pending_recipe


def normalize_recipe_name(name: str) -> str:
    """Normalize a recipe name for matching."""
    # Lowercase, remove extra spaces, remove common punctuation
    normalized = name.lower().strip()
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized


def fuzzy_match_names(name1: str, name2: str, threshold: float = 0.85) -> bool:
    """
    Check if two recipe names are similar enough to be considered a match.
    Uses a simple character-based similarity ratio.
    
    Args:
        name1: First name to compare
        name2: Second name to compare  
        threshold: Minimum similarity ratio (0-1) to consider a match
    
    Returns:
        True if names are similar enough
    """
    n1 = normalize_recipe_name(name1)
    n2 = normalize_recipe_name(name2)
    
    # Exact match
    if n1 == n2:
        return True
    
    # One contains the other
    if n1 in n2 or n2 in n1:
        return True
    
    # Calculate similarity ratio (simple Levenshtein-like approach)
    # Using difflib's SequenceMatcher for simplicity
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, n1, n2).ratio()
    
    return ratio >= threshold


def reassign_unknown_chapters(catalog: dict) -> int:
    """
    Reassign recipes from "Unknown" chapter to correct chapters based on chapter recipe lists.
    
    Args:
        catalog: The recipe catalog to update
    
    Returns:
        Number of recipes reassigned
    """
    reassigned = 0
    
    # Build a lookup from recipe name -> chapter info
    chapter_lookup = {}
    for chapter in catalog.get("chapters", []):
        chapter_title = chapter.get("chapter_title", "Unknown")
        chapter_number = chapter.get("chapter_number")
        for listed_name in chapter.get("recipe_list", []):
            chapter_lookup[normalize_recipe_name(listed_name)] = {
                "chapter_title": chapter_title,
                "chapter_number": chapter_number
            }
    
    # Find recipes with "Unknown" or missing chapter and try to reassign
    for recipe in catalog.get("recipes", []):
        current_chapter = recipe.get("chapter", "")
        
        if not current_chapter or current_chapter.lower() == "unknown":
            recipe_name = recipe.get("name", "")
            
            # Try to find matching chapter from chapter lists
            for listed_normalized, chapter_info in chapter_lookup.items():
                if fuzzy_match_names(recipe_name, listed_normalized):
                    recipe["chapter"] = chapter_info["chapter_title"]
                    if chapter_info["chapter_number"]:
                        recipe["chapter_number"] = chapter_info["chapter_number"]
                    recipe["chapter_reassigned"] = True
                    reassigned += 1
                    break
    
    return reassigned


def upsert_recipes(catalog: dict, new_recipes: list, new_chapters: list = None, 
                   source_image: str = None) -> dict:
    """
    Upsert (update or insert) recipes into an existing catalog.
    
    - If a recipe with the same name exists, it gets updated
    - If it's new, it gets added
    - Rebuilds the index after changes
    
    Args:
        catalog: Existing catalog dictionary
        new_recipes: List of recipe dictionaries to upsert
        new_chapters: Optional list of chapter dictionaries to upsert
        source_image: Source image filename for logging
    
    Returns:
        Updated catalog with upsert log
    """
    if "recipes" not in catalog:
        catalog["recipes"] = []
    if "chapters" not in catalog:
        catalog["chapters"] = []
    if "upsert_log" not in catalog:
        catalog["upsert_log"] = []
    
    # Build lookup of existing recipes by normalized name (and fuzzy matches)
    existing_recipes = {}
    for i, recipe in enumerate(catalog["recipes"]):
        name = recipe.get("name", "")
        if name:
            normalized = normalize_recipe_name(name)
            existing_recipes[normalized] = i
    
    # Process new recipes
    added = 0
    updated = 0
    merged = 0
    
    for recipe in new_recipes:
        name = recipe.get("name", "")
        if not name:
            continue
            
        normalized = normalize_recipe_name(name)
        
        # Check for exact match first
        match_idx = existing_recipes.get(normalized)
        
        # If no exact match, try fuzzy matching
        if match_idx is None:
            for existing_normalized, idx in existing_recipes.items():
                if fuzzy_match_names(name, catalog["recipes"][idx].get("name", "")):
                    match_idx = idx
                    break
        
        if match_idx is not None:
            old_recipe = catalog["recipes"][match_idx]
            
            # Check if this looks like a continuation/partial that should be merged
            # Merge if: new recipe has more instructions OR old recipe seems incomplete
            old_instructions = len(old_recipe.get("instructions", []))
            new_instructions = len(recipe.get("instructions", []))
            old_ingredients = len(old_recipe.get("ingredients", []))
            new_ingredients = len(recipe.get("ingredients", []))
            
            # Determine if we should merge or replace
            should_merge = False
            
            # Case 1: Old recipe has ingredients but few instructions, new has more instructions
            if old_ingredients > 0 and old_instructions < 3 and new_instructions > old_instructions:
                should_merge = True
            
            # Case 2: New recipe has ingredients but few instructions, old has more instructions
            elif new_ingredients > 0 and new_instructions < 3 and old_instructions > new_instructions:
                should_merge = True
            
            # Case 3: Both have content, combine them (likely split across pages)
            elif old_instructions > 0 and new_instructions > 0 and old_ingredients > 0 and new_ingredients == 0:
                should_merge = True
            elif new_instructions > 0 and old_instructions > 0 and new_ingredients > 0 and old_ingredients == 0:
                should_merge = True
            
            if should_merge:
                # Merge the recipes
                merged_recipe = merge_recipes(old_recipe, recipe)
                merged_recipe["merged_from_sources"] = [
                    old_recipe.get("source_image", "unknown"),
                    recipe.get("source_image", source_image or "unknown")
                ]
                catalog["recipes"][match_idx] = merged_recipe
                merged += 1
                
                catalog["upsert_log"].append({
                    "action": "merged",
                    "recipe_name": name,
                    "source_image": source_image or recipe.get("source_image"),
                    "timestamp": datetime.now().isoformat(),
                    "previous_source": old_recipe.get("source_image"),
                    "note": f"Merged: old had {old_ingredients} ing/{old_instructions} steps, new had {new_ingredients} ing/{new_instructions} steps"
                })
            else:
                # Replace with newer version (more complete)
                catalog["recipes"][match_idx] = recipe
                updated += 1
                
                catalog["upsert_log"].append({
                    "action": "updated",
                    "recipe_name": name,
                    "source_image": source_image or recipe.get("source_image"),
                    "timestamp": datetime.now().isoformat(),
                    "previous_source": old_recipe.get("source_image")
                })
        else:
            # Add new recipe
            catalog["recipes"].append(recipe)
            existing_recipes[normalized] = len(catalog["recipes"]) - 1
            added += 1
            
            catalog["upsert_log"].append({
                "action": "added",
                "recipe_name": name,
                "source_image": source_image or recipe.get("source_image"),
                "timestamp": datetime.now().isoformat()
            })
    
    # Process new chapters (if any)
    if new_chapters:
        existing_chapters = {}
        for i, chapter in enumerate(catalog["chapters"]):
            title = chapter.get("chapter_title", "")
            if title:
                existing_chapters[title.lower()] = i
        
        for chapter in new_chapters:
            title = chapter.get("chapter_title", "")
            if not title:
                continue
            
            if title.lower() in existing_chapters:
                # Update existing chapter
                idx = existing_chapters[title.lower()]
                catalog["chapters"][idx] = chapter
            else:
                # Add new chapter
                catalog["chapters"].append(chapter)
    
    # Reassign unknown chapters based on chapter recipe lists
    reassigned = reassign_unknown_chapters(catalog)
    if reassigned > 0:
        print(f"  📁 Reassigned {reassigned} recipe(s) to correct chapters")
    
    # Rebuild index
    catalog["index"] = build_recipe_index(catalog)
    
    # Update metadata
    catalog["metadata"]["recipes_extracted"] = len(catalog["recipes"])
    catalog["metadata"]["indexed_recipes"] = len(catalog["index"]["by_name"])
    catalog["metadata"]["last_upsert"] = datetime.now().isoformat()
    
    return catalog, added, updated, merged


def build_recipe_index(catalog: dict) -> dict:
    """
    Build an index linking recipe names to their full recipe data.
    
    Creates:
    - by_name: Quick lookup by normalized recipe name
    - by_chapter: Recipes grouped by chapter
    - all_recipes: List of all recipe names for random selection
    - unmatched: Recipe names from chapters that weren't found in extracted recipes
    """
    index = {
        "by_name": {},
        "by_chapter": {},
        "all_recipes": [],
        "unmatched": [],
        "by_dietary": {},
        "by_macros": {
            "high_protein": [],  # > 30g protein
            "low_carb": [],      # < 20g carbs
            "low_calorie": []    # < 400 calories
        }
    }
    
    # Index all extracted recipes by normalized name
    recipe_lookup = {}
    for i, recipe in enumerate(catalog.get("recipes", [])):
        name = recipe.get("name", "")
        if name:
            normalized = normalize_recipe_name(name)
            recipe_lookup[normalized] = i
            
            index["by_name"][name] = {
                "recipe_index": i,
                "chapter": recipe.get("chapter"),
                "serves": recipe.get("serves"),
                "dietary_info": recipe.get("dietary_info", []),
                "calories": recipe.get("calories"),
                "protein": recipe.get("protein"),
                "prep_time": recipe.get("prep_time")
            }
            index["all_recipes"].append(name)
            
            # Group by chapter
            chapter = recipe.get("chapter", "Unknown")
            if chapter not in index["by_chapter"]:
                index["by_chapter"][chapter] = []
            index["by_chapter"][chapter].append(name)
            
            # Group by dietary info
            for diet in recipe.get("dietary_info", []):
                diet_key = diet.lower().replace("-", "_").replace(" ", "_")
                if diet_key not in index["by_dietary"]:
                    index["by_dietary"][diet_key] = []
                index["by_dietary"][diet_key].append(name)
            
            # Group by macros (parse numeric values)
            try:
                protein = recipe.get("protein", "")
                if protein:
                    protein_val = int(re.search(r'\d+', str(protein)).group())
                    if protein_val > 30:
                        index["by_macros"]["high_protein"].append(name)
            except:
                pass
            
            try:
                carbs = recipe.get("carbs", "")
                if carbs:
                    carbs_val = int(re.search(r'\d+', str(carbs)).group())
                    if carbs_val < 20:
                        index["by_macros"]["low_carb"].append(name)
            except:
                pass
            
            try:
                calories = recipe.get("calories", "")
                if calories:
                    cal_val = int(re.search(r'\d+', str(calories)).group())
                    if cal_val < 400:
                        index["by_macros"]["low_calorie"].append(name)
            except:
                pass
    
    # Check chapter recipe lists against extracted recipes
    # Track already-added unmatched to avoid duplicates
    unmatched_normalized = set()
    
    for chapter in catalog.get("chapters", []):
        chapter_title = chapter.get("chapter_title", "Unknown")
        for listed_name in chapter.get("recipe_list", []):
            normalized = normalize_recipe_name(listed_name)
            
            # Skip if we've already processed this (avoid duplicates)
            if normalized in unmatched_normalized:
                continue
            
            # Try to find a match using fuzzy matching
            matched = False
            for recipe in catalog.get("recipes", []):
                recipe_name = recipe.get("name", "")
                if fuzzy_match_names(listed_name, recipe_name):
                    matched = True
                    break
            
            if not matched:
                # Also check if already in all_recipes (exact match)
                if listed_name not in index["all_recipes"]:
                    index["unmatched"].append({
                        "name": listed_name,
                        "chapter": chapter_title,
                        "note": "Listed in chapter but not yet extracted"
                    })
                    unmatched_normalized.add(normalized)
    
    return index


def get_random_recipe(catalog: dict, chapter: str = None, dietary: str = None, 
                     macro_filter: str = None) -> dict:
    """
    Get a random recipe from the catalog.
    
    Args:
        catalog: The recipe catalog dictionary
        chapter: Optional chapter to filter by
        dietary: Optional dietary filter (e.g., "vegan", "gluten_free")
        macro_filter: Optional macro filter ("high_protein", "low_carb", "low_calorie")
    
    Returns:
        Full recipe dictionary or error message
    """
    import random
    
    index = catalog.get("index", {})
    recipes = catalog.get("recipes", [])
    
    # Start with all recipes
    recipe_names = set(index.get("all_recipes", []))
    
    # Filter by chapter
    if chapter:
        chapter_recipes = set(index.get("by_chapter", {}).get(chapter, []))
        recipe_names = recipe_names.intersection(chapter_recipes)
    
    # Filter by dietary
    if dietary:
        dietary_key = dietary.lower().replace("-", "_").replace(" ", "_")
        dietary_recipes = set(index.get("by_dietary", {}).get(dietary_key, []))
        recipe_names = recipe_names.intersection(dietary_recipes)
    
    # Filter by macros
    if macro_filter:
        macro_recipes = set(index.get("by_macros", {}).get(macro_filter, []))
        recipe_names = recipe_names.intersection(macro_recipes)
    
    if not recipe_names:
        filters = []
        if chapter:
            filters.append(f"chapter='{chapter}'")
        if dietary:
            filters.append(f"dietary='{dietary}'")
        if macro_filter:
            filters.append(f"macro='{macro_filter}'")
        return {"error": f"No recipes found matching filters: {', '.join(filters)}"}
    
    chosen_name = random.choice(list(recipe_names))
    recipe_info = index.get("by_name", {}).get(chosen_name, {})
    recipe_idx = recipe_info.get("recipe_index")
    
    if recipe_idx is not None and recipe_idx < len(recipes):
        return recipes[recipe_idx]
    
    return {"error": f"Could not find recipe: {chosen_name}"}


def print_recipe_list_simple(catalog: dict):
    """Print a simple alphabetical list of recipes with numbers."""
    recipes = catalog.get("recipes", [])
    
    if not recipes:
        print("No recipes in catalog.")
        return
    
    # Create list of (original_index, name) tuples
    indexed_recipes = [(i + 1, r.get("name", "Unknown")) for i, r in enumerate(recipes)]
    
    # Sort by name (case-insensitive)
    sorted_recipes = sorted(indexed_recipes, key=lambda x: x[1].lower())
    
    print(f"\n📋 Recipes ({len(recipes)} total) - Alphabetical")
    print("=" * 60)
    
    for num, name in sorted_recipes:
        recipe = next((r for r in recipes if r.get("name", "Unknown") == name), None)
        sub_count = len(recipe.get("sub_recipes", [])) if recipe else 0
        sub_str = f" (+{sub_count} sub-recipes)" if sub_count > 0 else ""
        print(f"  {num:3}. {name}{sub_str}")
    
    print("=" * 60)
    print(f"Use --delete <num> [num2 ...] to remove recipes")
    print(f"Use --list for detailed view with chapters and dietary info")


def print_catalog_summary(catalog: dict):
    """Print a summary of the catalog with available chapters and recipes."""
    print("\n" + "=" * 60)
    print("📚 RECIPE CATALOG SUMMARY")
    print("=" * 60)
    
    recipes = catalog.get("recipes", [])
    index = catalog.get("index", {})
    
    # Chapters summary
    by_chapter = index.get("by_chapter", {})
    if by_chapter:
        print(f"\n📖 Chapters ({len(by_chapter)}):")
        for chapter, chapter_recipes in by_chapter.items():
            print(f"   • {chapter}: {len(chapter_recipes)} recipes")
    
    # Dietary categories
    by_dietary = index.get("by_dietary", {})
    if by_dietary:
        print(f"\n🏷️  Dietary Categories:")
        for diet, diet_recipes in sorted(by_dietary.items()):
            print(f"   • {diet}: {len(diet_recipes)} recipes")
    
    # Macro categories
    by_macros = index.get("by_macros", {})
    if by_macros:
        print(f"\n💪 Macro Filters:")
        for macro, macro_recipes in by_macros.items():
            if macro_recipes:
                print(f"   • {macro}: {len(macro_recipes)} recipes")
    
    # All recipes with numbers
    print(f"\n📋 All Recipes ({len(recipes)}):")
    print("-" * 60)
    
    # Group by chapter for nicer display
    recipes_by_chapter = {}
    for i, recipe in enumerate(recipes):
        chapter = recipe.get("chapter", "Unknown")
        if chapter not in recipes_by_chapter:
            recipes_by_chapter[chapter] = []
        recipes_by_chapter[chapter].append((i + 1, recipe))  # 1-indexed
    
    for chapter in sorted(recipes_by_chapter.keys()):
        print(f"\n   [{chapter}]")
        for num, recipe in recipes_by_chapter[chapter]:
            name = recipe.get("name", "Unknown")
            dietary = recipe.get("dietary_info", [])
            dietary_str = f" ({', '.join(dietary)})" if dietary and dietary != [''] else ""
            print(f"   {num:3}. {name}{dietary_str}")
            
            sub_recipes = recipe.get("sub_recipes", [])
            if sub_recipes:
                print(f"        + {len(sub_recipes)} sub-recipes: {', '.join([s.get('name', 'Unknown') for s in sub_recipes])}")
    
    # Unmatched (recipes listed but not extracted)
    unmatched = index.get("unmatched", [])
    if unmatched:
        print(f"\n⚠️  Not yet extracted ({len(unmatched)}):")
        for item in unmatched[:5]:
            print(f"   • {item['name']}")
        if len(unmatched) > 5:
            print(f"   ... and {len(unmatched) - 5} more")
    
    print("\n" + "=" * 60)
    print(f"Total: {len(recipes)} recipes")
    print("Use --delete <num> [num2 ...] to remove recipes by number")
    print("=" * 60)


def process_cookbook_folder(folder_path: str, model: str = "llava", output_file: str = None, 
                           max_retries: int = 2, api_key: str = None, backup_model: str = None,
                           sort_by: str = "name") -> dict:
    """
    Process all images in a folder and catalog recipes.
    
    Args:
        folder_path: Path to folder containing cookbook images
        model: Ollama model to use
        output_file: Optional path for output JSON file
        max_retries: Max retry attempts per image
        api_key: API key for Claude models
        backup_model: Fallback model for large files
        sort_by: How to sort files - 'name' (alphabetical) or 'date' (oldest first)
    
    Returns:
        Dictionary containing cataloged cookbook data
    """
    folder = Path(folder_path)
    
    # Supported image extensions
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    
    # Get all image files
    image_files = [
        f for f in folder.iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ]
    
    # Sort based on preference
    if sort_by == "date":
        # Sort by modification time (oldest first)
        image_files = sorted(image_files, key=lambda f: f.stat().st_mtime)
        print(f"Sorting by modification date (oldest first)")
    else:
        # Default: sort by filename
        image_files = sorted(image_files)
        print(f"Sorting by filename (alphabetical)")
    
    if not image_files:
        print(f"No image files found in {folder_path}")
        return {"error": "No images found"}
    
    print(f"Found {len(image_files)} images to process")
    
    # Initialize catalog structure
    catalog = {
        "metadata": {
            "source_folder": str(folder_path),
            "processed_date": datetime.now().isoformat(),
            "model_used": model,
            "total_images": len(image_files)
        },
        "chapters": [],
        "recipes": [],
        "processing_log": []
    }
    
    current_chapter = None
    pending_recipe = None  # Recipe that continues from previous page
    
    for i, image_path in enumerate(image_files):
        print(f"\n[{i+1}/{len(image_files)}] Processing: {image_path.name}")
        
        # Classify the page with detailed analysis
        classification = classify_page(str(image_path), model, api_key, backup_model)
        page_type = classification.get("type", "other")
        
        print(f"  Type: {page_type} (confidence: {classification.get('confidence', 'unknown')})")
        
        if classification.get("page_numbers"):
            print(f"  Pages: {classification['page_numbers']}")
        
        log_entry = {
            "file": image_path.name,
            "page_type": page_type,
            "page_numbers": classification.get("page_numbers", []),
            "classification": classification
        }
        
        if page_type == "chapter":
            # Extract chapter info
            chapter_info = extract_chapter_info(str(image_path), model, api_key, backup_model)
            chapter_info["source_image"] = image_path.name
            chapter_info["page_numbers"] = classification.get("page_numbers", [])
            catalog["chapters"].append(chapter_info)
            current_chapter = chapter_info
            
            print(f"  Chapter: {chapter_info.get('chapter_title', 'Unknown')}")
            print(f"  Recipes listed: {len(chapter_info.get('recipe_list', []))}")
            
            log_entry["chapter_title"] = chapter_info.get("chapter_title")
            log_entry["recipes_listed"] = len(chapter_info.get("recipe_list", []))
            
        elif page_type in ["recipe", "recipe_partial"]:
            # Handle recipe continuation
            if pending_recipe and classification.get("has_recipe_continuation"):
                print(f"  Continuing recipe: {pending_recipe.get('name', 'Unknown')}")
            
            # Extract recipes
            result = extract_recipes(str(image_path), model, current_chapter, pending_recipe, max_retries, api_key, backup_model, classification)
            
            # Handle completed recipes
            for recipe in result.get("recipes", []):
                recipe["source_image"] = image_path.name
                catalog["recipes"].append(recipe)
            
            # Handle partial recipe for next page
            new_partial = result.get("partial_recipe")
            if new_partial:
                new_partial["source_image"] = image_path.name
                
                # Check if this "partial" is actually a complete recipe that was misidentified
                # This happens when a recipe has something like "step 5" at the top from another recipe
                has_name = bool(new_partial.get("name"))
                has_ingredients = len(new_partial.get("ingredients", [])) > 0
                has_instructions = len(new_partial.get("instructions", [])) > 0
                
                if has_name and has_ingredients and has_instructions:
                    # This looks complete - check if it was marked as continuation without a pending
                    if new_partial.get("is_continuation") and not pending_recipe:
                        print(f"  Saving as complete (was orphan continuation): {new_partial.get('name', 'Unknown')}")
                        new_partial["note"] = "Was marked as continuation but no previous context - saved as complete"
                        new_partial["is_continuation"] = False
                        new_partial["is_complete"] = True
                        catalog["recipes"].append(new_partial)
                        pending_recipe = None
                    else:
                        print(f"  Recipe continues: {new_partial.get('name', 'Unknown')}")
                        pending_recipe = new_partial
                else:
                    print(f"  Recipe continues: {new_partial.get('name', 'Unknown')}")
                    pending_recipe = new_partial
            else:
                # Clear pending if we completed it
                if pending_recipe and result.get("recipes"):
                    pending_recipe = None
            
            recipe_names = [r.get("name", "Unknown") for r in result.get("recipes", [])]
            print(f"  Extracted {len(result.get('recipes', []))} recipe(s): {', '.join(recipe_names) if recipe_names else 'none'}")
            
            log_entry["recipes_extracted"] = recipe_names
            log_entry["has_continuation"] = pending_recipe is not None
            
        elif page_type == "article":
            print(f"  Skipping article/text page")
            log_entry["status"] = "skipped - article"
            
        elif page_type == "photo":
            # Check if this is a recipe photo that might have useful info
            recipe_names = classification.get("recipe_names_visible", [])
            if recipe_names:
                print(f"  Photo page for: {', '.join(recipe_names)}")
                log_entry["recipe_names_visible"] = recipe_names
            else:
                print(f"  Skipping photo page")
            log_entry["status"] = "skipped - photo"
            
        else:
            print(f"  Skipping (page type: {page_type})")
            log_entry["status"] = "skipped"
        
        catalog["processing_log"].append(log_entry)
    
    # Handle any remaining pending recipe
    if pending_recipe:
        print(f"\nNote: Recipe '{pending_recipe.get('name', 'Unknown')}' may be incomplete (continued beyond processed pages)")
        pending_recipe["is_complete"] = False
        pending_recipe["note"] = "Recipe may be incomplete - continued beyond processed pages"
        catalog["recipes"].append(pending_recipe)
    
    # Build recipe index
    catalog["index"] = build_recipe_index(catalog)
    
    # Summary
    catalog["metadata"]["chapters_found"] = len(catalog["chapters"])
    catalog["metadata"]["recipes_extracted"] = len(catalog["recipes"])
    catalog["metadata"]["indexed_recipes"] = len(catalog["index"]["by_name"])
    
    print(f"\n{'='*50}")
    print(f"Processing complete!")
    print(f"  Chapters found: {len(catalog['chapters'])}")
    print(f"  Recipes extracted: {len(catalog['recipes'])}")
    
    # Save to file
    if output_file is None:
        output_file = folder / "recipe_catalog.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, indent=2, ensure_ascii=False)
    
    print(f"  Catalog saved to: {output_file}")
    
    return catalog


def process_single_file(file_path: str, model: str, chapter_context: dict = None, 
                       max_retries: int = 2, api_key: str = None, debug: bool = False,
                       backup_model: str = None) -> dict:
    """
    Process a single image file for testing purposes.
    
    Args:
        file_path: Path to the image file
        model: Ollama model to use
        chapter_context: Optional chapter info to use as context
    
    Returns:
        Dictionary with extraction results
    """
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        return {"error": "File not found"}
    
    print(f"Processing single file: {file_path}")
    print(f"Using model: {model}")
    print("=" * 50)
    
    result = {
        "file": os.path.basename(file_path),
        "model": model
    }
    
    # Step 1: Classify the page with detailed analysis
    print("\n[Step 1] Classifying page type...")
    classification = classify_page(file_path, model, api_key, backup_model)
    page_type = classification.get("type", "other")
    result["classification"] = classification
    
    print(f"  Type: {page_type}")
    print(f"  Confidence: {classification.get('confidence', 'unknown')}")
    if classification.get("page_numbers"):
        print(f"  Page numbers: {classification['page_numbers']}")
    if classification.get("total_pages"):
        print(f"  Total pages in book: {classification['total_pages']}")
    if classification.get("recipe_names_visible"):
        print(f"  Recipes visible: {classification['recipe_names_visible']}")
    print(f"  Has recipe start: {classification.get('has_recipe_start', False)}")
    print(f"  Has continuation: {classification.get('has_recipe_continuation', False)}")
    
    # Step 2: Extract content based on type
    if page_type == "chapter":
        print("\n[Step 2] Extracting chapter information...")
        chapter_info = extract_chapter_info(file_path, model, api_key, backup_model)
        result["chapter_info"] = chapter_info
        
        print(f"  Chapter: {chapter_info.get('chapter_number', 'N/A')} - {chapter_info.get('chapter_title', 'Unknown')}")
        recipe_list = chapter_info.get('recipe_list', [])
        print(f"  Recipes listed: {len(recipe_list)}")
        if recipe_list:
            print("  Recipe names:")
            for i, name in enumerate(recipe_list, 1):
                print(f"    {i}. {name}")
        
        if chapter_info.get('notes'):
            print(f"  Notes: {chapter_info['notes']}")
            
    elif page_type in ["recipe", "recipe_partial"]:
        print("\n[Step 2] Extracting recipe details...")
        if chapter_context:
            print(f"  Using chapter context: {chapter_context.get('chapter_title', 'Unknown')}")
        
        extraction = extract_recipes(file_path, model, chapter_context, None, max_retries, api_key, backup_model, classification)
        recipes = extraction.get("recipes", [])
        result["recipes"] = recipes
        result["partial_recipe"] = extraction.get("partial_recipe")
        
        print(f"  Found {len(recipes)} complete recipe(s)")
        
        for i, recipe in enumerate(recipes, 1):
            print(f"\n  --- Recipe {i}: {recipe.get('name', 'Unknown')} ---")
            print(f"  Serves: {recipe.get('serves', 'N/A')}")
            
            # Meal type and dish role
            if recipe.get('meal_type'):
                print(f"  Meal type: {recipe['meal_type']}")
            if recipe.get('dish_role'):
                print(f"  Dish role: {recipe['dish_role']}")
            
            # Time info
            if recipe.get('prep_time') or recipe.get('cook_time'):
                times = []
                if recipe.get('prep_time'):
                    times.append(f"Prep: {recipe['prep_time']}")
                if recipe.get('cook_time'):
                    times.append(f"Cook: {recipe['cook_time']}")
                print(f"  Time: {', '.join(times)}")
            
            # Macros
            macros = []
            if recipe.get('calories'):
                macros.append(f"{recipe['calories']} cal")
            if recipe.get('protein'):
                macros.append(f"{recipe['protein']} protein")
            if recipe.get('carbs'):
                macros.append(f"{recipe['carbs']} carbs")
            if recipe.get('fat'):
                macros.append(f"{recipe['fat']} fat")
            if macros:
                print(f"  Macros: {' | '.join(macros)}")
            
            dietary = recipe.get('dietary_info', [])
            if dietary:
                print(f"  Dietary: {', '.join(dietary)}")
            
            ingredients = recipe.get('ingredients', [])
            print(f"  Ingredients: {len(ingredients)} items")
            for ing in ingredients[:5]:
                print(f"    - {ing}")
            if len(ingredients) > 5:
                print(f"    ... and {len(ingredients) - 5} more")
            
            sub_recipes = recipe.get('sub_recipes', [])
            if sub_recipes:
                print(f"  Sub-recipes: {len(sub_recipes)} found")
                for sr in sub_recipes:
                    print(f"    - {sr.get('name', 'Unknown')}")
                    if sr.get('ingredients'):
                        print(f"      Ingredients: {len(sr.get('ingredients'))}")
                    if sr.get('instructions'):
                        print(f"      Instructions: {len(sr.get('instructions'))}")
            
            instructions = recipe.get('instructions', [])
            print(f"  Instructions: {len(instructions)} steps")
            
            tips = recipe.get('tips', [])
            if tips:
                print(f"  Tips: {len(tips)} tip(s)")
        
        if extraction.get("partial_recipe"):
            partial = extraction["partial_recipe"]
            
            # Check if this "partial" is actually complete (has name, ingredients, instructions)
            has_name = bool(partial.get("name"))
            has_ingredients = len(partial.get("ingredients", [])) > 0
            has_instructions = len(partial.get("instructions", [])) > 0
            
            if has_name and has_ingredients and has_instructions:
                # This looks complete - treat it as a full recipe
                print(f"\n  📋 Recipe (marked as partial but appears complete): {partial.get('name', 'Unknown')}")
                
                # Print details for verification
                recipe = partial
                print(f"  Serves: {recipe.get('serves', 'N/A')}")
                
                # Meal type and dish role
                if recipe.get('meal_type'):
                    print(f"  Meal type: {recipe['meal_type']}")
                if recipe.get('dish_role'):
                    print(f"  Dish role: {recipe['dish_role']}")
                
                # Time info
                if recipe.get('prep_time') or recipe.get('cook_time'):
                    times = []
                    if recipe.get('prep_time'):
                        times.append(f"Prep: {recipe['prep_time']}")
                    if recipe.get('cook_time'):
                        times.append(f"Cook: {recipe['cook_time']}")
                    print(f"  Time: {', '.join(times)}")
                
                # Macros
                macros = []
                if recipe.get('calories'):
                    macros.append(f"{recipe['calories']} cal")
                if recipe.get('protein'):
                    macros.append(f"{recipe['protein']} protein")
                if recipe.get('carbs'):
                    macros.append(f"{recipe['carbs']} carbs")
                if recipe.get('fat'):
                    macros.append(f"{recipe['fat']} fat")
                if macros:
                    print(f"  Macros: {' | '.join(macros)}")
                
                dietary = recipe.get('dietary_info', [])
                if dietary:
                    print(f"  Dietary: {', '.join(dietary)}")
                
                ingredients = recipe.get('ingredients', [])
                print(f"  Ingredients: {len(ingredients)} items")
                for ing in ingredients[:5]:
                    print(f"    - {ing}")
                if len(ingredients) > 5:
                    print(f"    ... and {len(ingredients) - 5} more")
                
                sub_recipes = recipe.get('sub_recipes', [])
                if sub_recipes:
                    print(f"  Sub-recipes: {len(sub_recipes)} found")
                    for sr in sub_recipes:
                        print(f"    - {sr.get('name', 'Unknown')}")
                        if sr.get('ingredients'):
                            print(f"      Ingredients: {len(sr.get('ingredients'))}")
                        if sr.get('instructions'):
                            print(f"      Instructions: {len(sr.get('instructions'))}")
                
                instructions = recipe.get('instructions', [])
                print(f"  Instructions: {len(instructions)} steps")
                
                tips = recipe.get('tips', [])
                if tips:
                    print(f"  Tips: {len(tips)} tip(s)")
                partial["note"] = "Was marked as continuation/partial but has all required fields"
                partial["is_complete"] = True
                
                # Add to recipes list
                if "recipes" not in result:
                    result["recipes"] = []
                result["recipes"].append(partial)
                result["partial_recipe"] = None  # Clear partial
            else:
                print(f"\n  ⚠️  Partial recipe (continues next page): {partial.get('name', 'Unknown')}")
                print(f"      Has name: {has_name}, Has ingredients: {has_ingredients}, Has instructions: {has_instructions}")
        
        # Debug mode: Run diagnostic if extraction seems to have failed
        if debug:
            expected_recipes = len(classification.get("recipe_names_visible", []))
            actual_recipes = len(result.get("recipes", []))
            has_partial = result.get("partial_recipe") is not None
            
            # Determine if we should run diagnostics
            run_diagnostic = False
            diagnostic_reason = ""
            
            if expected_recipes > 0 and actual_recipes == 0 and not has_partial:
                run_diagnostic = True
                diagnostic_reason = f"Expected {expected_recipes} recipe(s) but extracted 0"
            elif expected_recipes > actual_recipes + (1 if has_partial else 0):
                run_diagnostic = True
                diagnostic_reason = f"Expected {expected_recipes} recipe(s) but only got {actual_recipes} complete + {1 if has_partial else 0} partial"
            elif has_partial and not result.get("recipes"):
                run_diagnostic = True
                diagnostic_reason = "Only got partial recipe, no complete recipes"
            
            if run_diagnostic:
                print(f"\n🔍 Running diagnostic analysis ({diagnostic_reason})...")
                diagnostic = analyze_extraction_failure(
                    file_path, model, api_key, classification, extraction
                )
                result["diagnostic"] = diagnostic
                print_diagnostic_report(diagnostic)
                
    elif page_type == "article":
        print("\n[Step 2] This is an article/text page - no recipe extraction")
        result["note"] = "Article page - contains text/stories but no recipes"
        
    elif page_type == "photo":
        print("\n[Step 2] This is a photo page")
        if classification.get("recipe_names_visible"):
            result["note"] = f"Photo page for: {', '.join(classification['recipe_names_visible'])}"
        else:
            result["note"] = "Photo page with no recipe text"
    else:
        print("\n[Step 2] Page classified as 'other' - no extraction performed")
        result["note"] = "Page was not identified as a chapter or recipe page"
    
    print("\n" + "=" * 50)
    print("Processing complete!")
    
    return result


def process_multiple_files(file_paths: List[str], model: str, chapter_context: dict = None,
                          max_retries: int = 2, api_key: str = None, debug: bool = False,
                          backup_model: str = None) -> dict:
    """
    Process multiple image files with continuation support.
    Files should be provided in page order for proper continuation handling.
    
    Args:
        file_paths: List of paths to image files (in order)
        model: Model to use
        chapter_context: Optional chapter info to use as context
        max_retries: Max retry attempts per image
        api_key: API key for Claude
        debug: Run diagnostic on failures
        backup_model: Fallback model for large files
    
    Returns:
        Dictionary with combined extraction results
    """
    print(f"Processing {len(file_paths)} files with continuation support...")
    print(f"Using model: {model}")
    print("=" * 60)
    
    # Validate all files exist first
    for fp in file_paths:
        if not os.path.isfile(fp):
            print(f"Error: File not found: {fp}")
            return {"error": f"File not found: {fp}"}
    
    all_recipes = []
    all_chapters = []
    pending_recipe = None
    current_chapter = chapter_context
    processing_log = []
    
    for i, file_path in enumerate(file_paths, 1):
        print(f"\n[{i}/{len(file_paths)}] Processing: {os.path.basename(file_path)}")
        print("-" * 50)
        
        # Classify the page
        print("  Classifying page...")
        classification = classify_page(file_path, model, api_key, backup_model)
        page_type = classification.get("type", "other")
        
        print(f"  Type: {page_type}")
        print(f"  Confidence: {classification.get('confidence', 'unknown')}")
        
        if classification.get("page_numbers"):
            print(f"  Page numbers: {classification['page_numbers']}")
        if classification.get("has_recipe_continuation"):
            print(f"  ⚠️  Has continuation from previous page")
        if classification.get("recipe_names_visible"):
            print(f"  Recipes visible: {classification['recipe_names_visible']}")
        
        log_entry = {
            "file": os.path.basename(file_path),
            "page_type": page_type,
            "classification": classification,
            "recipes_extracted": []
        }
        
        # Handle based on page type
        if page_type == "chapter":
            print("  Extracting chapter info...")
            chapter_info = extract_chapter_info(file_path, model, api_key, backup_model)
            all_chapters.append(chapter_info)
            current_chapter = chapter_info
            
            print(f"  📖 Chapter: {chapter_info.get('chapter_title', 'Unknown')}")
            recipe_list = chapter_info.get('recipe_list', [])
            if recipe_list:
                print(f"  Recipes listed: {len(recipe_list)}")
            
            log_entry["chapter_info"] = chapter_info
        
        elif page_type in ["recipe", "recipe_partial"]:
            print("  Extracting recipes...")
            
            has_continuation = classification.get("has_recipe_continuation", False)
            has_new_recipe = classification.get("has_recipe_start", False) or classification.get("recipe_names_visible")
            
            # If page is classified as recipe_partial and we have a pending recipe,
            # ALWAYS use extract_partial_recipe - this is a continuation page
            if page_type == "recipe_partial" and pending_recipe:
                print(f"  📝 Continuing recipe (partial page): {pending_recipe.get('name', 'Unknown')}")
                
                # Use extract_partial_recipe for continuation pages
                completed_recipe = extract_partial_recipe(
                    file_path, model, pending_recipe, api_key, backup_model
                )
                
                if completed_recipe.get("is_complete", True):
                    completed_recipe["source_image"] = os.path.basename(file_path)
                    if current_chapter:
                        completed_recipe["chapter"] = current_chapter.get("chapter_title", "")
                    all_recipes.append(completed_recipe)
                    log_entry["recipes_extracted"].append(completed_recipe.get("name", "Unknown"))
                    print(f"  ✅ Completed: {completed_recipe.get('name', 'Unknown')}")
                    pending_recipe = None
                else:
                    # Still continues to next page
                    pending_recipe = completed_recipe
                    print(f"  ⏳ Still continues: {completed_recipe.get('name', 'Unknown')}")
                    log_entry["has_continuation"] = True
            
            # If this is a continuation page with no pending recipe, or a full recipe page
            elif has_continuation and pending_recipe and not has_new_recipe:
                print(f"  📝 Continuing recipe: {pending_recipe.get('name', 'Unknown')}")
                
                # Use extract_partial_recipe for pure continuation pages
                completed_recipe = extract_partial_recipe(
                    file_path, model, pending_recipe, api_key, backup_model
                )
                
                if completed_recipe.get("is_complete", True):
                    completed_recipe["source_image"] = os.path.basename(file_path)
                    if current_chapter:
                        completed_recipe["chapter"] = current_chapter.get("chapter_title", "")
                    all_recipes.append(completed_recipe)
                    log_entry["recipes_extracted"].append(completed_recipe.get("name", "Unknown"))
                    print(f"  ✅ Completed: {completed_recipe.get('name', 'Unknown')}")
                    pending_recipe = None
                else:
                    # Still continues to next page
                    pending_recipe = completed_recipe
                    print(f"  ⏳ Still continues: {completed_recipe.get('name', 'Unknown')}")
                    log_entry["has_continuation"] = True
            else:
                # Normal extraction - may have new recipes (possibly with continuation too)
                extraction = extract_recipes(
                    file_path, model, current_chapter, pending_recipe, 
                    max_retries, api_key, backup_model, classification
                )
                
                # Handle completed recipes
                recipes = extraction.get("recipes", [])
                for recipe in recipes:
                    recipe["source_image"] = os.path.basename(file_path)
                    if current_chapter:
                        recipe["chapter"] = current_chapter.get("chapter_title", "")
                    all_recipes.append(recipe)
                    log_entry["recipes_extracted"].append(recipe.get("name", "Unknown"))
                    print(f"  ✅ Extracted: {recipe.get('name', 'Unknown')}")
                
                # Handle partial/continuation
                new_partial = extraction.get("partial_recipe")
                if new_partial:
                    new_partial["source_image"] = os.path.basename(file_path)
                    
                    # Check if partial is actually complete
                    has_name = bool(new_partial.get("name"))
                    has_ingredients = len(new_partial.get("ingredients", [])) > 0
                    has_instructions = len(new_partial.get("instructions", [])) > 0
                    
                    if has_name and has_ingredients and has_instructions:
                        # Complete enough to save
                        if new_partial.get("is_continuation") and not pending_recipe:
                            new_partial["note"] = "Was marked as continuation but no previous context"
                        new_partial["is_complete"] = True
                        if current_chapter:
                            new_partial["chapter"] = current_chapter.get("chapter_title", "")
                        all_recipes.append(new_partial)
                        log_entry["recipes_extracted"].append(new_partial.get("name", "Unknown"))
                        print(f"  ✅ Extracted (from partial): {new_partial.get('name', 'Unknown')}")
                        pending_recipe = None
                    else:
                        # Truly partial - save for next page
                        pending_recipe = new_partial
                        print(f"  ⏳ Partial recipe continues: {new_partial.get('name', 'Unknown')}")
                        log_entry["has_continuation"] = True
                else:
                    pending_recipe = None
            
            # Debug mode
            if debug and not recipes and not new_partial:
                expected = len(classification.get("recipe_names_visible", []))
                if expected > 0:
                    print(f"  🔍 Running diagnostic (expected {expected} recipes)...")
                    diagnostic = analyze_extraction_failure(
                        file_path, model, api_key, classification, extraction
                    )
                    log_entry["diagnostic"] = diagnostic
                    print_diagnostic_report(diagnostic)
        
        elif page_type == "article":
            print("  ℹ️  Article page - skipping extraction")
        
        elif page_type == "photo":
            print("  📷 Photo page - skipping extraction")
        
        else:
            print(f"  ⚠️  Unknown page type: {page_type}")
        
        processing_log.append(log_entry)
    
    # Handle any remaining partial recipe
    if pending_recipe:
        has_name = bool(pending_recipe.get("name"))
        has_ingredients = len(pending_recipe.get("ingredients", [])) > 0
        has_instructions = len(pending_recipe.get("instructions", [])) > 0
        
        if has_name and has_ingredients and has_instructions:
            pending_recipe["note"] = "Final partial saved as complete"
            pending_recipe["is_complete"] = True
            all_recipes.append(pending_recipe)
            print(f"\n✅ Saved final partial as complete: {pending_recipe.get('name', 'Unknown')}")
        else:
            print(f"\n⚠️  Incomplete recipe not saved: {pending_recipe.get('name', 'Unknown')}")
            print(f"    Has name: {has_name}, ingredients: {has_ingredients}, instructions: {has_instructions}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Files processed: {len(file_paths)}")
    print(f"  Chapters found: {len(all_chapters)}")
    print(f"  Recipes extracted: {len(all_recipes)}")
    
    if all_recipes:
        print("\n  Recipes:")
        for i, recipe in enumerate(all_recipes, 1):
            print(f"    {i}. {recipe.get('name', 'Unknown')}")
    
    return {
        "files_processed": [os.path.basename(fp) for fp in file_paths],
        "model": model,
        "chapters": all_chapters,
        "recipes": all_recipes,
        "processing_log": processing_log
    }
def check_model_available(model: str, api_key: str = None) -> bool:
    """Check if the specified model is available (Ollama or Claude)."""
    
    # Check if it's a Claude model
    is_claude = any(claude_model in model for claude_model in config.CLAUDE_VISION_MODELS) or model.startswith("claude-")
    
    if is_claude:
        if not api_key:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not api_key:
            print(f"Error: Claude model '{model}' requires an API key.")
            print("Set ANTHROPIC_API_KEY environment variable or use --api-key")
            return False
        
        # Verify API key works with a minimal request
        try:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            # Just check auth, don't actually send a message
            response = requests.get("https://api.anthropic.com/v1/models", headers=headers, timeout=10)
            if response.status_code == 401:
                print("Error: Invalid Anthropic API key")
                return False
            # 404 is OK - endpoint might not exist but auth worked
            # 200 is OK - auth worked
            print(f"Using Claude model: {model}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Warning: Could not verify Claude API key: {e}")
            print("Proceeding anyway...")
            return True
    else:
        # Ollama model
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            response.raise_for_status()
            
            models = response.json().get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]
            model_full_names = [m.get("name", "") for m in models]
            
            model_base = model.split(":")[0]
            if model_base not in model_names and model not in model_full_names:
                print(f"Model '{model}' not found. Available models: {model_full_names}")
                print(f"Pull the model with: ollama pull {model}")
                return False
            
            print(f"Using Ollama model: {model}")
            return True
        except requests.exceptions.ConnectionError:
            print("Ollama is not running. Start it with: ollama serve")
            return False
        except Exception as e:
            print(f"Error checking Ollama: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Catalog recipes from cookbook images using Ollama vision models"
    )
    parser.add_argument(
        "folder",
        nargs="?",  # Make folder optional
        help="Path to folder containing cookbook images"
    )
    parser.add_argument(
        "-f", "--file",
        nargs="+",
        help="Process one or more image files (for multi-page recipes, list in page order)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: recipe_catalog.json in input folder)"
    )
    parser.add_argument(
        "-m", "--model",
        default="llava",
        help="Model to use. Ollama: llava, llava:13b, qwen2-vl:8b. Claude: claude-sonnet-4-20250514, claude-3-5-sonnet-20241022"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key for Claude models (or set ANTHROPIC_API_KEY env var)"
    )
    parser.add_argument(
        "--backup-model",
        help="Fallback model for files > 5MB (Claude limit). E.g., 'qwen2-vl:8b' for Ollama"
    )
    parser.add_argument(
        "--chapter-title",
        help="Chapter title to use as context when testing a single recipe file"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if Ollama and model are available"
    )
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=2,
        help="Max retry attempts per image for recipe extraction (default: 2)"
    )
    parser.add_argument(
        "--save-test",
        action="store_true",
        help="Save single file test results to JSON"
    )
    parser.add_argument(
        "--random",
        nargs="?",
        const="__all__",
        metavar="CHAPTER",
        help="Pick a random recipe from an existing catalog. Optionally specify a chapter name."
    )
    parser.add_argument(
        "--dietary",
        help="Filter random recipe by dietary tag (e.g., 'vegan', 'gluten_free')"
    )
    parser.add_argument(
        "--macro",
        choices=["high_protein", "low_carb", "low_calorie"],
        help="Filter random recipe by macro category"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all recipes (grouped by chapter with stats)"
    )
    parser.add_argument(
        "-l",
        action="store_true",
        help="Simple alphabetical list of recipes with numbers"
    )
    parser.add_argument(
        "--delete",
        nargs="+",
        type=int,
        metavar="NUM",
        help="Delete one or more recipes by number (use --list or -l to see numbers)"
    )
    parser.add_argument(
        "-c", "--catalog",
        help="Path to existing catalog JSON (for use with --random, --list, or --delete)"
    )
    parser.add_argument(
        "--append-to",
        help="Append/upsert results to an existing catalog JSON file"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run diagnostic analysis when extraction fails or finds fewer recipes than expected"
    )
    parser.add_argument(
        "--sort-by",
        choices=["name", "date"],
        default="name",
        help="How to sort files when processing a folder: 'name' (alphabetical, default) or 'date' (oldest first by modification time)"
    )
    
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    
    # Check model availability (skip for --list, -l, --random, --delete which don't need a model)
    if not args.list and not args.l and not args.random and not args.delete:
        if not check_model_available(args.model, api_key):
            sys.exit(1)
    
    if args.check_only:
        print(f"Model '{args.model}' is available!")
        sys.exit(0)
    
    # Load existing catalog for --random, --list, -l, or --delete
    if args.random or args.list or args.l or args.delete:
        catalog_path = args.catalog
        if not catalog_path:
            # Try to find catalog in current dir or specified folder
            if args.folder and os.path.isdir(args.folder):
                catalog_path = os.path.join(args.folder, "recipe_catalog.json")
            else:
                catalog_path = "recipe_catalog.json"
        
        if not os.path.isfile(catalog_path):
            print(f"Error: Catalog not found: {catalog_path}")
            print("Use -c/--catalog to specify the catalog path, or run on a folder first to create one.")
            sys.exit(1)
        
        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)
        
        # Auto-fix chapters when listing (reassign "Unknown" chapters)
        if args.l or args.list:
            reassigned = reassign_unknown_chapters(catalog)
            if reassigned > 0:
                print(f"📁 Reassigned {reassigned} recipe(s) to correct chapters")
                # Rebuild index and save
                catalog["index"] = build_recipe_index(catalog)
                with open(catalog_path, 'w', encoding='utf-8') as f:
                    json.dump(catalog, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved updated catalog\n")
        
        # Simple alphabetical list (-l)
        if args.l:
            print_recipe_list_simple(catalog)
            sys.exit(0)
        
        # Full summary with chapters (--list)
        if args.list:
            print_catalog_summary(catalog)
            sys.exit(0)
        
        if args.delete:
            recipes = catalog.get("recipes", [])
            total_recipes = len(recipes)
            
            # Validate all numbers first
            invalid_nums = [n for n in args.delete if n < 1 or n > total_recipes]
            if invalid_nums:
                print(f"Error: Invalid recipe number(s): {invalid_nums}")
                print(f"Valid range is 1-{total_recipes}. Use --list to see recipe numbers.")
                sys.exit(1)
            
            # Convert to 0-indexed and sort descending (delete from end first to preserve indices)
            indices_to_delete = sorted([n - 1 for n in args.delete], reverse=True)
            
            # Show what will be deleted
            print(f"\n🗑️  Deleting {len(indices_to_delete)} recipe(s) from: {catalog_path}")
            print("-" * 50)
            for idx in sorted(indices_to_delete):
                recipe = recipes[idx]
                print(f"  {idx + 1}. {recipe.get('name', 'Unknown')}")
            print("-" * 50)
            
            # Confirm deletion
            try:
                confirm = input("Confirm deletion? (y/N): ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                sys.exit(0)
            
            if confirm != 'y':
                print("Cancelled.")
                sys.exit(0)
            
            # Delete recipes (from end to preserve indices)
            deleted_names = []
            for idx in indices_to_delete:
                deleted_names.append(recipes[idx].get("name", "Unknown"))
                del recipes[idx]
            
            # Update catalog
            catalog["recipes"] = recipes
            
            # Add to deletion log
            if "deletion_log" not in catalog:
                catalog["deletion_log"] = []
            catalog["deletion_log"].append({
                "deleted": deleted_names,
                "timestamp": datetime.now().isoformat()
            })
            
            # Rebuild index if it exists
            if "index" in catalog:
                # Simple rebuild - just list all recipe names
                catalog["index"] = {
                    "recipes_by_name": {r.get("name", ""): i for i, r in enumerate(recipes)},
                    "total_recipes": len(recipes)
                }
            
            # Save updated catalog
            with open(catalog_path, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, indent=2, ensure_ascii=False)
            
            print(f"\n✅ Deleted {len(deleted_names)} recipe(s)")
            for name in deleted_names:
                print(f"   - {name}")
            print(f"\nTotal recipes remaining: {len(recipes)}")
            sys.exit(0)
        
        if args.random:
            chapter = None if args.random == "__all__" else args.random
            recipe = get_random_recipe(catalog, chapter, args.dietary, args.macro)
            
            if "error" in recipe:
                print(recipe["error"])
                sys.exit(1)
            
            print("\n🎲 RANDOM RECIPE PICK 🎲")
            print("=" * 50)
            print(f"Recipe: {recipe.get('name', 'Unknown')}")
            print(f"Chapter: {recipe.get('chapter', 'Unknown')}")
            print(f"Serves: {recipe.get('serves', 'N/A')}")
            
            # Time info
            if recipe.get('prep_time') or recipe.get('cook_time'):
                times = []
                if recipe.get('prep_time'):
                    times.append(f"Prep: {recipe['prep_time']}")
                if recipe.get('cook_time'):
                    times.append(f"Cook: {recipe['cook_time']}")
                print(f"Time: {', '.join(times)}")
            
            # Macros
            macros = []
            if recipe.get('calories'):
                macros.append(f"{recipe['calories']} cal")
            if recipe.get('protein'):
                macros.append(f"{recipe['protein']} protein")
            if recipe.get('carbs'):
                macros.append(f"{recipe['carbs']} carbs")
            if recipe.get('fat'):
                macros.append(f"{recipe['fat']} fat")
            if macros:
                print(f"Macros: {' | '.join(macros)}")
            
            dietary = recipe.get('dietary_info', [])
            if dietary:
                print(f"Dietary: {', '.join(dietary)}")
            
            print(f"\nIngredients:")
            for ing in recipe.get('ingredients', []):
                print(f"  • {ing}")
            
            for sub in recipe.get('sub_recipes', []):
                print(f"\n{sub.get('name', 'Sub-recipe')}:")
                for ing in sub.get('ingredients', []):
                    print(f"  • {ing}")
            
            print(f"\nInstructions:")
            for i, step in enumerate(recipe.get('instructions', []), 1):
                print(f"  {i}. {step}")
            
            tips = recipe.get('tips', [])
            if tips:
                print(f"\nTips:")
                for tip in tips:
                    print(f"  💡 {tip}")
            
            print("=" * 50)
            sys.exit(0)
    
    # Single or multiple file mode
    if args.file:
        chapter_context = None
        if args.chapter_title:
            chapter_context = {"chapter_title": args.chapter_title}
        
        # Determine if single or multiple files
        if len(args.file) == 1:
            # Single file - use original process_single_file
            result = process_single_file(args.file[0], args.model, chapter_context, args.retries, api_key, args.debug, args.backup_model)
            files_processed = [args.file[0]]
        else:
            # Multiple files - use process_multiple_files with continuation support
            print(f"\n📚 Processing {len(args.file)} files with continuation support...")
            print("   Files will be processed in order for multi-page recipe handling")
            result = process_multiple_files(args.file, args.model, chapter_context, args.retries, api_key, args.debug, args.backup_model)
            files_processed = args.file
        
        # Handle --append-to for upserting to existing catalog
        if args.append_to:
            if not os.path.isfile(args.append_to):
                print(f"Creating new catalog: {args.append_to}")
                catalog = {
                    "metadata": {
                        "source_folder": os.path.dirname(files_processed[0]),
                        "created_date": datetime.now().isoformat(),
                        "model_used": args.model
                    },
                    "chapters": [],
                    "recipes": [],
                    "processing_log": []
                }
            else:
                print(f"Loading existing catalog: {args.append_to}")
                with open(args.append_to, 'r', encoding='utf-8') as f:
                    catalog = json.load(f)
            
            # Collect recipes and chapters from result
            new_recipes = result.get("recipes", [])
            new_chapters = result.get("chapters", [])
            
            # For single file mode, also check chapter_info
            if result.get("chapter_info"):
                new_chapters.append(result["chapter_info"])
            
            # Handle partial recipe as complete if it looks complete (single file mode)
            if result.get("partial_recipe"):
                partial = result["partial_recipe"]
                if partial.get("name") and partial.get("ingredients") and partial.get("instructions"):
                    partial["note"] = "Saved from file processing"
                    new_recipes.append(partial)
            
            if new_recipes or new_chapters:
                source_images = ", ".join([os.path.basename(f) for f in files_processed])
                catalog, added, updated, merged = upsert_recipes(catalog, new_recipes, new_chapters, source_images)
                
                # Add to processing log
                for fp in files_processed:
                    log_entry = {
                        "file": os.path.basename(fp),
                        "timestamp": datetime.now().isoformat()
                    }
                    # Find matching log entry from result if available
                    for entry in result.get("processing_log", []):
                        if entry.get("file") == os.path.basename(fp):
                            log_entry.update(entry)
                            break
                    catalog["processing_log"].append(log_entry)
                
                # Save catalog
                with open(args.append_to, 'w', encoding='utf-8') as f:
                    json.dump(catalog, f, indent=2, ensure_ascii=False)
                
                print(f"\n✅ Catalog updated: {args.append_to}")
                print(f"   Added: {added} recipe(s)")
                print(f"   Updated: {updated} recipe(s)")
                if merged > 0:
                    print(f"   Merged: {merged} recipe(s) (continuations combined)")
                print(f"   Total recipes: {len(catalog['recipes'])}")
            else:
                print(f"\n⚠️  No recipes found to add/update")
        
        elif args.save_test or args.output:
            if len(files_processed) == 1:
                output_path = args.output or f"{Path(files_processed[0]).stem}_test_result.json"
            else:
                output_path = args.output or "multi_file_result.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nResults saved to: {output_path}")
        
        return
    
    # Folder mode - verify folder exists
    if not args.folder:
        parser.print_help()
        print("\nError: Please provide either a folder path or use -f/--file for single file testing")
        sys.exit(1)
    
    if not os.path.isdir(args.folder):
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)
    
    # Process the folder
    if args.append_to:
        # Upsert mode - load existing catalog and add/update
        if os.path.isfile(args.append_to):
            print(f"Loading existing catalog for upsert: {args.append_to}")
            with open(args.append_to, 'r', encoding='utf-8') as f:
                existing_catalog = json.load(f)
        else:
            print(f"Creating new catalog: {args.append_to}")
            existing_catalog = None
        
        # Process folder normally
        new_catalog = process_cookbook_folder(args.folder, args.model, None, args.retries, api_key, args.backup_model, args.sort_by)
        
        if "error" not in new_catalog:
            if existing_catalog:
                # Upsert all recipes from new catalog into existing
                all_new_recipes = new_catalog.get("recipes", [])
                all_new_chapters = new_catalog.get("chapters", [])
                
                updated_catalog, added, updated, merged = upsert_recipes(
                    existing_catalog, all_new_recipes, all_new_chapters
                )
                
                # Merge processing logs
                updated_catalog["processing_log"].extend(new_catalog.get("processing_log", []))
                
                # Save
                with open(args.append_to, 'w', encoding='utf-8') as f:
                    json.dump(updated_catalog, f, indent=2, ensure_ascii=False)
                
                print(f"\n✅ Catalog upserted: {args.append_to}")
                print(f"   Added: {added} recipe(s)")
                print(f"   Updated: {updated} recipe(s)")
                if merged > 0:
                    print(f"   Merged: {merged} recipe(s) (continuations combined)")
                print(f"   Total recipes: {len(updated_catalog['recipes'])}")
            else:
                # No existing catalog, just save the new one
                with open(args.append_to, 'w', encoding='utf-8') as f:
                    json.dump(new_catalog, f, indent=2, ensure_ascii=False)
                print(f"\nCatalog saved to: {args.append_to}")
    else:
        catalog = process_cookbook_folder(args.folder, args.model, args.output, args.retries, api_key, args.backup_model, args.sort_by)
        
        if "error" not in catalog:
            print("\nDone! Recipe catalog created successfully.")


if __name__ == "__main__":
    main()
