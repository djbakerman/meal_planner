from typing import List, Optional

def normalize_exclusions(items: List[str]) -> List[str]:
    """
    Standardize exclusion strings: lowercase, strip, remove empties.
    """
    if not items:
        return []
    norm = []
    for x in items:
        if x:
            s = str(x).strip().lower()
            if s:
                norm.append(s)
    return sorted(list(set(norm)))

def apply_exclusions(candidates: List, excluded_ingredients: List[str]) -> List:
    """
    Filter out candidates that contain any of the excluded ingredients.
    Checks name, description, and ingredients list.
    """
    if not excluded_ingredients:
        return candidates

    excluded = set(normalize_exclusions(excluded_ingredients))
    if not excluded:
        return candidates

    filtered = []
    for r in candidates:
        # Build search text from recipe attributes
        # ingredients might be a list of ORM objects or dicts depending on context
        ing_text_list = []
        
        # Handle ORM object or Dict
        raw_ings = getattr(r, 'ingredients', [])
        if isinstance(raw_ings, list):
             for ing in raw_ings:
                 if hasattr(ing, 'ingredient_text'):
                     ing_text_list.append(ing.ingredient_text)
                 elif isinstance(ing, dict):
                      ing_text_list.append(ing.get('ingredient_text', ''))
                 else:
                      ing_text_list.append(str(ing))

        haystack = " ".join([
            (getattr(r, 'name', '') or ""),
            (getattr(r, 'description', '') or ""),
            " ".join(ing_text_list)
        ]).lower()

        # Check if ANY exclusion is in the haystack
        # Simple string matching for now (e.g. "nut" matches "peanut")
        # Optimization: Use regex word boundaries if stricter matching is needed later
        is_excluded = False
        for bad_word in excluded:
            if bad_word in haystack:
                is_excluded = True
                break
        
        if not is_excluded:
            filtered.append(r)

    return filtered
