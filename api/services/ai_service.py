
from typing import List, Optional
from backend import llm

def parse_servings_str(serves_str: str) -> float:
    """Extract a numeric serving size from string (e.g., '4', '4-6', 'makes 12')."""
    try:
        if not serves_str: return 4.0 # Default
        import re
        # Match first number
        match = re.search(r'(\d+)', str(serves_str))
        if match:
            return float(match.group(1))
    except:
        pass
    return 4.0 # Fallback

def format_recipes_for_ai(recipes: List[dict], target_servings: int = None) -> str:
    """Format recipes for the AI prompt, including explicit scaling factors."""
    formatted = []
    
    for i, recipe in enumerate(recipes, 1):
        name = recipe.get("name", "Unknown")
        servings_str = recipe.get("serves", recipe.get("servings", "unknown"))
        
        # Calculate Ratio
        scaling_info = ""
        if target_servings:
            original_val = parse_servings_str(servings_str)
            if original_val > 0:
                ratio = round(target_servings / original_val, 2)
                if ratio != 1.0:
                    scaling_info = f"\nSCALING REQUIRED: Target {target_servings} / Original {int(original_val)} = {ratio}x multiplier.\nPLEASE MULTIPLY ALL INGREDIENTS BY {ratio}."
        
        # DB 'ingredients' are list of objects with 'ingredient_text'
        ingredients = recipe.get("ingredients", [])
        
        # Format ingredients
        ing_list = []
        for ing in ingredients:
            if isinstance(ing, dict):
                text = ing.get("ingredient_text", ing.get("item", str(ing))) 
                ing_list.append(f"  - {text}")
            elif hasattr(ing, "ingredient_text"):
                ing_list.append(f"  - {ing.ingredient_text}")
            else:
                ing_list.append(f"  - {ing}")
        
        formatted.append(f"""
Recipe {i}: {name}
Original Servings: {servings_str}{scaling_info}
Ingredients:
{chr(10).join(ing_list)}
""")
    
    return "\n".join(formatted)

def generate_grocery_list(recipes: List[dict], servings: int = 4, model: str = None) -> str:
    """
    Generate a consolidated grocery list using AI.
    """
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings)
    
    prompt = f"""I'm making these {len(recipes)} recipes for my meal plan. Please create a CONSOLIDATED grocery shopping list.
    
    Target Servings for the Plan: {servings} people.
    Note: Some recipes might be for a different number of servings. Please scale ingredient quantities intelligently to match the target of {servings} servings.

IMPORTANT: Combine similar ingredients intelligently. For example:
- If 3 recipes each need "2 eggs", list "6 eggs" (not "2 eggs" three times)
- If 2 recipes need bread for sandwiches, list "1 loaf bread" (not "bread" twice)
- If multiple recipes need chicken breast, estimate total pounds needed
- Group ingredients by store section (Produce, Meat, Dairy, Pantry, etc.)

Here are the recipes:
{recipes_text}

Please provide:
1. A consolidated grocery list organized by store section
2. Quantities that make sense for shopping.
3. IMPORTANT: Round up to the nearest whole purchase unit for produce/packaged goods (e.g., buy '1 Onion' not '0.5 Onion', '1 pack' not '0.3 pack'). Use exact measurements for bulk items (flour, rice).
4. Skip common pantry staples that most people have (salt, pepper, basic oil) unless large amounts needed

Format the list clearly with sections and checkboxes (□)."""
    
    # Use default model from config if not specified
    response = llm.query_llm(prompt, model=model)
    return response

def generate_prep_plan(recipes: List[dict], servings: int = 4, model: str = None) -> str:
    """
    Generate a meal prep plan using AI.
    """
    recipes_text = format_recipes_for_ai(recipes, target_servings=servings)
    
    prompt = f"""I'm meal prepping these {len(recipes)} recipes for the week. I want to do ALL the prep work in one session so that during the week I just assemble and cook.
    
    Target Servings: {servings} people. Scale prep tasks accordingly.

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

FORMAT:
📋 MEAL PREP SESSION PLAN

⏱️ ESTIMATED TOTAL PREP TIME: X minutes

🥩 PROTEINS (do these first for marinating time)
- Task 1 (for Recipe X, Y)
- Task 2...

🔪 CHOPPING & DICING  
- Onions: chop X total (for Recipe A, B, C) - store in airtight container, fridge 5 days
- Garlic: mince X cloves total...
- etc.

🥣 SAUCES, MARINADES & SPICE MIXES
- Make X sauce (for Recipe Y) - store in jar, fridge 1 week
- Mix spice rub for... 
- etc.

📦 STORAGE CONTAINERS NEEDED
- X small containers for...
- X medium containers for...

⚠️ DAY-OF PREP (don't do ahead)
- Items that should wait...

🗓️ SUGGESTED COOK ORDER FOR THE WEEK
- Day 1: Recipe X (needs longest marinating)
- Day 2: Recipe Y...
"""

    return llm.query_llm(prompt, model=model)

def find_substitute(target_recipe: dict, candidates: List[dict], model: str = None) -> Optional[int]:
    """
    Identify the best substitute from candidates for the target recipe.
    Returns the ID of the best candidate.
    """
    candidates_text = format_recipes_for_ai(candidates)
    
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
    recipes_text = format_recipes_for_ai(recipes)
    
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
