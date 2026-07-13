#!/usr/bin/env python3
"""
End-to-end test for the Weekly Builder.

Runs against a throwaway SQLite database (no MariaDB needed):
  1. Creates the schema
  2. Imports data/catalogs/builder_staples.json and perfect_bodybuilding_cookbook.json
  3. Backfills macros with the deterministic estimator (no AI required)
  4. Generates Week 1 (variety), Week 5 (variety), and Week 1 (simple) plans
     through the real FastAPI endpoint
  5. Prints day-by-day results and asserts calorie/protein sanity

Usage:  python scripts/test_weekly_planner.py
"""

import os
import sys
import tempfile
from pathlib import Path

# --- Point the app at a scratch SQLite DB BEFORE importing api modules ---
_tmpdir = tempfile.mkdtemp(prefix="weekly_planner_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db?check_same_thread=false"

sys.path.append(str(Path(__file__).parent.parent))

from api.database import engine, Base, SessionLocal            # noqa: E402
from api.models import orm                                     # noqa: E402
from api.services import nutrition_service, weekly_planner     # noqa: E402


def import_catalog_json(db, json_path):
    import json
    data = json.load(open(json_path, encoding="utf-8"))
    catalog = orm.Catalog(
        name=Path(json_path).stem.replace("_", " ").title(),
        metadata_info=data.get("metadata", {}),
        recipe_count=len(data.get("recipes", [])),
    )
    db.add(catalog)
    db.flush()
    for r in data.get("recipes", []):
        recipe = orm.Recipe(
            catalog_id=catalog.id,
            name=r["name"],
            chapter=r.get("chapter"),
            meal_type=r.get("meal_type") or "any",
            dish_role=r.get("dish_role", "main"),
            serves=str(r.get("serves", "")),
            cook_time=str(r.get("cook_time", "")),
            calories=str(r.get("calories", "")),
            protein=str(r.get("protein", "")),
            carbs=str(r.get("carbs", "")),
            fat=str(r.get("fat", "")),
            nutrition_full=r.get("nutrition_full"),
            description=r.get("description"),
            instructions=r.get("instructions", []),
            tips=r.get("tips", []),
            sub_recipes=r.get("sub_recipes", []),
            dietary_info=r.get("dietary_info", []),
        )
        db.add(recipe)
        db.flush()
        for idx, ing in enumerate(r.get("ingredients", [])):
            db.add(orm.Ingredient(recipe_id=recipe.id, ingredient_text=ing, sort_order=idx))
    db.commit()
    return catalog


def show_week(week):
    print(f"\n{'=' * 78}")
    print(f"WEEK {week['week_number']} | {week['phase']} phase | {week['mode']} mode | "
          f"targets: {week['targets']['training_calories']} kcal train / "
          f"{week['targets']['rest_calories']} kcal rest / {week['targets']['protein']} g protein")
    print('=' * 78)
    for day in week["days"]:
        t = day["totals"]
        flag = "TRAIN" if day["training_day"] else "rest "
        print(f"\n  {day['day']:<9} [{flag}]  goal {day['target_calories']} kcal  ->  "
              f"{t['calories']} kcal, {t['protein']} g protein, "
              f"{t['carbs']} g carbohydrate, {t['fat']} g fat")
        for s in day["slots"]:
            mult = f" x{s['servings']}" if abs(s['servings'] - 1.0) > 0.01 else ""
            print(f"      {s['slot']:<18} {s['name'][:44]:<46}{mult:<6} "
                  f"{s['calories']:>4} kcal {s['protein']:>5}P")
    avg = week["week_average"]
    print(f"\n  WEEK AVERAGE: {avg['calories']} kcal, {avg['protein']} g protein, "
          f"{avg['carbs']} g carbohydrate, {avg['fat']} g fat")


def check_week(week, label):
    problems = []
    for day in week["days"]:
        t = day["totals"]
        goal = day["target_calories"]
        if len(day["slots"]) < 5:
            problems.append(f"{label} {day['day']}: only {len(day['slots'])} slots filled")
        if abs(t["calories"] - goal) > 0.12 * goal:
            problems.append(f"{label} {day['day']}: {t['calories']} kcal vs goal {goal} (>12% off)")
        if t["protein"] < week["targets"]["protein"] - 25:
            problems.append(f"{label} {day['day']}: protein {t['protein']} g "
                            f"(floor {week['targets']['protein']} g)")
    return problems


def main():
    print(f"Scratch database: {os.environ['DATABASE_URL']}")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    root = Path(__file__).parent.parent
    import_catalog_json(db, root / "data/catalogs/builder_staples.json")
    import_catalog_json(db, root / "data/catalogs/perfect_bodybuilding_cookbook.json")

    recipes = db.query(orm.Recipe).all()
    print(f"Imported {len(recipes)} recipes")

    # Deterministic macro backfill (no AI in test environment)
    stats = nutrition_service.ensure_recipe_macros(db, recipes, allow_llm=False)
    print(f"Macro backfill: {stats}")
    usable = [r for r in recipes if nutrition_service.get_macros(r)]
    print(f"Recipes with usable macros: {len(usable)}/{len(recipes)}")
    for r in usable:
        m = nutrition_service.get_macros(r)
        print(f"   {r.name[:52]:<54} {m['calories']:>5.0f} kcal {m['protein']:>5.1f}P "
              f"{m['carbs']:>5.1f}C {m['fat']:>5.1f}F  [{r.meal_type}]")

    # --- Exercise the real API endpoint ---
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    headers = {}
    if os.getenv("INTERNAL_API_KEY"):
        headers["X-Internal-Secret"] = os.getenv("INTERNAL_API_KEY")

    all_problems = []
    for week_number, mode in [(1, "variety"), (5, "variety"), (1, "simple")]:
        resp = client.post("/api/plans/generate-weekly", headers=headers, json={
            "week_number": week_number,
            "mode": mode,
            "use_llm": False,
        })
        assert resp.status_code == 200, f"API error {resp.status_code}: {resp.text[:500]}"
        plan = resp.json()
        assert plan["plan_type"] == "weekly"
        week = plan["week_structure"]
        show_week(week)
        all_problems += check_week(week, f"[wk{week_number}/{mode}]")

    print(f"\n{'=' * 78}")
    if all_problems:
        print("SANITY WARNINGS:")
        for p in all_problems:
            print("  -", p)
    else:
        print("ALL SANITY CHECKS PASSED: slots filled, calories within 12%, protein near floor.")
    print(f"Plans stored: {db.query(orm.MealPlan).count()} (in scratch DB)")
    db.close()
    return 0 if not all_problems else 1


if __name__ == "__main__":
    sys.exit(main())
