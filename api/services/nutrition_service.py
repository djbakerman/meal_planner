"""
Nutrition service: parse, estimate, and persist per-serving macros for recipes.

Two estimation paths:
  1. LLM (preferred)   - uses the existing backend.llm plumbing (Ollama or Claude),
                         same pattern as import_catalog.py --enrich. Result is cached
                         into the recipe row so each recipe is only ever estimated once.
  2. Deterministic     - built-in ingredient nutrient table + quantity parser.
                         Free, instant, used as fallback when no model is reachable.

All stored values are plain per-serving numbers as strings (e.g. calories="520",
protein="42") to stay compatible with the existing VARCHAR columns, which may also
contain legacy strings like "500 kcal per serving" (parse_macro handles both).
"""

import re
from datetime import date
from typing import Optional, List

from backend.llm import query_llm, parse_json_response


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_macro(value) -> Optional[float]:
    """Extract a numeric macro value from strings like '520', '520 kcal', '42g per serving'."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)', s.replace(',', ''))
    if not m:
        return None
    v = float(m.group(1))
    if v < 0 or v > 5000:
        return None
    return v


def get_macros(recipe) -> Optional[dict]:
    """Return {'calories','protein','carbs','fat'} per serving, or None if unusable.

    Requires calories and protein; carbs/fat default to 0 when absent.
    Accepts either an ORM Recipe or a dict.
    """
    g = (lambda k: recipe.get(k)) if isinstance(recipe, dict) else (lambda k: getattr(recipe, k, None))
    kcal = parse_macro(g('calories'))
    protein = parse_macro(g('protein'))
    if kcal is None or protein is None or kcal < 20:
        return None
    return {
        'calories': kcal,
        'protein': protein,
        'carbs': parse_macro(g('carbs')) or 0.0,
        'fat': parse_macro(g('fat')) or 0.0,
    }


def parse_servings(serves_str) -> float:
    """'4 Servings' -> 4.0; defaults to 1 serving when unclear."""
    if serves_str is None:
        return 1.0
    if isinstance(serves_str, (int, float)):
        return max(1.0, float(serves_str))
    m = re.search(r'(\d+(?:\.\d+)?)', str(serves_str))
    if not m:
        return 1.0
    v = float(m.group(1))
    return v if 0 < v <= 24 else 1.0


# ---------------------------------------------------------------------------
# Deterministic estimator
# ---------------------------------------------------------------------------

# Fractions commonly found in recipe text
_FRACTIONS = {
    '½': 0.5, '⅓': 1 / 3, '⅔': 2 / 3, '¼': 0.25,
    '¾': 0.75, '⅛': 0.125, '⅜': 0.375, '⅝': 0.625, '⅞': 0.875,
}

# Nutrient table: values are per 100 g -> (kcal, protein g, carbs g, fat g).
# 'cup' overrides grams-per-cup where the 240 g default is badly wrong.
# 'unit' is grams per piece for countable items.
# Order matters only via longest-keyword-first matching (done at match time).
NUTRIENT_TABLE = [
    # Proteins
    ({'chicken breast', 'chicken'}, (165, 31, 0, 3.6), {'unit': 170}),
    ({'ground turkey', 'turkey sausage', 'turkey'}, (170, 27, 0, 7), {'unit': 113}),
    ({'ground beef', 'beef', 'steak', 'bison'}, (215, 26, 0, 12), {'unit': 113}),
    ({'pork loin', 'pork chop', 'pork'}, (195, 27, 0, 9), {'unit': 130}),
    ({'salmon'}, (206, 22, 0, 12), {'unit': 150}),
    ({'tilapia', 'trout', 'halibut', 'white fish', 'cod'}, (128, 26, 0, 2.6), {'unit': 150}),
    ({'tuna'}, (116, 26, 0, 1), {'unit': 140, 'cup': 154}),
    ({'shrimp', 'scallop', 'scallops'}, (99, 21, 0.2, 1), {'cup': 145}),
    ({'crab'}, (97, 19, 0, 1.5), {'cup': 135}),
    ({'egg white'}, (52, 11, 0.7, 0.2), {'unit': 33, 'cup': 243}),
    ({'egg'}, (143, 13, 0.7, 9.5), {'unit': 50}),
    ({'bacon'}, (541, 37, 1.4, 42), {'unit': 12}),
    ({'protein powder', 'whey', 'casein'}, (380, 80, 8, 4), {'scoop': 30, 'cup': 120, 'tbsp': 7.5}),
    ({'greek yogurt', 'yogurt'}, (73, 10, 4, 1.9), {'cup': 245}),
    ({'cottage cheese'}, (98, 11, 3.4, 4.3), {'cup': 226}),
    ({'mozzarella'}, (280, 28, 3, 17), {'cup': 112}),
    ({'parmesan'}, (431, 38, 4, 29), {'tbsp': 5, 'cup': 100}),
    ({'cheddar', 'cheese'}, (403, 25, 1.3, 33), {'cup': 113, 'slice': 21}),
    ({'tofu', 'tempeh'}, (144, 15, 3, 8), {'cup': 126}),
    # Carbohydrates
    ({'whole-wheat flour', 'whole wheat flour', 'wheat flour', 'flour'}, (364, 10, 76, 1), {'cup': 120}),
    ({'rolled oats', 'oats', 'oatmeal'}, (379, 13, 68, 6.5), {'cup': 90}),
    ({'brown rice', 'white rice', 'rice'}, (365, 7, 80, 0.9), {'cup': 185}),
    ({'quinoa'}, (368, 14, 64, 6), {'cup': 170}),
    ({'sweet potato', 'yam'}, (86, 1.6, 20, 0.1), {'unit': 130, 'cup': 133}),
    ({'potato noodles', 'potato'}, (77, 2, 17, 0.1), {'unit': 170, 'cup': 150}),
    ({'pasta', 'noodle', 'lasagna'}, (371, 13, 74, 1.5), {'cup': 105}),
    ({'bread crumbs', 'breadcrumbs'}, (395, 13, 72, 5), {'cup': 108}),
    ({'bread', 'toast', 'bun', 'pita', 'tortilla', 'fry bread'}, (265, 9, 49, 3.2), {'unit': 40, 'slice': 40}),
    ({'granola'}, (471, 10, 64, 20), {'cup': 111}),
    ({'banana'}, (89, 1.1, 23, 0.3), {'unit': 118}),
    ({'apple'}, (52, 0.3, 14, 0.2), {'unit': 182}),
    ({'mango'}, (60, 0.8, 15, 0.4), {'unit': 200, 'cup': 165}),
    ({'pineapple'}, (50, 0.5, 13, 0.1), {'cup': 165}),
    ({'orange'}, (47, 0.9, 12, 0.1), {'unit': 131}),
    ({'blueberries', 'strawberries', 'raspberries', 'berries'}, (50, 0.7, 12, 0.3), {'cup': 148}),
    ({'pumpkin'}, (34, 1.1, 8, 0.1), {'cup': 245}),
    ({'butternut squash', 'squash'}, (45, 1, 12, 0.1), {'cup': 205}),
    ({'zucchini'}, (17, 1.2, 3.1, 0.3), {'unit': 196, 'cup': 124}),
    ({'black beans', 'kidney beans', 'chickpeas', 'beans', 'lentils'}, (132, 8.9, 24, 0.5), {'cup': 172}),
    ({'corn'}, (86, 3.3, 19, 1.4), {'cup': 145}),
    ({'honey', 'maple syrup', 'syrup'}, (304, 0.3, 82, 0), {'tbsp': 21, 'tsp': 7, 'cup': 340}),
    ({'sugar', 'stevia', 'sweetener'}, (387, 0, 100, 0), {'tbsp': 12.5, 'tsp': 4.2, 'cup': 200}),
    ({'pudding mix'}, (350, 0, 88, 0), {'tbsp': 8}),
    # Fats
    ({'olive oil', 'coconut oil', 'canola oil', 'oil'}, (884, 0, 0, 100), {'tbsp': 13.5, 'tsp': 4.5, 'cup': 216}),
    ({'peanut butter', 'almond butter', 'nut butter'}, (588, 25, 20, 50), {'tbsp': 16, 'cup': 258}),
    ({'butter'}, (717, 0.9, 0.1, 81), {'tbsp': 14, 'tsp': 4.7, 'cup': 227}),
    ({'avocado'}, (160, 2, 8.5, 15), {'unit': 200, 'cup': 150}),
    ({'almonds', 'walnuts', 'pecans', 'cashews', 'macadamia', 'nuts'}, (607, 20, 21, 54), {'cup': 143, 'tbsp': 9}),
    ({'chia seeds', 'chia'}, (486, 17, 42, 31), {'tbsp': 12, 'tsp': 4}),
    ({'flax seed', 'flaxseed', 'hemp seed'}, (534, 18, 29, 42), {'tbsp': 10}),
    ({'pumpkin seeds', 'sunflower seeds', 'seeds'}, (559, 30, 11, 49), {'cup': 129, 'tbsp': 8}),
    ({'dark chocolate', 'chocolate chips', 'cocoa'}, (546, 4.9, 61, 31), {'tbsp': 15, 'cup': 170}),
    ({'coconut milk'}, (230, 2.3, 6, 24), {'cup': 240}),
    ({'shredded coconut', 'coconut'}, (660, 6.9, 24, 65), {'cup': 93, 'tbsp': 6}),
    ({'whipped cream', 'heavy cream', 'cream'}, (340, 2.8, 2.8, 36), {'tbsp': 15, 'cup': 238}),
    ({'sour cream'}, (198, 2.4, 4.6, 19), {'tbsp': 12, 'cup': 230}),
    ({'mayonnaise', 'mayo'}, (680, 1, 0.6, 75), {'tbsp': 14}),
    # Dairy / liquids
    ({'almond milk'}, (17, 0.6, 0.7, 1.1), {'cup': 240}),
    ({'whole milk'}, (61, 3.2, 4.8, 3.3), {'cup': 244}),
    ({'skim milk', 'milk'}, (42, 3.4, 5, 1), {'cup': 244}),
    ({'orange juice', 'juice'}, (45, 0.7, 10, 0.2), {'cup': 248}),
    ({'broth', 'stock'}, (5, 1, 0.4, 0.2), {'cup': 240}),
    # Vegetables & aromatics
    ({'broccoli'}, (34, 2.8, 7, 0.4), {'cup': 91}),
    ({'spinach', 'kale', 'greens', 'lettuce', 'arugula'}, (25, 2.9, 3.6, 0.4), {'cup': 30}),
    ({'cauliflower'}, (25, 1.9, 5, 0.3), {'cup': 107}),
    ({'asparagus'}, (20, 2.2, 3.9, 0.1), {'cup': 134}),
    ({'bell pepper', 'red pepper', 'pepper'}, (31, 1, 6, 0.3), {'unit': 119, 'cup': 92}),
    ({'onion'}, (40, 1.1, 9.3, 0.1), {'unit': 110, 'cup': 160}),
    ({'garlic'}, (149, 6.4, 33, 0.5), {'unit': 3, 'tsp': 3, 'clove': 3}),
    ({'tomato sauce', 'salsa', 'marinara'}, (29, 1.3, 6.6, 0.2), {'cup': 245}),
    ({'tomato paste'}, (82, 4.3, 19, 0.5), {'tbsp': 16}),
    ({'tomato'}, (18, 0.9, 3.9, 0.2), {'unit': 123, 'cup': 149}),
    ({'carrot'}, (41, 0.9, 9.6, 0.2), {'unit': 61, 'cup': 128}),
    ({'celery'}, (16, 0.7, 3, 0.2), {'unit': 40, 'cup': 101}),
    ({'cucumber'}, (15, 0.7, 3.6, 0.1), {'unit': 200, 'cup': 104}),
    ({'mushroom'}, (22, 3.1, 3.3, 0.3), {'cup': 70}),
]

# Zero/negligible-calorie items we can safely skip without hurting coverage
_SKIP_WORDS = (
    'water', 'salt', 'black pepper', 'cayenne', 'paprika', 'cumin', 'chili powder',
    'cinnamon', 'nutmeg', 'pumpkin pie spice', 'vanilla', 'baking powder', 'baking soda',
    'oregano', 'basil', 'thyme', 'rosemary', 'parsley', 'cilantro', 'dill', 'bay leaf',
    'lemon juice', 'lime juice', 'lemon', 'lime', 'zest', 'vinegar', 'mustard', 'hot sauce',
    'soy sauce', 'worcestershire', 'seasoning', 'spice', 'extract', 'garnish', 'cooking spray',
    'ginger', 'turmeric', 'red pepper flakes', 'italian herbs', 'garlic powder', 'onion powder',
)

_UNIT_DEFAULT_GRAMS = {
    'cup': 240.0, 'tbsp': 15.0, 'tablespoon': 15.0, 'tsp': 5.0, 'teaspoon': 5.0,
    'oz': 28.35, 'ounce': 28.35, 'lb': 453.6, 'pound': 453.6, 'g': 1.0, 'gram': 1.0,
    'kg': 1000.0, 'scoop': 30.0, 'slice': 30.0, 'clove': 3.0, 'can': 400.0,
    'package': 250.0, 'packet': 100.0, 'stick': 113.0,
}

_UNIT_PATTERN = re.compile(
    r'\b(cups?|tablespoons?|tbsps?|tbsp|teaspoons?|tsps?|tsp|ounces?|oz|pounds?|lbs?|lb|'
    r'grams?|g|kg|scoops?|slices?|cloves?|cans?|packages?|packets?|sticks?)\b'
)


def _parse_quantity(text: str) -> float:
    """Leading quantity of an ingredient line -> float (default 1)."""
    t = text.strip()
    for ch, val in _FRACTIONS.items():
        t = t.replace(ch, f' {val} ')
    # "1 1/2" or "1/2" or "1.5" or "2"
    m = re.match(r'\s*(\d+)\s+(\d+)\s*/\s*(\d+)', t)
    if m:
        return float(m.group(1)) + float(m.group(2)) / float(m.group(3))
    m = re.match(r'\s*(\d+)\s*/\s*(\d+)', t)
    if m:
        return float(m.group(1)) / float(m.group(2))
    m = re.match(r'\s*(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)', t)  # "1 0.5" from unicode replace
    if m:
        return float(m.group(1)) + float(m.group(2))
    m = re.match(r'\s*(\d+(?:\.\d+)?)', t)
    if m:
        return float(m.group(1))
    return 1.0


def _match_food(text: str):
    """Longest-keyword match against the nutrient table."""
    best = None
    best_len = 0
    for keywords, per100, units in NUTRIENT_TABLE:
        for kw in keywords:
            if kw in text and len(kw) > best_len:
                best = (per100, units)
                best_len = len(kw)
    return best


_SIZED_UNIT_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*[-–]?\s*(ounce|oz|pound|lb)\b')


def _ingredient_grams(text: str, qty: float, units: dict) -> Optional[float]:
    # "1, 12-ounce salmon fillet" / "2 8-oz steaks": count x attached size
    m = _SIZED_UNIT_PATTERN.search(text)
    if m and not text.strip().startswith(m.group(1) + ' '):
        size = float(m.group(1))
        unit = {'ounce': 'oz', 'pound': 'lb'}.get(m.group(2), m.group(2))
        grams_per = _UNIT_DEFAULT_GRAMS.get(unit, 28.35)
        count = qty if qty and qty != size else 1.0
        return count * size * grams_per
    m = _UNIT_PATTERN.search(text)
    if m:
        unit = m.group(1).rstrip('s')
        unit = {'tablespoon': 'tbsp', 'teaspoon': 'tsp', 'ounce': 'oz', 'pound': 'lb', 'gram': 'g'}.get(unit, unit)
        grams_per = units.get(unit, _UNIT_DEFAULT_GRAMS.get(unit))
        if grams_per:
            return qty * grams_per
        return None
    # No unit word: treat as countable pieces
    grams_per = units.get('unit')
    if grams_per:
        return qty * grams_per
    return None


def estimate_macros_table(ingredients: List[str], serves) -> Optional[dict]:
    """Deterministic per-serving estimate. Returns None when coverage is too poor to trust."""
    n_serv = parse_servings(serves)
    totals = {'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fat': 0.0}
    considered = 0
    matched = 0
    for raw in ingredients or []:
        text = str(raw).lower().strip()
        if not text:
            continue
        if any(w in text for w in _SKIP_WORDS) and _match_food(text) is None:
            continue  # spice/garnish line
        considered += 1
        hit = _match_food(text)
        if not hit:
            continue
        per100, units = hit
        qty = _parse_quantity(text)
        grams = _ingredient_grams(text, qty, units)
        if grams is None or grams <= 0 or grams > 5000:
            continue
        matched += 1
        f = grams / 100.0
        totals['calories'] += per100[0] * f
        totals['protein'] += per100[1] * f
        totals['carbs'] += per100[2] * f
        totals['fat'] += per100[3] * f
    if considered == 0 or matched / considered < 0.6 or totals['calories'] < 40:
        return None
    return {k: round(v / n_serv, 1) for k, v in totals.items()}


# ---------------------------------------------------------------------------
# LLM estimator (cached into DB by ensure_recipe_macros)
# ---------------------------------------------------------------------------

def estimate_macros_llm(name: str, ingredients: List[str], serves, model: str = None) -> Optional[dict]:
    n_serv = parse_servings(serves)
    prompt = f"""You are a nutrition analyst. Estimate the nutrition of this recipe.

Recipe: {name}
Total servings: {n_serv:g}
Ingredients (for the WHOLE recipe):
{chr(10).join('- ' + str(i) for i in (ingredients or [])[:40])}

Return ONLY a JSON object with numeric values PER SINGLE SERVING:
{{"calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
No units, no text, numbers only."""
    try:
        response = query_llm(prompt, model=model, json_mode=True)
        data = parse_json_response(response) if response else None
    except Exception:
        return None
    if not data:
        return None
    try:
        result = {
            'calories': float(data.get('calories', 0)),
            'protein': float(data.get('protein', 0)),
            'carbs': float(data.get('carbs', 0)),
            'fat': float(data.get('fat', 0)),
        }
    except (TypeError, ValueError):
        return None
    if not (20 <= result['calories'] <= 3000) or result['protein'] < 0:
        return None
    # Consistency check: kcal should roughly match 4P + 4C + 9F
    derived = 4 * result['protein'] + 4 * result['carbs'] + 9 * result['fat']
    if derived > 0 and abs(derived - result['calories']) / max(derived, result['calories']) > 0.45:
        result['calories'] = round(derived)
    return {k: round(v, 1) for k, v in result.items()}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def ensure_recipe_macros(db, recipes, model: str = None, allow_llm: bool = True) -> dict:
    """Fill in missing per-serving macros on ORM recipes; cache results in the DB.

    Returns counters: {'already': n, 'via_llm': n, 'via_table': n, 'skipped': n}
    """
    stats = {'already': 0, 'via_llm': 0, 'via_table': 0, 'skipped': 0}
    dirty = False
    for r in recipes:
        if get_macros(r):
            stats['already'] += 1
            continue
        ingredient_texts = [i.ingredient_text for i in (r.ingredients or [])]
        est, method = None, None
        if allow_llm:
            est = estimate_macros_llm(r.name, ingredient_texts, r.serves, model=model)
            method = 'AI model'
        if est is None:
            est = estimate_macros_table(ingredient_texts, r.serves)
            method = 'ingredient table'
        if est is None:
            stats['skipped'] += 1
            continue
        r.calories = str(round(est['calories']))
        r.protein = str(round(est['protein']))
        r.carbs = str(round(est['carbs']))
        r.fat = str(round(est['fat']))
        note = f"Macros per serving estimated via {method} on {date.today().isoformat()}."
        r.nutrition_full = ((r.nutrition_full or '').strip() + ' ' + note).strip()
        stats['via_llm' if method == 'AI model' else 'via_table'] += 1
        dirty = True
    if dirty:
        db.commit()
    return stats
