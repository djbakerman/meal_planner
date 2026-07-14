"""
Weekly planner engine: builds a 7-day, macro-aware meal plan from recipes
that already have per-serving macros (see nutrition_service.ensure_recipe_macros).

Design goals (per Dan's 90-day muscle program):
  * Graduated calorie ramp - week 1 starts near current intake, climbs ~150 kcal
    per week, settles at the Build-phase target. No day-one force feeding.
  * Grazer profile - six smaller slots instead of three large plates.
  * Protein floor first, calories second, variety third.
  * A COOKING BUDGET: real people don't cook 42 recipes a week. 'variety' mode
    builds a balanced menu of ~14 distinct recipes: 3 rotating breakfasts,
    4 dinner mains each cooked double so tonight's dinner becomes tomorrow's
    lunch, a Monday lunch anchor, and 2+2 rotating snacks/shakes.
  * 'simple' mode is tighter still: one fixed staple menu repeated all week
    for batch cooking.

Pure logic module: no DB access, no HTTP. Fully unit-testable.
"""

import random
from typing import List, Optional

from api.services import nutrition_service

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DEFAULT_TRAINING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# Grazer slot layout: (name, share of daily calories, eligible meal_types)
# ('Mid-Morning' rather than 'Shake': overnight oats and egg bakes land there too)
SLOTS = [
    ('Breakfast',       0.20, ('breakfast', 'any')),
    ('Mid-Morning',     0.16, ('snack', 'breakfast', 'any')),
    ('Lunch',           0.22, ('lunch', 'dinner', 'any')),
    ('Afternoon Snack', 0.12, ('snack', 'any')),
    ('Dinner',          0.22, ('dinner', 'lunch', 'any')),
    ('Evening Snack',   0.08, ('snack', 'dessert', 'any')),
]
_SLOT_TYPES = {name: types for name, share, types in SLOTS}
_SLOT_SHARE = {name: share for name, share, types in SLOTS}

# Slots where side dishes and light items are acceptable
SNACK_SLOTS = {'Mid-Morning', 'Afternoon Snack', 'Evening Snack'}

# Clean, kitchen-real serving multipliers only
SERVING_STEPS = [0.5, 1.0, 1.5, 2.0]

# Minimum protein (grams, at chosen multiplier) for quality-sensitive slots.
# Keeps spritz cookies and rice pilaf out of a muscle program's snack slots.
SLOT_PROTEIN_FLOOR = {
    'Mid-Morning': 20.0,
    'Evening Snack': 10.0,
    'Afternoon Snack': 6.0,
}

# Balanced-menu cooking budget (distinct recipes: 3+2+2+2+4+1 = 14)
BALANCED_BUDGET = {
    'breakfasts': 3,
    'shakes': 2,
    'afternoon': 2,
    'evening': 2,
    'dinners': 4,
    'lunch_anchor': 1,
}

# Calorie ramp: training-day targets by program week (rest days = target - 250)
RAMP = {1: 2300, 2: 2300, 3: 2450, 4: 2600, 5: 2700}
RAMP_MAX = 2800
REST_DAY_DELTA = -250
DEFAULT_PROTEIN_TARGET = 180


def target_calories(week_number: int, training_day: bool, kcal_override: Optional[int] = None) -> int:
    base = kcal_override if kcal_override else RAMP.get(max(1, week_number), RAMP_MAX)
    if not kcal_override and week_number >= 6:
        base = RAMP_MAX
    return base + (0 if training_day else REST_DAY_DELTA)


# ---------------------------------------------------------------------------
# Candidate helpers
# ---------------------------------------------------------------------------

def _eligible(recipe_info: dict, slot_types: tuple, slot_name: str) -> bool:
    mt = (recipe_info['meal_type'] or 'any').lower()
    role = (recipe_info['dish_role'] or 'main').lower()
    if role == 'sub_recipe':
        return False
    if role == 'side' and slot_name not in SNACK_SLOTS:
        return False
    if mt == 'dessert' and slot_name != 'Evening Snack':
        return False
    if mt in ('main', 'side'):  # legacy enum values occasionally stored as meal_type
        mt = 'any'
    return mt in slot_types


def _recipe_info(recipe) -> Optional[dict]:
    macros = nutrition_service.get_macros(recipe)
    if not macros:
        return None
    subs = getattr(recipe, 'sub_recipes', None) or []
    return {
        'id': recipe.id,
        'name': recipe.name,
        'meal_type': getattr(recipe, 'meal_type', 'any'),
        'dish_role': getattr(recipe, 'dish_role', 'main'),
        'macros': macros,
        # Sub-recipe chains (stocks, frostings, components) multiply prep work
        'complexity': len(subs) if isinstance(subs, (list, tuple)) else 0,
    }


def _best_mult(info: dict, slot_kcal: float):
    """Closest clean multiplier to the slot's calorie budget."""
    best_mult, best_gap = None, None
    for mult in SERVING_STEPS:
        gap = abs(info['macros']['calories'] * mult - slot_kcal)
        # Prefer x1.0 on near-ties: subtract a small bonus
        adjusted = gap - (18 if mult == 1.0 else 0)
        if best_gap is None or adjusted < best_gap:
            best_mult, best_gap = mult, adjusted
    return best_mult, abs(info['macros']['calories'] * best_mult - slot_kcal)


def _meets_protein_floor(info: dict, mult: float, slot_name: str) -> bool:
    floor = SLOT_PROTEIN_FLOOR.get(slot_name)
    if floor is None:
        return True
    return info['macros']['protein'] * mult >= floor


def _slot_entry(info: dict, mult: float, slot_name: str, note: str = None) -> dict:
    m = info['macros']
    entry = {
        'slot': slot_name,
        'recipe_id': info['id'],
        'name': info['name'],
        'servings': mult,
        'calories': round(m['calories'] * mult),
        'protein': round(m['protein'] * mult, 1),
        'carbs': round(m['carbs'] * mult, 1),
        'fat': round(m['fat'] * mult, 1),
    }
    if note:
        entry['note'] = note
    return entry


def _day_totals(slots: List[dict]) -> dict:
    return {
        'calories': round(sum(s['calories'] for s in slots)),
        'protein': round(sum(s['protein'] for s in slots), 1),
        'carbs': round(sum(s['carbs'] for s in slots), 1),
        'fat': round(sum(s['fat'] for s in slots), 1),
    }


# ---------------------------------------------------------------------------
# Menu selection (shared scoring for balanced and simple modes)
# ---------------------------------------------------------------------------

def _score_candidate(info: dict, slot_name: str, slot_kcal: float, slot_protein: float,
                     recent_ids: set, rng: random.Random):
    """Lower is better. Returns (score, mult) or None if the recipe can't fit."""
    mult, gap = _best_mult(info, slot_kcal)
    gap_ratio = gap / max(slot_kcal, 1)
    if gap_ratio > 0.35:
        return None
    protein_here = info['macros']['protein'] * mult
    if protein_here < slot_protein:
        protein_score = (slot_protein - protein_here) / max(slot_protein, 1)
    else:
        # Mild penalty for gross overshoot: stops 250 g protein days that
        # crowd out the carbohydrate a training week runs on
        protein_score = 0.20 * (protein_here - slot_protein) / max(slot_protein, 1)
    score = (gap_ratio * 2.0
             + protein_score
             + info['complexity'] * 0.30
             + (0.25 if info['id'] in recent_ids else 0)
             + rng.random() * 0.05)  # seeded tie-break for cross-week rotation
    return score, mult


def _pick_menu(pool: List[dict], slot_name: str, count: int, day_kcal: float,
               protein_target: float, rng: random.Random, recent_ids: set,
               exclude_ids: set) -> List[dict]:
    """Choose `count` distinct recipes suited to a slot's budget and protein share."""
    slot_kcal = day_kcal * _SLOT_SHARE[slot_name]
    slot_protein = protein_target * _SLOT_SHARE[slot_name]
    slot_types = _SLOT_TYPES[slot_name]

    def collect(enforce_floor: bool):
        scored = []
        for info in pool:
            if info['id'] in exclude_ids:
                continue
            if not _eligible(info, slot_types, slot_name):
                continue
            result = _score_candidate(info, slot_name, slot_kcal, slot_protein, recent_ids, rng)
            if result is None:
                continue
            score, mult = result
            if enforce_floor and not _meets_protein_floor(info, mult, slot_name):
                continue
            scored.append((score, info))
        scored.sort(key=lambda s: s[0])
        return [s[1] for s in scored]

    picks = collect(enforce_floor=True)
    if len(picks) < count:  # small pool: relax the quality floor rather than fail
        seen = {p['id'] for p in picks}
        picks += [p for p in collect(enforce_floor=False) if p['id'] not in seen]
    return picks[:count]


# ---------------------------------------------------------------------------
# Balanced menu (mode: 'variety') - the ~14-recipe cooking budget
# ---------------------------------------------------------------------------

def _build_balanced_menu(pool: List[dict], day_kcal: float, protein_target: float,
                         rng: random.Random, recent_ids: set) -> dict:
    used = set()

    def take(slot_name, count):
        picks = _pick_menu(pool, slot_name, count, day_kcal, protein_target, rng, recent_ids, used)
        used.update(p['id'] for p in picks)
        return picks

    menu = {
        'breakfasts': take('Breakfast', BALANCED_BUDGET['breakfasts']),
        'shakes': take('Mid-Morning', BALANCED_BUDGET['shakes']),
        'afternoon': take('Afternoon Snack', BALANCED_BUDGET['afternoon']),
        'evening': take('Evening Snack', BALANCED_BUDGET['evening']),
        'dinners': take('Dinner', BALANCED_BUDGET['dinners']),
        'lunch_anchor': take('Lunch', BALANCED_BUDGET['lunch_anchor']),
    }
    # Absolute fallbacks so a sparse pool still yields a full week
    if not menu['lunch_anchor'] and menu['dinners']:
        menu['lunch_anchor'] = [menu['dinners'][0]]
    return menu


def _rotate(items: List[dict], day_idx: int) -> Optional[dict]:
    if not items:
        return None
    return items[day_idx % len(items)]


def _fit_slot(info: dict, day_kcal: float, active_share_sum: float, slot_name: str,
              note: str = None) -> dict:
    slot_kcal = day_kcal * _SLOT_SHARE[slot_name] / active_share_sum
    mult, _ = _best_mult(info, slot_kcal)
    return _slot_entry(info, mult, slot_name, note)


# ---------------------------------------------------------------------------
# Simple menu (mode: 'simple') - unchanged batch-cook behavior
# ---------------------------------------------------------------------------

def _build_simple_menu(pool: List[dict], day_kcal: float, protein_target: float,
                       rng: random.Random, recent_ids: set) -> dict:
    """One fixed staple menu. Recipes are distinct across slots (no eating the
    same main for lunch AND dinner on the same day), relaxing only when the
    pool is too small to allow it."""
    menu = {}
    used = set()
    for slot_name, share, slot_types in SLOTS:
        take = 2 if slot_name in ('Lunch', 'Dinner') else 1
        picks = _pick_menu(pool, slot_name, take, day_kcal, protein_target,
                           rng, recent_ids, used)
        if len(picks) < take:  # sparse pool: allow reuse rather than leave holes
            seen = {p['id'] for p in picks}
            extra = [p for p in _pick_menu(pool, slot_name, take, day_kcal, protein_target,
                                           rng, recent_ids, set())
                     if p['id'] not in seen]
            picks += extra[: take - len(picks)]
        used.update(p['id'] for p in picks)
        menu[slot_name] = picks
    return menu


# ---------------------------------------------------------------------------
# Week assembly
# ---------------------------------------------------------------------------

def build_week(recipes, week_number: int = 1, mode: str = 'variety',
               training_days: Optional[List[str]] = None,
               protein_target: int = DEFAULT_PROTEIN_TARGET,
               kcal_override: Optional[int] = None,
               recent_recipe_ids: Optional[List[int]] = None) -> dict:
    """Build the week structure from ORM recipes (macros must already be present)."""
    training_days = training_days or DEFAULT_TRAINING_DAYS
    recent_ids = set(recent_recipe_ids or [])
    rng = random.Random(week_number * 7919)  # deterministic per week, varies across weeks

    pool = [i for i in (_recipe_info(r) for r in recipes) if i]
    if len(pool) < 6:
        raise ValueError(
            f"Only {len(pool)} recipes have usable macros - import the Builder Staples "
            "catalog and/or run macro enrichment first."
        )

    train_kcal = target_calories(week_number, True, kcal_override)

    if mode == 'simple':
        menu = _build_simple_menu(pool, train_kcal, protein_target, rng, recent_ids)
    else:
        menu = _build_balanced_menu(pool, train_kcal, protein_target, rng, recent_ids)

    days = []
    for day_idx, day_name in enumerate(DAY_NAMES):
        is_training = day_name in training_days
        day_kcal = target_calories(week_number, is_training, kcal_override)

        # Rest days drop the evening snack; remaining slots absorb its share
        active_slots = [s for s, _, _ in SLOTS if not (s == 'Evening Snack' and not is_training)]
        share_sum = sum(_SLOT_SHARE[s] for s in active_slots)

        day_slots = []
        for slot_name in active_slots:
            info, note = None, None

            if mode == 'simple':
                options = menu.get(slot_name) or []
                # Offset the dinner rotation so lunch and dinner never land on
                # the same alternation phase (belt to the menu dedupe's braces)
                rotate_idx = day_idx + 1 if slot_name == 'Dinner' else day_idx
                info = _rotate(options, rotate_idx) if options else None
            else:
                if slot_name == 'Breakfast':
                    info = _rotate(menu['breakfasts'], day_idx)
                elif slot_name == 'Mid-Morning':
                    info = _rotate(menu['shakes'], day_idx)
                elif slot_name == 'Afternoon Snack':
                    info = _rotate(menu['afternoon'], day_idx)
                elif slot_name == 'Evening Snack':
                    info = _rotate(menu['evening'], day_idx)
                elif slot_name == 'Dinner':
                    info = _rotate(menu['dinners'], day_idx)
                    if info:
                        note = ("Cook double - portion 2 is tomorrow's lunch"
                                if day_idx < 6 else
                                "Single portion (or bank half for next Monday's lunch)")
                elif slot_name == 'Lunch':
                    if day_idx == 0:
                        info = menu['lunch_anchor'][0] if menu['lunch_anchor'] else None
                        note = 'Prepped Sunday or quick-cook'
                    else:
                        info = _rotate(menu['dinners'], day_idx - 1)
                        note = "Leftover from yesterday's dinner"

            if info is None:
                continue
            day_slots.append(_fit_slot(info, day_kcal, share_sum, slot_name, note))

        # Protein rescue: if a day lands short, step the shake up half a serving
        totals = _day_totals(day_slots)
        if totals['protein'] < protein_target - 10:
            for entry in day_slots:
                if entry['slot'] != 'Mid-Morning':
                    continue
                info = next((p for p in pool if p['id'] == entry['recipe_id']), None)
                if not info:
                    break
                new_mult = min(2.0, entry['servings'] + 0.5)
                new_kcal_total = totals['calories'] - entry['calories'] + info['macros']['calories'] * new_mult
                if new_mult > entry['servings'] and new_kcal_total <= day_kcal * 1.08:
                    idx = day_slots.index(entry)
                    day_slots[idx] = _slot_entry(info, new_mult, entry['slot'])
                break

        totals = _day_totals(day_slots)
        days.append({
            'day': day_name,
            'training_day': is_training,
            'target_calories': day_kcal,
            'slots': day_slots,
            'totals': totals,
            'protein_target': protein_target,
        })

    # Cook plan: which dinners get cooked when, and what each cook covers
    cook_plan = []
    if mode != 'simple':
        for day_idx, day in enumerate(days):
            dinner = next((s for s in day['slots'] if s['slot'] == 'Dinner'), None)
            if not dinner:
                continue
            covers = [f"{day['day']} dinner ({dinner['servings']:g} serving)"]
            portions = dinner['servings']
            if day_idx < 6:
                next_lunch = next((s for s in days[day_idx + 1]['slots']
                                   if s['slot'] == 'Lunch' and s['recipe_id'] == dinner['recipe_id']), None)
                if next_lunch:
                    covers.append(f"{days[day_idx + 1]['day']} lunch ({next_lunch['servings']:g} serving)")
                    portions += next_lunch['servings']
            cook_plan.append({
                'recipe_id': dinner['recipe_id'],
                'name': dinner['name'],
                'cook_on': day['day'],
                'portions': round(portions, 2),
                'covers': covers,
            })

    distinct_ids = []
    for day in days:
        for s in day['slots']:
            if s['recipe_id'] not in distinct_ids:
                distinct_ids.append(s['recipe_id'])

    n = len(days)
    avg = {
        'calories': round(sum(d['totals']['calories'] for d in days) / n),
        'protein': round(sum(d['totals']['protein'] for d in days) / n, 1),
        'carbs': round(sum(d['totals']['carbs'] for d in days) / n, 1),
        'fat': round(sum(d['totals']['fat'] for d in days) / n, 1),
    }

    phase = ('Foundation' if week_number <= 4 else
             'Build' if week_number <= 8 else
             'Define' if week_number <= 12 else 'Test Week')

    return {
        'version': 2,
        'week_number': week_number,
        'phase': phase,
        'mode': mode,
        'training_days': training_days,
        'targets': {
            'training_calories': target_calories(week_number, True, kcal_override),
            'rest_calories': target_calories(week_number, False, kcal_override),
            'protein': protein_target,
        },
        'days': days,
        'cook_plan': cook_plan,
        'distinct_recipes': len(distinct_ids),
        'week_average': avg,
        'notes': [
            ('Cooking budget: about {} distinct recipes this week. Dinners are cooked '
             'double and roll into the next day\'s lunch.'.format(len(distinct_ids)))
            if mode != 'simple' else
            ('Cooking budget: {} distinct recipes on one fixed menu - batch-cook on '
             'Sunday; lunches and dinners alternate between two mains each.'.format(len(distinct_ids))),
            'Servings are multipliers of one recipe serving (1.5 = one and a half servings).',
            'Add 5 g creatine monohydrate to any shake, daily - training and rest days alike.',
            'Weigh in each morning; judge the week by its average, not by any single day.',
            'If the ramp feels too fast, hold this week\'s calories one extra week - '
            'consistency beats speed.',
        ],
    }
