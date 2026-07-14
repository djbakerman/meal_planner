
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

def format_recipes_for_ai(recipes: List[dict], target_servings: int = None,
                          include_instructions: bool = False,
                          servings_map: dict = None) -> str:
    """Format recipes for the AI prompt, including explicit scaling factors.

    servings_map: optional {recipe_id: total_servings_needed} override, used by
    weekly plans where each recipe is eaten a different number of times.
    """
    formatted = []

    for i, recipe in enumerate(recipes, 1):
        name = recipe.get("name", "Unknown")
        servings_str = recipe.get("serves", recipe.get("servings", "unknown"))

        # Calculate Ratio
        ratio = 1.0
        scaling_note = ""

        effective_target = target_servings
        if servings_map is not None and recipe.get("id") in servings_map:
            effective_target = servings_map[recipe.get("id")]

        if effective_target:
            original_val = parse_servings_str(servings_str)
            if original_val > 0:
                ratio = round(effective_target / original_val, 2)
                if ratio != 1.0:
                    scaling_note = f" [Scaled from {int(original_val)} servings to {effective_target:g}]"
        
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

        if include_instructions and recipe.get("instructions"):
            inst_list = recipe.get("instructions", [])
            if inst_list:
                formatted.append("Instructions:")
                formatted.append("\n".join(inst_list))
                formatted.append("\n")

        # Handle Sub-recipes
        sub_recipes = recipe.get("sub_recipes", [])
        if sub_recipes:
            for sub_i, sub in enumerate(sub_recipes, 1):
                sub_name = sub.get("name", "Unknown Sub-recipe")
                sub_ings = sub.get("ingredients", [])
                
                # Format sub-recipe ingredients
                sub_ing_list = []
                for ing in sub_ings:
                    # Apply same scaling ratio as parent
                    scaled_sub_text = scale_quantity(str(ing), ratio)
                    sub_ing_list.append(f"  - {scaled_sub_text}")
                
                formatted.append(f"""
Recipe {i}.{sub_i}: {sub_name} (Component of {name})
Ingredients:
{chr(10).join(sub_ing_list)}
""")
                if include_instructions and sub.get("instructions"):
                    s_inst = sub.get("instructions", [])
                    if s_inst:
                        formatted.append("Instructions:")
                        formatted.append("\n".join(s_inst))
                        formatted.append("\n")

    return "\n".join(formatted)

def generate_grocery_list(recipes: List[dict], servings: int = 4, model: str = None,
                          servings_map: dict = None, week_context: str = None) -> str:
    """
    Generate a consolidated grocery list using AI.
    """
    # Recipes are now pre-scaled by format_recipes_for_ai
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings,
                                         servings_map=servings_map)

    context_block = f"\nPLAN CONTEXT:\n{week_context}\n" if week_context else ""

    prompt = f"""I'm making these {len(recipes)} recipes for my meal plan. Please create a CONSOLIDATED grocery shopping list.

    Target Servings for the Plan: {servings} people.
    {context_block}
    NOTE: The ingredients listed below have ALREADY been scaled to the servings needed.
    You do NOT need to do any math scaling.
    Your job is to CONSOLIDATE duplicates.

IMPORTANT: Combine similar ingredients intelligently. For example:
- If 3 recipes each need "2 eggs", list "6 eggs" (NOT "2 eggs" three times)
- If 2 recipes need bread for sandwiches, list "1 loaf bread"
- Convert measured/liquid produce into whole produce shopping equivalents (e.g. "2 tbsp lemon juice" -> "1 lemon", "1 cup chopped onion" -> "1 large onion").
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

4. BUY REAL PACKAGES: round every quantity UP to the smallest package a store actually
   sells, and never list an amount below a purchasable unit.
   - 🔴 BAD: "Scallops - 1.4 oz", "Sirloin - 1.5 oz", "Barramundi - 0.06 lb"
   - 🟢 GOOD: "Scallops - ½ lb (smallest counter order; freeze the rest)"
   - When rounding up creates meaningful leftover, add a short "(leftover: ~X, freezes well)" note.

5. Skip common pantry staples that most people have (salt, pepper, basic oil) unless large amounts needed

6. If an ingredient's total across the whole week is still a trivial amount (under a teaspoon),
   fold it into a single "check the spice rack" line at the end instead of the shopping sections.

Format the list clearly with sections and checkboxes (□)."""

    # Use default model from config if not specified
    response = llm.query_llm(prompt, model=model)
    return response

def generate_prep_plan(recipes: List[dict], servings: int = 4, model: str = None,
                       servings_map: dict = None, week_context: str = None) -> str:
    """
    Generate a meal prep plan using AI.
    """
    # Recipes pre-scaled
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings,
                                         include_instructions=True,
                                         servings_map=servings_map)

    context_block = f"\nPLAN CONTEXT (use this to organize the week):\n{week_context}\n" if week_context else ""

    prompt = f"""I'm meal prepping these {len(recipes)} recipes for the week. I want ONE efficient Sunday batch session, then minimal day-of work.

    Target Servings: {servings} people.
    NOTE: Ingredients below are ALREADY scaled to the servings needed.
    {context_block}
Here are the recipes:
{recipes_text}

Please create a MEAL PREP PLAN split into a SUNDAY BATCH SESSION and short DAY-OF notes.

IMPORTANT PRINCIPLES:
1. COMBINE similar prep tasks across recipes:
   - If 2 recipes need ½ chopped onion each, say "Chop 1 onion, store in container"
   - If 3 recipes need minced garlic, say "Mince 6 cloves garlic total, store together"

2. BE CONCISE: one line per task. No step-by-step cooking lessons - I can read
   the recipe when cooking. The prep plan is a checklist, not a cookbook.

3. If the plan context shows dinners that roll into next-day lunches, treat each
   as ONE cook event producing two portions - remind me to box the lunch portion
   before serving dinner.

4. Note STORAGE (fridge/freezer, keeps X days) inline, in parentheses.

5. Note TIME-SENSITIVE items (marinades needing hours; avocado and pear day-of only).

FORMAT (exactly this structure):
📋 MEAL PREP PLAN

⏱️ SUNDAY BATCH: about X minutes total

🥩 PROTEINS & MARINADES (Sunday)
- □ One-line task (Recipe names) (storage note)

🔪 CHOP & PORTION (Sunday)
- □ One-line task (Recipe names) (storage note)

🥣 SAUCES & MIXES (Sunday)
- □ One-line task (Recipe names) (storage note)

🗓️ DAY-OF (5-15 minutes each day)
- □ Monday: cook X for dinner (double portion - box half for Tuesday lunch); assemble Y
- □ Tuesday: ...one line per day...

⚠️ DON'T PREP AHEAD
- □ Item - reason (three words max)

FORMATTING RULES:
1. **NO DECIMALS**: 0.33 -> "⅓", 0.25 -> "¼", 0.04 -> "tiny pinch".
2. **NO MATH shown**: "⅓ lb", never "0.34 lbs (0.17x 2 lbs)".
3. **ROUND SMARTLY**: "0.34 onions" -> "½ onion", "0.80 limes" -> "1 lime".
4. Keep the whole plan under 60 lines. Shakes and no-cook snacks need no prep
   lines unless something must be portioned ahead.
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
