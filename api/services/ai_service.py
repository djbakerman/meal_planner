
from typing import List, Optional
import re
from backend import llm

def parse_servings_str(serves_str: str) -> float:
    """Extract a numeric serving size from string (e.g., '4', '4-6', 'makes 12')."""
    try:
        if not serves_str: return 4.0 # Default
        # Match first number
        match = re.search(r'(\d+)', str(serves_str))
        if match:
            return float(match.group(1))
    except:
        pass
    return 4.0 # Fallback

def scale_quantity(text: str, ratio: float) -> str:
    """
    Scale numbers in the ingredient text by the given ratio.
    Handles integers, decimals, and simple fractions (1/2, 1/4).
    """
    if ratio == 1.0:
        return text

    # Regex to find numbers: 
    # 1. Fractions: \d+\s*/\s*\d+
    # 2. Decimals/Integers: \d+(?:\.\d+)?
    # We use a pattern that captures these. 
    # Note: simple replacement of all numbers might affect things like "7up" or "V8", 
    # but in ingredient context, usually numbers are quantities.
    
    pattern = r'(?P<frac>\d+\s*/\s*\d+)|(?P<num>\d+(?:\.\d+)?)'
    
    def replace(match):
        g = match.groupdict()
        val = 0.0
        is_float = False
        
        if g['frac']:
            try:
                num, den = g['frac'].split('/')
                val = float(num) / float(den)
                is_float = True # Fractions become floats after scaling usually
            except:
                return match.group(0)
        elif g['num']:
            val = float(g['num'])
            is_float = '.' in g['num']

        new_val = val * ratio
        
        # Format back
        # If it was an integer and result is close to integer, keep as int
        if abs(new_val - round(new_val)) < 0.05:
            return str(int(round(new_val)))
        else:
            # Return as formatted float, max 2 decimals to keep it clean
            # The LLM is asked to clean up decimals later anyway
            return f"{new_val:.2f}".rstrip('0').rstrip('.')

    try:
        return re.sub(pattern, replace, text)
    except Exception as e:
        # Fallback if anything goes wrong, return original
        return text

def format_recipes_for_ai(recipes: List[dict], target_servings: int = None) -> str:
    """Format recipes for the AI prompt, including explicit scaling factors."""
    formatted = []
    
    for i, recipe in enumerate(recipes, 1):
        name = recipe.get("name", "Unknown")
        servings_str = recipe.get("serves", recipe.get("servings", "unknown"))
        
        # Calculate Ratio
        ratio = 1.0
        scaling_note = ""
        
        if target_servings:
            original_val = parse_servings_str(servings_str)
            if original_val > 0:
                ratio = round(target_servings / original_val, 2)
                if ratio != 1.0:
                    scaling_note = f" [Scaled from {int(original_val)} servings]"
        
        # DB 'ingredients' are list of objects with 'ingredient_text'
        ingredients = recipe.get("ingredients", [])
        
        # Format ingredients
        ing_list = []
        for ing in ingredients:
            text = ""
            if isinstance(ing, dict):
                text = ing.get("ingredient_text", ing.get("item", str(ing))) 
            elif hasattr(ing, "ingredient_text"):
                text = ing.ingredient_text
            else:
                text = str(ing)
            
            # Apply Scaling
            scaled_text = scale_quantity(text, ratio)
            ing_list.append(f"  - {scaled_text}")
        
        formatted.append(f"""
Recipe {i}: {name}{scaling_note}
Ingredients:
{chr(10).join(ing_list)}
""")
    
    return "\n".join(formatted)

def generate_grocery_list(recipes: List[dict], servings: int = 4, model: str = None) -> str:
    """
    Generate a consolidated grocery list using AI.
    """
    # Recipes are now pre-scaled by format_recipes_for_ai
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings)
    
    prompt = f"""I'm making these {len(recipes)} recipes for my meal plan. Please create a CONSOLIDATED grocery shopping list.
    
    Target Servings for the Plan: {servings} people.
    
    NOTE: The ingredients listed below have ALREADY been scaled to the target servings. 
    You do NOT need to do any math scaling. 
    Your job is to CONSOLIDATE duplicates.

IMPORTANT: Combine similar ingredients intelligently. For example:
- If 3 recipes each need "2 eggs", list "6 eggs" (NOT "2 eggs" three times)
- If 2 recipes need bread for sandwiches, list "1 loaf bread"
- If multiple recipes need chicken breast, sum the quantities found
- Group ingredients by store section (Produce, Meat, Dairy, Pantry, etc.)

Here are the recipes:
{recipes_text}

Please provide:
1. A consolidated grocery list organized by store section
2. Quantities that make sense for shopping.
3. IMPORTANT: Round numbers cleanly (Kitchen Style).
   - 🔴 NO DECIMALS: "0.33 cup" -> "⅓ cup", "0.04 tsp" -> "tiny pinch".
   - 🟢 ROUND UP/SMOOTH: "0.80 onions" -> "1 onion", "0.34 limes" -> "½ lime".

4. Skip common pantry staples that most people have (salt, pepper, basic oil) unless large amounts needed

Format the list clearly with sections and checkboxes (□)."""
    
    # Use default model from config if not specified
    response = llm.query_llm(prompt, model=model)
    return response

def generate_prep_plan(recipes: List[dict], servings: int = 4, model: str = None) -> str:
    """
    Generate a meal prep plan using AI.
    """
    # Recipies pre-scaled
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings)
    
    prompt = f"""I'm meal prepping these {len(recipes)} recipes for the week. I want to do ALL the prep work in one session so that during the week I just assemble and cook.
    
    Target Servings: {servings} people.
    NOTE: Ingredients below are ALREADY scaled to this target.

Here are the recipes:
{recipes_text}

Please create a CONSOLIDATED MEAL PREP PLAN that batches similar prep tasks together. 

IMPORTANT PRINCIPLES:
1. COMBINE similar prep tasks across recipes:
   - If 2 recipes need ½ chopped onion each, say "Chop 1 onion, store in container"
   - If 3 recipes need minced garlic, say "Mince 6 cloves garlic total, store together"
   
2. Group prep tasks by TYPE:
   - All chopping/dicing together
   - All sauce/marinade making together  
   - All protein prep (marinating, rubbing, portioning) together
   - All measuring of dry spices together

3. Note STORAGE instructions:
   - What goes in the fridge vs freezer
   - How long each prep will keep
   - Which preps should stay separate vs can be combined

4. Note TIME-SENSITIVE items:
   - Things that should be prepped day-of (like avocado)
   - Marinades that need X hours
   - Anything that doesn't store well

5. Create a PREP ORDER that's efficient:
   - Start with longest marinating items
   - Group by cutting board (veggies first, then meat)
   - End with items that are quick or need to stay fresh

6. FORMAT AS A CHECKLIST:
   - Use checkboxes (□) for all actionable tasks so I can check them off as I go.

FORMAT:
📋 MEAL PREP SESSION PLAN

⏱️ ESTIMATED TOTAL PREP TIME: X minutes

🥩 PROTEINS (do these first for marinating time)
- □ Task 1 (for Recipe X, Y)
- □ Task 2...

🔪 CHOPPING & DICING  
- □ Onions: chop X total (for Recipe A, B, C) - store in airtight container, fridge 5 days
- □ Garlic: mince X cloves total...
- etc.

🥣 SAUCES, MARINADES & SPICE MIXES
- □ Make X sauce (for Recipe Y) - store in jar, fridge 1 week
- □ Mix spice rub for... 
- etc.

📦 STORAGE CONTAINERS NEEDED
- □ X small containers for...
- □ X medium containers for...

⚠️ DAY-OF PREP (don't do ahead)
- □ Items that should wait...

🗓️ SUGGESTED COOK ORDER FOR THE WEEK
- Day 1: Recipe X (needs longest marinating)
- Day 2: Recipe Y...

FORMATTING RULES:
1. **NO DECIMALS**: Convert all decimals to standard fractions.
   - 0.33 or 0.34 → "⅓"
   - 0.66 or 0.67 → "⅔"
   - 0.25 → "¼"
   - 0.125 or 0.13 → "⅛"
   - 0.16 or 0.17 → "⅙" or "roughly ⅙"
   - 0.04 → "tiny pinch"

2. **NO MATH**: Do NOT show your calculations in the output.
   - 🔴 BAD: "0.34 lbs (0.17x 2 lbs)"
   - 🟢 GOOD: "⅓ lb"
   
3. **ROUND SMARTLY**:
   - "0.34 onions" -> "½ onion" (nobody buys 0.34 onions)
   - "0.80 limes" -> "1 lime"
"""

    return llm.query_llm(prompt, model=model)

def find_substitute(target_recipe: dict, candidates: List[dict], model: str = None) -> Optional[int]:
    """
    Identify the best substitute from candidates for the target recipe.
    Returns the ID of the best candidate.
    """
    # No scaling for substitution matching
    candidates_text = format_recipes_for_ai(candidates, target_servings=None)
    
    prompt = f"""I need to swap out a recipe in my meal plan: "{target_recipe.get('name')}".
    
I want a "Similar Swap" - something that fulfills a similar role or style (e.g. replacing a fish dish with another seafood dish, or a pasta with another pasta).

Here is the target recipe:
Name: {target_recipe.get('name')}
Description: {target_recipe.get('description')}
Ingredients: {target_recipe.get('ingredients')}

Here are the available candidates:
{candidates_text}

Task:
Select the SINGLE best substitute from the candidates list.
Return ONLY the ID of the selected recipe (e.g. "15"). 
If no good match exists, pick the one that is most similar in style.
"""
    
    response = llm.query_llm(prompt, model=model)
    
    # Clean response to get ID
    try:
        if not response:
            return None
        # Extract first number found
        import re
        match = re.search(r'\d+', response)
        if match:
            return int(match.group())
    except Exception as e:
        print(f"Error parsing AI response for substitute: {e}")
        
    return None

def generate_plan_name(recipes: List[dict], model: str = None) -> str:
    """
    Generate a creative name for the meal plan based on its recipes.
    """
    # No scaling for naming
    recipes_text = format_recipes_for_ai(recipes, target_servings=None)
    
    prompt = f"""Create a catchment, short, fun name for a meal plan containing these recipes:
{recipes_text}

Examples of good names:
- "Spicy Taco Week"
- "Comfort Food Classics"
- "Healthy Green Eats"
- "Italian Night & Leftovers"

Return ONLY the name. No quotes, no "Here is a name:", just the text of the name.
"""
    
    response = llm.query_llm(prompt, model=model)
    
    # Basic cleanup
    if response:
        return response.strip().strip('"').strip("'")
    
    return "Weekly Meal Plan"
