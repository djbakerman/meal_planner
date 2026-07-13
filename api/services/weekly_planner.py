"""
Weekly planner engine: builds a 7-day, macro-aware meal plan from recipes
that already have per-serving macros (see nutrition_service.ensure_recipe_macros).

Design goals (per Dan's 90-day muscle program):
  * Graduated calorie ramp - week 1 starts near current intake, climbs ~150 kcal
    per week, settles at the Build-phase target. No day-one force feeding.
  * Grazer profile - six smaller slots instead of three large plates.
  * Protein floor first, calories second, variety third.
  * Two modes: 'variety' (rotate recipes, max 2 uses/week) and
    'simple' (small staple pool repeated all week for batch cooking).

Pure logic module: no DB access, no HTTP. Fully unit-testable.
"""

import random
from typing import List, Optional

from api.services import nutrition_service

DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DEFAULT_TRAINING_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

# Grazer slot layout: (name, share of daily calories, eligible meal_types)
SLOTS = [
    ('Breakfast',         0.20, ('breakfast', 'any')),
    ('Mid-Morning Shake', 0.16, ('snack', 'breakfast', 'any')),
    ('Lunch',             0.22, ('lunch', 'dinner', 'any')),
    ('Afternoon Snack',   0.12, ('snack', 'any')),
    ('Dinner',            0.22, ('dinner', 'lunch', 'any')),
    ('Evening Snack',     0.08, ('snack', 'dessert', 'any')),
]

SERVING_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]

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


def _eligible(recipe_info: dict, slot_types: tuple, slot_name: str) -> bool:
    mt = (recipe_info['meal_type'] or 'any').lower()
    role = (recipe_info['dish_role'] or 'main').lower()
    if role == 'sub_recipe':
        return False
    if role == 'side' and 'Snack' not in slot_name and 'Shake' not in slot_name:
        return False
    if mt == 'dessert' and slot_name != 'Evening Snack':
        return False
    # legacy enum values 'main'/'side' occasionally stored as meal_type
    if mt in ('main', 'side'):
        mt = 'any'
    return mt in slot_types


def _recipe_info(recipe) -> Optional[dict]:
    macros = nutrition_service.get_macros(recipe)
    if not macros:
        return None
    return {
        'id': recipe.id,
        'name': recipe.name,
        'meal_type': getattr(recipe, 'meal_type', 'any'),
        'dish_role': getattr(recipe, 'dish_role', 'main'),
        'macros': macros,
    }


def _score(info: dict, mult: float, slot_kcal: float, protein_deficit: float,
           uses_this_week: int, used_yesterday_in_slot: bool, recent_penalty: float) -> float:
    m = info['macros']
    kcal = m['calories'] * mult
    protein = m['protein'] * mult
    score = abs(kcal - slot_kcal)                       # closeness to slot budget
    score -= min(protein, protein_deficit) * 2.0        # protein still needed today is valuable
    score += abs(mult - 1.0) * 40                       # prefer natural serving sizes
    score += uses_this_week * 120                       # variety pressure within the week
    score += 90 if used_yesterday_in_slot else 0        # avoid same slot two days running
    score += recent_penalty                             # rotation across weeks
    return score


def _pick(pool: List[dict], slot_name: str, slot_kcal: float, protein_deficit: float,
          week_uses: dict, yesterday_slot: dict, recent_ids: set, rng: random.Random,
          max_uses: int) -> Optional[dict]:
    slot_types = next(s[2] for s in SLOTS if s[0] == slot_name)
    best, best_score = None, None
    order = list(pool)
    rng.shuffle(order)  # stable tie-breaking per seed
    for info in order:
        if not _eligible(info, slot_types, slot_name):
            continue
        uses = week_uses.get(info['id'], 0)
        if uses >= max_uses:
            continue
        for mult in SERVING_STEPS:
            kcal = info['macros']['calories'] * mult
            if kcal < slot_kcal * 0.45 or kcal > slot_kcal * 1.8:
                continue
            s = _score(info, mult, slot_kcal, protein_deficit, uses,
                       yesterday_slot.get(slot_name) == info['id'],
                       60 if info['id'] in recent_ids else 0)
            if best_score is None or s < best_score:
                best, best_score = (info, mult), s
    return best


def _slot_entry(info: dict, mult: float, slot_name: str) -> dict:
    m = info['macros']
    return {
        'slot': slot_name,
        'recipe_id': info['id'],
        'name': info['name'],
        'servings': mult,
        'calories': round(m['calories'] * mult),
        'protein': round(m['protein'] * mult, 1),
        'carbs': round(m['carbs'] * mult, 1),
        'fat': round(m['fat'] * mult, 1),
    }


def _day_totals(slots: List[dict]) -> dict:
    return {
        'calories': round(sum(s['calories'] for s in slots)),
        'protein': round(sum(s['protein'] for s in slots), 1),
        'carbs': round(sum(s['carbs'] for s in slots), 1),
        'fat': round(sum(s['fat'] for s in slots), 1),
    }


def _protein_rescue(day_slots: List[dict], pool: List[dict], protein_target: float,
                    day_kcal_target: float, week_uses: dict, max_uses: int) -> List[dict]:
    """If the day is short on protein, upgrade snack slots to higher-protein picks."""
    totals = _day_totals(day_slots)
    if totals['protein'] >= protein_target - 10:
        return day_slots
    for idx, entry in enumerate(day_slots):
        if 'Snack' not in entry['slot'] and 'Shake' not in entry['slot']:
            continue
        slot_types = next(s[2] for s in SLOTS if s[0] == entry['slot'])
        current_protein = entry['protein']
        best = None
        for info in pool:
            if not _eligible(info, slot_types, entry['slot']):
                continue
            # Protein floor outranks variety: allow one use beyond the weekly cap here
            if week_uses.get(info['id'], 0) >= max_uses + 1 and info['id'] != entry['recipe_id']:
                continue
            for mult in SERVING_STEPS:
                kcal = info['macros']['calories'] * mult
                if abs(kcal - entry['calories']) > max(120, 0.06 * day_kcal_target):
                    continue
                protein = info['macros']['protein'] * mult
                if protein > current_protein + 5 and (best is None or protein > best[2]):
                    best = (info, mult, protein)
        if best:
            info, mult, _ = best
            week_uses[entry['recipe_id']] = max(0, week_uses.get(entry['recipe_id'], 1) - 1)
            week_uses[info['id']] = week_uses.get(info['id'], 0) + 1
            day_slots[idx] = _slot_entry(info, mult, entry['slot'])
            totals = _day_totals(day_slots)
            if totals['protein'] >= protein_target - 10:
                break
    return day_slots


def _build_simple_menu(pool: List[dict], day_kcal: float, protein_target: float,
                       rng: random.Random) -> dict:
    """Pick one staple per slot (two alternates for lunch/dinner) - batch-cook mode.

    Candidates must actually FIT the slot's calorie budget at their best serving
    multiplier (within 15%, widening to 35% only if nothing qualifies); among the
    fits, prefer protein density. This keeps 'simple' from starving the day.
    """
    menu = {}
    for slot_name, share, slot_types in SLOTS:
        slot_kcal = day_kcal * share
        slot_protein = protein_target * share  # balanced protein share for this slot
        scored = []
        for info in pool:
            if not _eligible(info, slot_types, slot_name):
                continue
            best_mult, best_gap = None, None
            for mult in SERVING_STEPS:
                gap = abs(info['macros']['calories'] * mult - slot_kcal)
                if best_gap is None or gap < best_gap:
                    best_mult, best_gap = mult, gap
            gap_ratio = best_gap / max(slot_kcal, 1)
            protein_here = info['macros']['protein'] * best_mult
            # Penalize protein shortfall against the slot's share more than overage
            if protein_here < slot_protein:
                protein_score = (slot_protein - protein_here) / max(slot_protein, 1)
            else:
                protein_score = 0.25 * (protein_here - slot_protein) / max(slot_protein, 1)
            scored.append((gap_ratio * 2 + protein_score, gap_ratio, rng.random(), info, best_mult))
        fits = [s for s in scored if s[1] <= 0.15]
        if not fits:
            fits = [s for s in scored if s[1] <= 0.35]
        if not fits:
            fits = scored
        fits.sort(key=lambda c: (c[0], c[2]))
        take = 2 if slot_name in ('Lunch', 'Dinner') else 1
        menu[slot_name] = [(c[3], c[4]) for c in fits[:take]]
    return menu


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

    max_uses = 2 if mode == 'variety' else 99
    week_uses = {}
    yesterday_slot = {}
    days = []

    simple_menu = None
    if mode == 'simple':
        train_kcal = target_calories(week_number, True, kcal_override)
        simple_menu = _build_simple_menu(pool, train_kcal, protein_target, rng)

    for day_idx, day_name in enumerate(DAY_NAMES):
        is_training = day_name in training_days
        day_kcal = target_calories(week_number, is_training, kcal_override)
        day_slots = []
        protein_so_far = 0.0

        for slot_name, share, slot_types in SLOTS:
            # Simple mode uses one fixed menu; rest days trim the evening snack
            # instead of rescaling every dish (keeps batch cooking simple).
            if simple_menu is not None and not is_training and slot_name == 'Evening Snack':
                continue
            slot_kcal = day_kcal * share
            protein_deficit = max(0.0, protein_target - protein_so_far)
            picked = None

            if simple_menu is not None:
                options = simple_menu.get(slot_name) or []
                if options:
                    info, mult = options[day_idx % len(options)]
                    picked = (info, mult)
            if picked is None:
                picked = _pick(pool, slot_name, slot_kcal, protein_deficit,
                               week_uses, yesterday_slot, recent_ids, rng, max_uses)
            if picked is None:  # relax variety cap rather than leave a hole
                picked = _pick(pool, slot_name, slot_kcal, protein_deficit,
                               week_uses, yesterday_slot, recent_ids, rng, max_uses=99)
            if picked is None:
                continue

            info, mult = picked
            week_uses[info['id']] = week_uses.get(info['id'], 0) + 1
            entry = _slot_entry(info, mult, slot_name)
            protein_so_far += entry['protein']
            day_slots.append(entry)

        if mode == 'variety':
            day_slots = _protein_rescue(day_slots, pool, protein_target, day_kcal, week_uses, max_uses)

        yesterday_slot = {e['slot']: e['recipe_id'] for e in day_slots}
        totals = _day_totals(day_slots)
        days.append({
            'day': day_name,
            'training_day': is_training,
            'target_calories': day_kcal,
            'slots': day_slots,
            'totals': totals,
            'protein_target': protein_target,
        })

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
        'version': 1,
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
        'week_average': avg,
        'notes': [
            'Servings are multipliers of one recipe serving (1.5 = one and a half servings).',
            'Add 5 g creatine monohydrate to any shake, daily - training and rest days alike.',
            'Weigh in each morning; judge the week by its average, not by any single day.',
            'If the ramp feels too fast, hold this week\'s calories one extra week - '
            'consistency beats speed.',
        ],
    }
