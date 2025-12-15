"""
Meal Plan API router
Handles plan generation, CRUD, and recipe management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import json
import random
from datetime import datetime

from database import get_db
from models.schemas import (
    MealPlanCreate,
    MealPlanList,
    MealPlanDetail,
    MealPlanListResponse,
    RecipeList,
)

router = APIRouter()


@router.get("", response_model=MealPlanListResponse)
async def list_plans(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List all meal plans"""
    query = """
        SELECT mp.id, mp.name, mp.meal_types, mp.recipe_count, mp.created_at,
               COUNT(mpr.id) as actual_count
        FROM meal_plans mp
        LEFT JOIN meal_plan_recipes mpr ON mp.id = mpr.plan_id
    """
    params = {}

    if user_id:
        query += " WHERE mp.user_id = :user_id"
        params["user_id"] = user_id

    query += " GROUP BY mp.id ORDER BY mp.created_at DESC"

    result = db.execute(text(query), params)

    plans = []
    for row in result.mappings():
        meal_types = row["meal_types"]
        if meal_types and isinstance(meal_types, str):
            meal_types = json.loads(meal_types)

        plans.append(MealPlanList(
            id=row["id"],
            name=row["name"] or "Unnamed Plan",
            meal_types=meal_types or [],
            recipe_count=row["actual_count"] or row["recipe_count"] or 0,
            created_at=row["created_at"],
        ))

    return MealPlanListResponse(plans=plans)


@router.post("/generate")
async def generate_plan(request: MealPlanCreate, db: Session = Depends(get_db)):
    """Generate a new meal plan with random recipes"""

    # Build query for eligible recipes
    conditions = ["dish_role != 'sub_recipe'"]
    params = {}

    # Filter by meal types
    if request.meal_types:
        type_values = [t.value if hasattr(t, 'value') else t for t in request.meal_types]
        # Include recipes that match any of the requested types OR are "any"
        type_placeholders = ", ".join([f":type{i}" for i in range(len(type_values))])
        conditions.append(f"(meal_type IN ({type_placeholders}) OR meal_type = 'any')")
        for i, t in enumerate(type_values):
            params[f"type{i}"] = t

    where_clause = "WHERE " + " AND ".join(conditions)

    # Get all matching recipe IDs
    result = db.execute(
        text(f"SELECT id FROM recipes {where_clause}"),
        params
    )
    recipe_ids = [row[0] for row in result]

    if not recipe_ids:
        raise HTTPException(status_code=400, detail="No recipes found matching criteria")

    # Randomly select recipes
    count = min(request.recipe_count, len(recipe_ids))
    selected_ids = random.sample(recipe_ids, count)

    # Create meal plan record
    plan_name = request.name or f"Meal Plan {datetime.now().strftime('%b %d, %Y')}"
    meal_types_json = json.dumps([t.value if hasattr(t, 'value') else t for t in request.meal_types])

    result = db.execute(
        text("""
            INSERT INTO meal_plans (name, meal_types, recipe_count)
            VALUES (:name, :meal_types, :recipe_count)
        """),
        {
            "name": plan_name,
            "meal_types": meal_types_json,
            "recipe_count": count,
        }
    )
    plan_id = result.lastrowid

    # Insert plan-recipe associations
    for position, recipe_id in enumerate(selected_ids):
        db.execute(
            text("""
                INSERT INTO meal_plan_recipes (plan_id, recipe_id, position)
                VALUES (:plan_id, :recipe_id, :position)
            """),
            {"plan_id": plan_id, "recipe_id": recipe_id, "position": position}
        )

    db.commit()

    # Fetch the created plan with recipes
    return await get_plan(plan_id, db)


@router.get("/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a meal plan with its recipes"""

    # Get plan details
    result = db.execute(
        text("""
            SELECT id, name, meal_types, recipe_count, grocery_list, prep_plan, created_at
            FROM meal_plans WHERE id = :id
        """),
        {"id": plan_id}
    )
    plan_row = result.mappings().first()

    if not plan_row:
        raise HTTPException(status_code=404, detail="Meal plan not found")

    # Get associated recipes
    recipes_result = db.execute(
        text("""
            SELECT r.id, r.name, r.chapter, r.meal_type, r.dish_role,
                   r.serves, r.prep_time, r.cook_time, r.dietary_info,
                   mpr.position
            FROM recipes r
            JOIN meal_plan_recipes mpr ON r.id = mpr.recipe_id
            WHERE mpr.plan_id = :plan_id
            ORDER BY mpr.position
        """),
        {"plan_id": plan_id}
    )

    recipes = []
    for row in recipes_result.mappings():
        dietary = row["dietary_info"]
        if dietary and isinstance(dietary, str):
            dietary = json.loads(dietary)

        recipes.append({
            "id": row["id"],
            "name": row["name"],
            "chapter": row["chapter"],
            "meal_type": row["meal_type"] or "any",
            "dish_role": row["dish_role"] or "main",
            "serves": row["serves"],
            "prep_time": row["prep_time"],
            "cook_time": row["cook_time"],
            "dietary_info": dietary or [],
        })

    # Parse JSON fields
    meal_types = plan_row["meal_types"]
    if meal_types and isinstance(meal_types, str):
        meal_types = json.loads(meal_types)

    grocery_list = plan_row["grocery_list"]
    if grocery_list and isinstance(grocery_list, str):
        grocery_list = json.loads(grocery_list)

    prep_plan = plan_row["prep_plan"]
    if prep_plan and isinstance(prep_plan, str):
        prep_plan = json.loads(prep_plan)

    return {
        "id": plan_row["id"],
        "name": plan_row["name"] or "Unnamed Plan",
        "meal_types": meal_types or [],
        "recipe_count": len(recipes),
        "recipes": recipes,
        "grocery_list": grocery_list,
        "prep_plan": prep_plan,
        "created_at": plan_row["created_at"].isoformat() if plan_row["created_at"] else None,
    }


@router.delete("/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """Delete a meal plan"""

    # Check if plan exists
    result = db.execute(
        text("SELECT id FROM meal_plans WHERE id = :id"),
        {"id": plan_id}
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="Meal plan not found")

    # Delete (cascade will handle meal_plan_recipes)
    db.execute(
        text("DELETE FROM meal_plans WHERE id = :id"),
        {"id": plan_id}
    )
    db.commit()

    return {"success": True, "message": "Plan deleted"}


@router.post("/{plan_id}/reroll/{recipe_id}")
async def reroll_recipe(
    plan_id: int,
    recipe_id: int,
    db: Session = Depends(get_db),
):
    """Replace a recipe in the plan with a different random one"""

    # Get the current recipe's meal type
    result = db.execute(
        text("""
            SELECT r.meal_type, mpr.position
            FROM recipes r
            JOIN meal_plan_recipes mpr ON r.id = mpr.recipe_id
            WHERE mpr.plan_id = :plan_id AND mpr.recipe_id = :recipe_id
        """),
        {"plan_id": plan_id, "recipe_id": recipe_id}
    )
    current = result.mappings().first()

    if not current:
        raise HTTPException(status_code=404, detail="Recipe not in this plan")

    meal_type = current["meal_type"]
    position = current["position"]

    # Get all recipe IDs currently in the plan (to exclude)
    result = db.execute(
        text("SELECT recipe_id FROM meal_plan_recipes WHERE plan_id = :plan_id"),
        {"plan_id": plan_id}
    )
    existing_ids = [row[0] for row in result]

    # Find a replacement recipe
    params = {"excluded": tuple(existing_ids) if existing_ids else (0,)}

    if meal_type and meal_type != "any":
        query = """
            SELECT id FROM recipes
            WHERE dish_role != 'sub_recipe'
            AND (meal_type = :meal_type OR meal_type = 'any')
            AND id NOT IN :excluded
        """
        params["meal_type"] = meal_type
    else:
        query = """
            SELECT id FROM recipes
            WHERE dish_role != 'sub_recipe'
            AND id NOT IN :excluded
        """

    result = db.execute(text(query), params)
    available_ids = [row[0] for row in result]

    if not available_ids:
        raise HTTPException(status_code=400, detail="No alternative recipes available")

    # Pick a random replacement
    new_recipe_id = random.choice(available_ids)

    # Update the association
    db.execute(
        text("""
            UPDATE meal_plan_recipes
            SET recipe_id = :new_id
            WHERE plan_id = :plan_id AND recipe_id = :old_id
        """),
        {"new_id": new_recipe_id, "plan_id": plan_id, "old_id": recipe_id}
    )
    db.commit()

    # Fetch and return the new recipe
    result = db.execute(
        text("""
            SELECT id, name, chapter, meal_type, dish_role,
                   serves, prep_time, cook_time, dietary_info
            FROM recipes WHERE id = :id
        """),
        {"id": new_recipe_id}
    )
    row = result.mappings().first()

    dietary = row["dietary_info"]
    if dietary and isinstance(dietary, str):
        dietary = json.loads(dietary)

    return {
        "success": True,
        "new_recipe": {
            "id": row["id"],
            "name": row["name"],
            "chapter": row["chapter"],
            "meal_type": row["meal_type"] or "any",
            "dish_role": row["dish_role"] or "main",
            "serves": row["serves"],
            "prep_time": row["prep_time"],
            "cook_time": row["cook_time"],
            "dietary_info": dietary or [],
        },
        "position": position,
    }


@router.post("/{plan_id}/grocery")
async def generate_grocery_list(plan_id: int, db: Session = Depends(get_db)):
    """
    Generate a consolidated grocery list for the plan.
    For MVP, returns a simple categorized list without AI consolidation.
    """

    # Get all ingredients for recipes in the plan
    result = db.execute(
        text("""
            SELECT i.ingredient_text
            FROM ingredients i
            JOIN meal_plan_recipes mpr ON i.recipe_id = mpr.recipe_id
            WHERE mpr.plan_id = :plan_id
            ORDER BY i.ingredient_text
        """),
        {"plan_id": plan_id}
    )

    ingredients = [row[0] for row in result]

    if not ingredients:
        return {"grocery_list": {}, "message": "No ingredients found"}

    # Simple categorization based on keywords
    categories = {
        "Produce": [],
        "Meat & Seafood": [],
        "Dairy": [],
        "Pantry": [],
        "Spices & Seasonings": [],
        "Other": [],
    }

    produce_keywords = ["onion", "garlic", "tomato", "pepper", "carrot", "celery", "lettuce", "spinach", "kale", "broccoli", "potato", "lemon", "lime", "ginger", "cilantro", "parsley", "basil", "apple", "banana", "avocado", "cucumber", "zucchini", "mushroom", "cabbage", "green", "red", "yellow"]
    meat_keywords = ["chicken", "beef", "pork", "fish", "salmon", "shrimp", "turkey", "bacon", "sausage", "lamb", "tofu", "tempeh", "ground"]
    dairy_keywords = ["milk", "cheese", "butter", "cream", "yogurt", "egg", "sour cream", "mozzarella", "parmesan", "cheddar"]
    spice_keywords = ["salt", "pepper", "cumin", "paprika", "oregano", "thyme", "rosemary", "cinnamon", "chili", "cayenne", "turmeric", "curry", "bay leaf", "nutmeg"]

    for ingredient in ingredients:
        lower = ingredient.lower()
        if any(kw in lower for kw in produce_keywords):
            categories["Produce"].append(ingredient)
        elif any(kw in lower for kw in meat_keywords):
            categories["Meat & Seafood"].append(ingredient)
        elif any(kw in lower for kw in dairy_keywords):
            categories["Dairy"].append(ingredient)
        elif any(kw in lower for kw in spice_keywords):
            categories["Spices & Seasonings"].append(ingredient)
        elif any(kw in lower for kw in ["oil", "vinegar", "sauce", "broth", "stock", "flour", "sugar", "rice", "pasta", "bread", "can", "bean"]):
            categories["Pantry"].append(ingredient)
        else:
            categories["Other"].append(ingredient)

    # Remove empty categories
    grocery_list = {k: v for k, v in categories.items() if v}

    # Cache in database
    db.execute(
        text("UPDATE meal_plans SET grocery_list = :list WHERE id = :id"),
        {"list": json.dumps(grocery_list), "id": plan_id}
    )
    db.commit()

    return {"grocery_list": grocery_list}


@router.post("/{plan_id}/prep")
async def generate_prep_plan(plan_id: int, db: Session = Depends(get_db)):
    """
    Generate a meal prep plan for the plan.
    For MVP, returns a simple task list without AI optimization.
    """

    # Get recipes with their details
    result = db.execute(
        text("""
            SELECT r.name, r.prep_time, r.cook_time, r.instructions
            FROM recipes r
            JOIN meal_plan_recipes mpr ON r.id = mpr.recipe_id
            WHERE mpr.plan_id = :plan_id
        """),
        {"plan_id": plan_id}
    )

    recipes = []
    for row in result.mappings():
        instructions = row["instructions"]
        if instructions and isinstance(instructions, str):
            instructions = json.loads(instructions)
        recipes.append({
            "name": row["name"],
            "prep_time": row["prep_time"],
            "cook_time": row["cook_time"],
            "instructions": instructions or [],
        })

    if not recipes:
        return {"prep_plan": {}, "message": "No recipes in plan"}

    # Simple prep plan structure
    prep_plan = {
        "advance": [],
        "day_of": [],
        "storage": [],
    }

    for recipe in recipes:
        # Add basic prep tasks
        prep_plan["day_of"].append(f"Prepare {recipe['name']}")

        # Check for marinading or long prep
        if recipe["instructions"]:
            for instruction in recipe["instructions"]:
                lower = instruction.lower() if instruction else ""
                if "marinate" in lower or "overnight" in lower or "refrigerate" in lower:
                    prep_plan["advance"].append(f"{recipe['name']}: {instruction[:100]}...")
                    break

    # Add general tips
    prep_plan["storage"] = [
        "Store prepped vegetables in airtight containers for up to 3 days",
        "Cooked grains can be refrigerated for up to 5 days",
        "Label containers with contents and date",
    ]

    # Remove empty sections
    prep_plan = {k: v for k, v in prep_plan.items() if v}

    # Cache in database
    db.execute(
        text("UPDATE meal_plans SET prep_plan = :plan WHERE id = :id"),
        {"plan": json.dumps(prep_plan), "id": plan_id}
    )
    db.commit()

    return {"prep_plan": prep_plan}
