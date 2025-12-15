#!/usr/bin/env python3
"""
Meal Planner - Randomly select recipes from a catalog and use AI to generate 
a consolidated grocery list.

The AI intelligently combines ingredients across recipes (e.g., 5 sandwiches = 1 loaf of bread).
"""

import json
import os
import sys
import argparse
import random
from typing import Optional, List, Dict
from pathlib import Path
import requests

# API endpoints
OLLAMA_API_URL = "http://localhost:11434/api/generate"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Default state file location (central location in home directory)
DEFAULT_STATE_FILE = os.path.expanduser("~/.meal_plan_state.json")

# Known Claude models
CLAUDE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514", 
    "claude-3-5-sonnet-20241022",
    "claude-3-opus-20240229",
    "claude-3-haiku-20240307"
]


def get_state_file_path(catalog_path: str = None) -> str:
    """Get the state file path - always uses central location in home directory."""
    return DEFAULT_STATE_FILE


def save_state(state_file: str, recipes: List[dict], meal_type: str, catalogs: List[str] = None):
    """Save current meal plan state to file."""
    from datetime import datetime
    state = {
        "meal_type": meal_type,
        "recipes": recipes,
        "recipe_names": [r.get("name", "Unknown") for r in recipes],
        "created": datetime.now().isoformat(),
        "catalogs": catalogs or []
    }
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_state(state_file: str) -> Optional[dict]:
    """Load saved meal plan state from file."""
    if not os.path.isfile(state_file):
        return None
    try:
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def find_recipe_by_name(recipes: List[dict], name: str) -> Optional[dict]:
    """Find a recipe by name (case-insensitive partial match)."""
    name_lower = name.lower()
    
    # Try exact match first
    for recipe in recipes:
        if recipe.get("name", "").lower() == name_lower:
            return recipe
    
    # Try partial match
    for recipe in recipes:
        if name_lower in recipe.get("name", "").lower():
            return recipe
    
    return None


def print_recipe_details(recipe: dict):
    """Print full recipe details including ingredients and instructions."""
    print("\n" + "=" * 60)
    print(f"📖 {recipe.get('name', 'Unknown Recipe')}")
    print("=" * 60)
    
    # Basic info
    chapter = recipe.get("chapter", "")
    page = recipe.get("page_number", "")
    servings = recipe.get("serves", recipe.get("servings", ""))
    prep_time = recipe.get("prep_time", "")
    cook_time = recipe.get("cook_time", "")
    total_time = recipe.get("total_time", "")
    dietary = recipe.get("dietary_info", [])
    
    if chapter:
        print(f"\n📚 Chapter: {chapter}")
    if page:
        print(f"📄 Page: {page}")
    if servings:
        print(f"👥 Servings: {servings}")
    
    times = []
    if prep_time:
        times.append(f"Prep: {prep_time}")
    if cook_time:
        times.append(f"Cook: {cook_time}")
    if total_time:
        times.append(f"Total: {total_time}")
    if times:
        print(f"⏱️  {', '.join(times)}")
    
    if dietary and dietary != ['']:
        print(f"🏷️  {', '.join([d for d in dietary if d])}")
    
    # Nutrition
    calories = recipe.get("calories", "")
    protein = recipe.get("protein", "")
    carbs = recipe.get("carbs", "")
    fat = recipe.get("fat", "")
    if any([calories, protein, carbs, fat]):
        nutrition = []
        if calories:
            nutrition.append(f"{calories} cal")
        if protein:
            nutrition.append(f"{protein} protein")
        if carbs:
            nutrition.append(f"{carbs} carbs")
        if fat:
            nutrition.append(f"{fat} fat")
        print(f"🔢 {', '.join(nutrition)}")
    
    # Ingredients
    ingredients = recipe.get("ingredients", [])
    if ingredients:
        print(f"\n🥗 INGREDIENTS ({len(ingredients)} items)")
        print("-" * 40)
        for ing in ingredients:
            if isinstance(ing, dict):
                item = ing.get("item", ing.get("name", str(ing)))
                amount = ing.get("amount", ing.get("quantity", ""))
                if amount:
                    print(f"  • {amount} {item}")
                else:
                    print(f"  • {item}")
            else:
                print(f"  • {ing}")
    
    # Instructions
    instructions = recipe.get("instructions", [])
    if instructions:
        print(f"\n👨‍🍳 INSTRUCTIONS ({len(instructions)} steps)")
        print("-" * 40)
        for i, step in enumerate(instructions, 1):
            if isinstance(step, dict):
                step_text = step.get("step", step.get("text", str(step)))
            else:
                step_text = str(step)
            print(f"  {i}. {step_text}")
    
    print("\n" + "=" * 60)


def is_claude_model(model: str) -> bool:
    """Check if the model is a Claude model."""
    return any(cm in model for cm in CLAUDE_MODELS) or model.startswith("claude-")


def query_ollama(prompt: str, model: str) -> Optional[str]:
    """Send a text prompt to Ollama."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 4096
        }
    }
    
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=180)
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Ollama at {OLLAMA_API_URL}")
        return None
    except Exception as e:
        print(f"Error querying Ollama: {e}")
        return None


def query_claude(prompt: str, model: str, api_key: str) -> Optional[str]:
    """Send a text prompt to Claude API."""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(CLAUDE_API_URL, headers=headers, json=payload, timeout=180)
        
        if response.status_code != 200:
            print(f"Error: Claude API returned {response.status_code}: {response.text[:200]}")
            return None
        
        result = response.json()
        return result.get("content", [{}])[0].get("text", "")
    except Exception as e:
        print(f"Error querying Claude: {e}")
        return None


def query_llm(prompt: str, model: str, api_key: str = None) -> Optional[str]:
    """Query either Ollama or Claude based on model name."""
    if is_claude_model(model):
        if not api_key:
            print("Error: Claude API key required. Set ANTHROPIC_API_KEY or use --api-key")
            return None
        return query_claude(prompt, model, api_key)
    else:
        return query_ollama(prompt, model)


def load_catalog(catalog_paths) -> Optional[dict]:
    """Load and validate one or more recipe catalogs, merging them if multiple."""
    # Handle single path or list of paths
    if isinstance(catalog_paths, str):
        catalog_paths = [catalog_paths]
    
    all_recipes = []
    all_chapters = []
    source_catalogs = []
    
    for catalog_path in catalog_paths:
        if not os.path.isfile(catalog_path):
            print(f"Error: Catalog not found: {catalog_path}")
            return None
        
        try:
            with open(catalog_path, 'r', encoding='utf-8') as f:
                catalog = json.load(f)
            
            recipes = catalog.get("recipes", [])
            chapters = catalog.get("chapters", [])
            
            if recipes:
                # Add source catalog info to each recipe
                for recipe in recipes:
                    recipe["_source_catalog"] = catalog_path
                all_recipes.extend(recipes)
                print(f"📚 Loaded {len(recipes)} recipes from {catalog_path}")
            
            if chapters:
                all_chapters.extend(chapters)
            
            source_catalogs.append(catalog_path)
            
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in {catalog_path}: {e}")
            return None
    
    if not all_recipes:
        print("Error: No recipes found in any catalog")
        return None
    
    print(f"📊 Total: {len(all_recipes)} recipes from {len(source_catalogs)} catalog(s)")
    
    return {
        "recipes": all_recipes,
        "chapters": all_chapters,
        "source_catalogs": source_catalogs
    }


def get_meal_type(recipe: dict) -> str:
    """
    Get meal type from recipe. Uses meal_type field if present, otherwise infers from chapter/name.
    Returns: 'breakfast', 'lunch', 'dinner', 'dessert', 'snack', or 'any'
    """
    # First check if meal_type was set by the AI during extraction
    stored_meal_type = recipe.get("meal_type", "").lower()
    if stored_meal_type in ["breakfast", "lunch", "dinner", "any", "dessert", "snack"]:
        return stored_meal_type
    
    # Fallback: infer from chapter and name
    chapter = recipe.get("chapter", "").lower()
    name = recipe.get("name", "").lower()
    
    # Check chapter first - be specific about non-meal categories
    if any(kw in chapter for kw in ["dessert", "sweets", "baking", "cake", "cookie", "pie"]):
        return "dessert"
    if any(kw in chapter for kw in ["snack", "shake", "smoothie", "bar", "bite"]):
        return "snack"
    if any(kw in chapter for kw in ["appetizer", "starter"]):
        return "appetizer"
    if any(kw in chapter for kw in ["breakfast", "brunch", "morning"]):
        return "breakfast"
    if any(kw in chapter for kw in ["lunch", "sandwiches"]):
        return "lunch"
    if any(kw in chapter for kw in ["dinner", "entrees", "mains", "main dishes", "suppers"]):
        return "dinner"
    if any(kw in chapter for kw in ["sides", "side dishes", "vegetables"]):
        return "side"
    
    # Check recipe name for specific categories
    dessert_keywords = ["cake", "cookie", "brownie", "pie", "tart", "cheesecake", "pudding", 
                       "ice cream", "mousse", "custard", "crisp", "cobbler", "fudge", "truffle"]
    if any(kw in name for kw in dessert_keywords):
        return "dessert"
    
    snack_keywords = ["bar", "bite", "ball", "shake", "smoothie", "snack", "chip", "cracker"]
    if any(kw in name for kw in snack_keywords):
        return "snack"
    
    breakfast_keywords = ["pancake", "waffle", "omelet", "omelette", "french toast", 
                         "scramble", "hash", "breakfast", "muffin", "granola", "oatmeal"]
    if any(kw in name for kw in breakfast_keywords):
        return "breakfast"
    
    # Check for main dish indicators - these should be dinner/lunch candidates
    main_keywords = ["steak", "roast", "chicken", "beef", "pork", "fish", "salmon", "shrimp",
                    "pasta", "lasagna", "casserole", "curry", "stir fry", "soup", "stew"]
    if any(kw in name for kw in main_keywords):
        return "dinner"
    
    # Salads can go either way
    if "salad" in name or "salad" in chapter:
        return "any"
    
    return "any"


def get_dish_role(recipe: dict) -> str:
    """
    Get dish role from recipe. Uses dish_role field if present, otherwise infers.
    Returns: 'main', 'side', or 'sub_recipe'
    """
    # First check if dish_role was set by the AI during extraction
    stored_role = recipe.get("dish_role", "").lower()
    if stored_role in ["main", "side", "sub_recipe"]:
        return stored_role
    
    # Fallback: infer from chapter and name
    chapter = recipe.get("chapter", "").lower()
    name = recipe.get("name", "").lower()
    
    # Sub-recipes: dressings, sauces, marinades, spice blends
    sub_recipe_keywords = ["dressing", "vinaigrette", "sauce", "marinade", "rub", 
                          "spice blend", "seasoning", "aioli", "pesto", "salsa"]
    if any(kw in name for kw in sub_recipe_keywords):
        return "sub_recipe"
    
    # Sides: vegetables, slaws, side dishes
    if any(kw in chapter for kw in ["sides", "side dishes", "vegetables", "slaws"]):
        return "side"
    
    # Most other things are mains
    return "main"


def filter_recipes(recipes: List[dict], meal_types: List[str], include_sides: bool = False) -> List[dict]:
    """
    Filter recipes by meal type(s).
    
    Args:
        recipes: List of recipes to filter
        meal_types: List of meal types like ['breakfast'], ['lunch', 'dinner'], or ['any']
        include_sides: If True, include side dishes in results
    """
    # Normalize to list
    if isinstance(meal_types, str):
        meal_types = [meal_types]
    
    if "any" in meal_types:
        # Return all except sub_recipes, desserts, and snacks
        return [r for r in recipes 
                if get_dish_role(r) != "sub_recipe" 
                and get_meal_type(r) not in ["dessert", "snack"]]
    
    filtered = []
    for recipe in recipes:
        dish_role = get_dish_role(recipe)
        recipe_meal = get_meal_type(recipe)
        
        # Skip sub_recipes (dressings, marinades, etc.) - they're not standalone meals
        if dish_role == "sub_recipe":
            continue
        
        # Skip desserts and snacks unless explicitly requested
        if recipe_meal in ["dessert", "snack"] and recipe_meal not in meal_types:
            continue
        
        # Skip sides unless include_sides is True
        if dish_role == "side" and not include_sides:
            continue
        
        # Direct match with any requested meal type
        if recipe_meal in meal_types:
            filtered.append(recipe)
        # "any" recipes can be used for lunch or dinner (but not breakfast)
        elif recipe_meal == "any" and any(mt in ["lunch", "dinner"] for mt in meal_types):
            filtered.append(recipe)
        # Sides can go with lunch or dinner if include_sides
        elif dish_role == "side" and include_sides and any(mt in ["lunch", "dinner"] for mt in meal_types):
            filtered.append(recipe)
    
    if not filtered:
        meal_str = ", ".join(meal_types)
        print(f"  ⚠️  No specific {meal_str} recipes found, selecting from all (excluding desserts, snacks, sub-recipes)")
        return [r for r in recipes 
                if get_dish_role(r) != "sub_recipe" 
                and get_meal_type(r) not in ["dessert", "snack"]]
    
    return filtered


def select_random_recipes(recipes: List[dict], count: int, meal_types: List[str]) -> List[dict]:
    """Select random recipes filtered by meal type(s)."""
    available = filter_recipes(recipes, meal_types)
    
    meal_str = ", ".join(meal_types) if isinstance(meal_types, list) else meal_types
    print(f"  Found {len(available)} {meal_str} recipes")
    
    if len(available) <= count:
        return available
    
    return random.sample(available, count)


def format_recipes_for_ai(recipes: List[dict]) -> str:
    """Format recipes for the AI prompt."""
    formatted = []
    
    for i, recipe in enumerate(recipes, 1):
        name = recipe.get("name", "Unknown")
        servings = recipe.get("serves", recipe.get("servings", "unknown"))
        ingredients = recipe.get("ingredients", [])
        
        # Format ingredients
        ing_list = []
        for ing in ingredients:
            if isinstance(ing, dict):
                item = ing.get("item", ing.get("name", str(ing)))
                amount = ing.get("amount", ing.get("quantity", ""))
                if amount:
                    ing_list.append(f"  - {amount} {item}")
                else:
                    ing_list.append(f"  - {item}")
            else:
                ing_list.append(f"  - {ing}")
        
        formatted.append(f"""
Recipe {i}: {name}
Servings: {servings}
Ingredients:
{chr(10).join(ing_list)}
""")
    
    return "\n".join(formatted)


def generate_grocery_list_with_ai(recipes: List[dict], model: str, api_key: str = None) -> Optional[str]:
    """Use AI to generate a consolidated grocery list."""
    
    recipes_text = format_recipes_for_ai(recipes)
    
    prompt = f"""I'm making these {len(recipes)} recipes for my meal plan. Please create a CONSOLIDATED grocery shopping list.

IMPORTANT: Combine similar ingredients intelligently. For example:
- If 3 recipes each need "2 eggs", list "6 eggs" (not "2 eggs" three times)
- If 2 recipes need bread for sandwiches, list "1 loaf bread" (not "bread" twice)
- If multiple recipes need chicken breast, estimate total pounds needed
- Group ingredients by store section (Produce, Meat, Dairy, Pantry, etc.)

Here are the recipes:
{recipes_text}

Please provide:
1. A consolidated grocery list organized by store section
2. Quantities that make sense for shopping (e.g., "1 bunch cilantro" not "2 tablespoons cilantro")
3. Skip common pantry staples that most people have (salt, pepper, basic oil) unless large amounts needed

Format the list clearly with sections and checkboxes (□)."""

    print("\n🤖 Generating consolidated grocery list...")
    return query_llm(prompt, model, api_key)


def generate_meal_prep_plan_with_ai(recipes: List[dict], model: str, api_key: str = None) -> Optional[str]:
    """Use AI to generate a consolidated meal prep plan (mise en place for the week)."""
    
    recipes_text = format_recipes_for_ai(recipes)
    
    prompt = f"""I'm meal prepping these {len(recipes)} recipes for the week. I want to do ALL the prep work in one session so that during the week I just assemble and cook.

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

    print("\n🤖 Generating meal prep plan...")
    return query_llm(prompt, model, api_key)


def print_meal_plan(recipes: List[dict], meal_type: str):
    """Print the meal plan."""
    print("\n" + "=" * 60)
    print(f"🍽️  MEAL PLAN - {meal_type.upper()} ({len(recipes)} meals)")
    print("=" * 60)
    
    for i, recipe in enumerate(recipes, 1):
        name = recipe.get("name", "Unknown")
        chapter = recipe.get("chapter", "")
        page = recipe.get("page_number", "")
        servings = recipe.get("serves", recipe.get("servings", ""))
        prep_time = recipe.get("prep_time", "")
        cook_time = recipe.get("cook_time", "")
        dietary = recipe.get("dietary_info", [])
        
        print(f"\n{i}. {name}")
        if chapter:
            print(f"   📖 {chapter}", end="")
            if page:
                print(f" (p. {page})")
            else:
                print()
        if servings:
            print(f"   👥 Serves: {servings}")
        if prep_time or cook_time:
            times = []
            if prep_time:
                times.append(f"Prep: {prep_time}")
            if cook_time:
                times.append(f"Cook: {cook_time}")
            print(f"   ⏱️  {', '.join(times)}")
        if dietary and dietary != ['']:
            print(f"   🏷️  {', '.join([d for d in dietary if d])}")


def interactive_mode(catalog: dict, model: str, api_key: str = None, state_file: str = None):
    """Interactive meal planning session."""
    recipes = catalog.get("recipes", [])
    current_plan = []
    current_meal_type = "any"
    
    # Try to load existing state
    if state_file:
        saved_state = load_state(state_file)
        if saved_state:
            current_plan = saved_state.get("recipes", [])
            current_meal_type = saved_state.get("meal_type", "any")
            print(f"📂 Loaded saved meal plan ({len(current_plan)} recipes)")
    
    print("\n" + "=" * 60)
    print("🍳 INTERACTIVE MEAL PLANNER")
    print("=" * 60)
    print(f"\nUsing model: {model}")
    print("\nCommands:")
    print("  plan <meal_type> [count]  - Generate NEW meal plan")
    print("      meal_type: breakfast, lunch, dinner, any")
    print("      count: number of recipes (default: 5)")
    print("  show                      - Show current meal plan")
    print("  recipe <name|number|all>  - Show recipe details")
    print("  grocery                   - Generate AI grocery list")
    print("  prep                      - Generate AI meal prep plan")
    print("  reroll <number>           - Replace a recipe")
    print("  save <filename>           - Export plan to file")
    print("  quit                      - Exit")
    print("-" * 60)
    
    if current_plan:
        print(f"\n📋 Current plan has {len(current_plan)} recipes. Type 'show' to see them.")
    
    while True:
        try:
            user_input = input("\nmeal-planner> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! 👋")
            break
        
        if not user_input:
            continue
        
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        
        if command in ["quit", "exit", "q"]:
            print("Goodbye! 👋")
            break
        
        elif command == "plan":
            sub_parts = parts[1].split() if len(parts) > 1 else []
            meal_type = sub_parts[0] if len(sub_parts) > 0 else "any"
            count = int(sub_parts[1]) if len(sub_parts) > 1 else 5
            
            if meal_type not in ["breakfast", "lunch", "dinner", "any"]:
                print(f"Unknown meal type: {meal_type}")
                continue
            
            print(f"\n🎲 Selecting {count} random {meal_type} recipes...")
            current_plan = select_random_recipes(recipes, count, meal_type)
            current_meal_type = meal_type
            
            # Save state
            if state_file:
                save_state(state_file, current_plan, meal_type)
            
            print_meal_plan(current_plan, meal_type)
            print("\n💡 Type 'grocery' for shopping list, 'prep' for meal prep plan")
        
        elif command == "show":
            if current_plan:
                print_meal_plan(current_plan, current_meal_type)
            else:
                print("No meal plan yet. Use 'plan <meal_type>' first.")
        
        elif command == "recipe":
            if not current_plan:
                print("No meal plan yet. Use 'plan <meal_type>' first.")
                continue
            
            if len(parts) < 2:
                print("Usage: recipe <name|number|all>")
                continue
            
            recipe_arg = parts[1].strip()
            
            if recipe_arg.lower() == "all":
                # List all recipes
                print("\n📋 Recipes in current plan:")
                for i, r in enumerate(current_plan, 1):
                    print(f"  {i}. {r.get('name', 'Unknown')}")
                print("\nUse 'recipe <number>' or 'recipe <name>' for details")
            else:
                # Try as number first
                try:
                    idx = int(recipe_arg) - 1
                    if 0 <= idx < len(current_plan):
                        print_recipe_details(current_plan[idx])
                    else:
                        print(f"Invalid number. Use 1-{len(current_plan)}")
                except ValueError:
                    # Try as name
                    recipe = find_recipe_by_name(current_plan, recipe_arg)
                    if recipe:
                        print_recipe_details(recipe)
                    else:
                        print(f"Recipe '{recipe_arg}' not found. Use 'recipe all' to see list.")
        
        elif command == "grocery":
            if not current_plan:
                print("Generate a plan first with 'plan <meal_type>'")
                continue
            
            grocery_list = generate_grocery_list_with_ai(current_plan, model, api_key)
            if grocery_list:
                print("\n" + "=" * 60)
                print("🛒 GROCERY LIST")
                print("=" * 60)
                print(grocery_list)
        
        elif command == "prep":
            if not current_plan:
                print("Generate a plan first with 'plan <meal_type>'")
                continue
            
            prep_plan = generate_meal_prep_plan_with_ai(current_plan, model, api_key)
            if prep_plan:
                print("\n" + "=" * 60)
                print("📋 MEAL PREP PLAN")
                print("=" * 60)
                print(prep_plan)
        
        elif command == "reroll":
            if not current_plan:
                print("Generate a plan first with 'plan <meal_type>'")
                continue
            
            if len(parts) < 2:
                print("Usage: reroll <number>")
                continue
            
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(current_plan):
                    # Get a new random recipe excluding current ones
                    exclude_names = [r.get("name", "").lower() for r in current_plan]
                    available = [r for r in recipes if r.get("name", "").lower() not in exclude_names]
                    
                    if available:
                        old_name = current_plan[idx].get("name")
                        new_recipe = random.choice(available)
                        current_plan[idx] = new_recipe
                        
                        # Save updated state
                        if state_file:
                            save_state(state_file, current_plan, current_meal_type)
                        
                        print(f"🔄 Replaced '{old_name}' with '{new_recipe.get('name')}'")
                    else:
                        print("No other recipes available")
                else:
                    print(f"Invalid number. Use 1-{len(current_plan)}")
            except ValueError:
                print("Please provide a valid number")
        
        elif command == "save":
            if not current_plan:
                print("Generate a plan first with 'plan <meal_type>'")
                continue
            
            filename = parts[1].strip() if len(parts) > 1 else "meal_plan.json"
            if not filename.endswith(".json"):
                filename += ".json"
            
            save_data = {
                "meal_type": current_meal_type,
                "recipes": current_plan,
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"💾 Exported to: {filename}")
        
        else:
            print(f"Unknown command: {command}")
            print("Commands: plan, show, recipe, grocery, prep, reroll, save, quit")


def main():
    parser = argparse.ArgumentParser(
        description="Meal Planner - Select random recipes and generate AI-consolidated grocery lists",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate NEW meal plan (5 dinner recipes)
  python meal_planner.py -c catalog.json --meal dinner -m claude-sonnet-4-20250514 --new
  
  # Use SAVED plan - just show grocery list
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --grocery-list
  
  # Use SAVED plan - show meal prep plan  
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --meal-prep
  
  # List all recipes in saved plan
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --recipe all
  
  # Show specific recipe details
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --recipe "beef stroganoff"
  
  # Generate BOTH grocery list AND meal prep plan
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --grocery-list --meal-prep
  
  # Interactive mode
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 -i
  
  # Export plan to file
  python meal_planner.py -c catalog.json -m claude-sonnet-4-20250514 --save weekly.json
  
  # View saved meal plan (no catalog or model needed)
  python meal_planner.py -s              # Show saved meal plan
  python meal_planner.py -s 3            # Show recipe #3 from plan
  python meal_planner.py -s "Salisbury"  # Show recipe by name
        """
    )
    
    parser.add_argument(
        "-s", "--show",
        nargs="?",
        const="all",
        metavar="RECIPE",
        help="Show saved meal plan. Optional: recipe number or name to show details"
    )
    parser.add_argument(
        "-c", "--catalog",
        nargs="+",
        help="Path to one or more recipe catalog JSON files"
    )
    parser.add_argument(
        "-m", "--model",
        help="Model for AI grocery list (e.g., claude-sonnet-4-20250514 or llama3.2)"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key for Claude (or set ANTHROPIC_API_KEY)"
    )
    parser.add_argument(
        "--meal",
        default="any",
        help="Meal type(s) to plan: breakfast, lunch, dinner, dessert, snack, any. Use comma for multiple: 'lunch,dinner'"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=5,
        help="Number of recipes (default: 5)"
    )
    parser.add_argument(
        "--new",
        action="store_true",
        help="Generate a new meal plan (otherwise loads saved plan if exists)"
    )
    parser.add_argument(
        "--recipe",
        metavar="NAME",
        help="Show details for a specific recipe (use 'all' to list all recipes in plan)"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode"
    )
    parser.add_argument(
        "--save",
        metavar="FILE",
        help="Save meal plan to JSON file"
    )
    parser.add_argument(
        "--grocery-list",
        action="store_true",
        help="Generate consolidated grocery shopping list"
    )
    parser.add_argument(
        "--meal-prep",
        action="store_true",
        help="Generate meal prep plan (mise en place for the week)"
    )
    parser.add_argument(
        "--no-grocery",
        action="store_true",
        help="Skip grocery list generation (legacy flag, use --grocery-list instead)"
    )
    
    args = parser.parse_args()
    
    # Handle --show flag first (doesn't require catalog or model)
    if args.show is not None:
        state_file = DEFAULT_STATE_FILE
        saved_state = load_state(state_file)
        
        if not saved_state:
            print(f"❌ No saved meal plan found at {state_file}")
            print("Generate a meal plan first with: meal_planner.py -c <catalog> -m <model> --new")
            sys.exit(1)
        
        recipes = saved_state.get("recipes", [])
        meal_type = saved_state.get("meal_type", "any")
        created = saved_state.get("created", "unknown")
        catalogs = saved_state.get("catalogs", [])
        
        if args.show == "all":
            # Show the full meal plan
            print("\n" + "=" * 60)
            print(f"🍽️  SAVED MEAL PLAN - {meal_type.upper()}")
            print("=" * 60)
            print(f"📅 Created: {created[:16] if len(created) > 16 else created}")
            if catalogs:
                print(f"📚 From: {', '.join(catalogs)}")
            print(f"🍴 Recipes: {len(recipes)}")
            print("-" * 60)
            
            for i, recipe in enumerate(recipes, 1):
                name = recipe.get("name", "Unknown")
                chapter = recipe.get("chapter", "")
                print(f"\n  {i}. {name}")
                if chapter:
                    print(f"     📖 {chapter}")
            
            print("\n" + "-" * 60)
            print("Use -s <number> or -s \"recipe name\" to see full details")
            print("=" * 60)
        else:
            # Try to find specific recipe by number or name
            recipe = None
            
            # Try as number first
            try:
                num = int(args.show)
                if 1 <= num <= len(recipes):
                    recipe = recipes[num - 1]
                else:
                    print(f"❌ Recipe #{num} not found. Plan has {len(recipes)} recipes.")
                    sys.exit(1)
            except ValueError:
                # Try as name
                recipe = find_recipe_by_name(recipes, args.show)
                if not recipe:
                    print(f"❌ Recipe '{args.show}' not found in meal plan.")
                    print("\nAvailable recipes:")
                    for i, r in enumerate(recipes, 1):
                        print(f"  {i}. {r.get('name', 'Unknown')}")
                    sys.exit(1)
            
            if recipe:
                print_recipe_details(recipe)
        
        sys.exit(0)
    
    # For other operations, catalog and model are required
    if not args.catalog:
        print("Error: -c/--catalog is required (unless using -s/--show)")
        sys.exit(1)
    if not args.model and (args.new or args.grocery_list or args.meal_prep or args.interactive):
        print("Error: -m/--model is required for generating plans or AI features")
        sys.exit(1)
    
    # Get API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    
    # Validate Claude API key if using Claude
    if args.model and is_claude_model(args.model) and not api_key:
        print("Error: Claude models require an API key.")
        print("Set ANTHROPIC_API_KEY environment variable or use --api-key")
        sys.exit(1)
    
    # Load catalog(s)
    catalog = load_catalog(args.catalog)
    if not catalog:
        sys.exit(1)
    
    # Determine state file location
    state_file = get_state_file_path()
    
    # Parse meal types (comma-separated)
    meal_types = [m.strip().lower() for m in args.meal.split(",")]
    meal_type_str = ", ".join(meal_types)
    
    # Interactive mode
    if args.interactive:
        interactive_mode(catalog, args.model, api_key, state_file)
        sys.exit(0)
    
    # Non-interactive mode
    recipes = catalog.get("recipes", [])
    selected = None
    
    # Check if we should load existing state or generate new
    if not args.new:
        saved_state = load_state(state_file)
        if saved_state:
            selected = saved_state.get("recipes", [])
            saved_meal_type = saved_state.get("meal_type", "any")
            print(f"📂 Loaded saved meal plan ({len(selected)} {saved_meal_type} recipes)")
            print(f"   Use --new to generate a fresh plan")
            meal_type_str = saved_meal_type  # Use saved meal type for display
    
    # Handle --recipe flag (show recipe details)
    if args.recipe:
        if not selected:
            # Try to load state first
            saved_state = load_state(state_file)
            if saved_state:
                selected = saved_state.get("recipes", [])
            else:
                print("No saved meal plan found. Generate one first or use --new")
                sys.exit(1)
        
        if args.recipe.lower() == "all":
            # List all recipes in the plan
            print("\n" + "=" * 60)
            print(f"📋 CURRENT MEAL PLAN ({len(selected)} recipes)")
            print("=" * 60)
            for i, recipe in enumerate(selected, 1):
                name = recipe.get("name", "Unknown")
                chapter = recipe.get("chapter", "")
                print(f"\n  {i}. {name}")
                if chapter:
                    print(f"     📖 {chapter}")
            print("\n" + "=" * 60)
            print("Use --recipe \"recipe name\" to see full details")
        else:
            # Find and show specific recipe
            recipe = find_recipe_by_name(selected, args.recipe)
            if recipe:
                print_recipe_details(recipe)
            else:
                print(f"Recipe '{args.recipe}' not found in current meal plan.")
                print("Available recipes:")
                for r in selected:
                    print(f"  • {r.get('name', 'Unknown')}")
        sys.exit(0)
    
    # Generate new plan if needed
    if selected is None:
        print(f"\n🎲 Selecting {args.count} random {meal_type_str} recipes...")
        selected = select_random_recipes(recipes, args.count, meal_types)
        
        if not selected:
            print("No recipes found")
            sys.exit(1)
        
        # Save state (include catalog paths for reference)
        catalog_list = args.catalog if isinstance(args.catalog, list) else [args.catalog]
        save_state(state_file, selected, meal_type_str, catalog_list)
        print(f"💾 Meal plan saved to {state_file}")
        print(f"   (use --recipe all to list, --new to regenerate)")
    
    # Print meal plan
    print_meal_plan(selected, meal_type_str)
    
    # Determine what to generate
    # If neither --grocery-list nor --meal-prep specified, default to grocery list (backward compatible)
    # Unless --no-grocery is specified
    generate_grocery = args.grocery_list or (not args.meal_prep and not args.no_grocery)
    generate_prep = args.meal_prep
    
    grocery_list = None
    meal_prep_plan = None
    
    # Generate grocery list
    if generate_grocery:
        grocery_list = generate_grocery_list_with_ai(selected, args.model, api_key)
        if grocery_list:
            print("\n" + "=" * 60)
            print("🛒 CONSOLIDATED GROCERY LIST")
            print("=" * 60)
            print(grocery_list)
    
    # Generate meal prep plan
    if generate_prep:
        meal_prep_plan = generate_meal_prep_plan_with_ai(selected, args.model, api_key)
        if meal_prep_plan:
            print("\n" + "=" * 60)
            print("📋 MEAL PREP PLAN")
            print("=" * 60)
            print(meal_prep_plan)
    
    # Save if requested
    if args.save:
        filename = args.save if args.save.endswith(".json") else args.save + ".json"
        
        save_data = {
            "meal_type": meal_type_str,
            "recipes": selected,
        }
        if grocery_list:
            save_data["grocery_list"] = grocery_list
        if meal_prep_plan:
            save_data["meal_prep_plan"] = meal_prep_plan
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to: {filename}")


if __name__ == "__main__":
    main()
