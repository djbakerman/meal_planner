"""
Recipe API router
Handles recipe listing, search, and detail operations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
import json
import random

from database import get_db
from models.schemas import (
    RecipeList,
    RecipeDetail,
    RecipeListResponse,
    RecipeSearchRequest,
    PaginationMeta,
    MealType,
    DishRole,
)

router = APIRouter()


@router.get("", response_model=RecipeListResponse)
async def list_recipes(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    meal_type: Optional[str] = None,
    dish_role: Optional[str] = None,
    catalog_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List recipes with pagination and filtering"""

    # Build WHERE clause
    conditions = []
    params = {}

    if meal_type:
        conditions.append("meal_type = :meal_type")
        params["meal_type"] = meal_type

    if dish_role:
        conditions.append("dish_role = :dish_role")
        params["dish_role"] = dish_role

    if catalog_id:
        conditions.append("catalog_id = :catalog_id")
        params["catalog_id"] = catalog_id

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    count_result = db.execute(
        text(f"SELECT COUNT(*) as total FROM recipes {where_clause}"),
        params
    )
    total = count_result.scalar()

    # Calculate pagination
    offset = (page - 1) * limit
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    # Get recipes
    params["limit"] = limit
    params["offset"] = offset

    result = db.execute(
        text(f"""
            SELECT id, name, chapter, meal_type, dish_role,
                   prep_time, calories, dietary_info
            FROM recipes
            {where_clause}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    recipes = []
    for row in result.mappings():
        dietary = row["dietary_info"]
        if dietary:
            dietary = json.loads(dietary) if isinstance(dietary, str) else dietary
        else:
            dietary = []

        recipes.append(RecipeList(
            id=row["id"],
            name=row["name"],
            chapter=row["chapter"],
            meal_type=row["meal_type"] or "any",
            dish_role=row["dish_role"] or "main",
            prep_time=row["prep_time"],
            calories=row["calories"],
            dietary_info=dietary,
        ))

    return RecipeListResponse(
        recipes=recipes,
        pagination=PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
        )
    )


@router.get("/random")
async def get_random_recipes(
    count: int = Query(5, ge=1, le=20),
    meal_type: Optional[str] = None,
    exclude_roles: str = "sub_recipe",
    db: Session = Depends(get_db),
):
    """Get random recipes for meal planning"""

    # Build WHERE clause
    conditions = ["dish_role != 'sub_recipe'"]
    params = {}

    if meal_type and meal_type != "any":
        # Include recipes that match the type OR are "any"
        conditions.append("(meal_type = :meal_type OR meal_type = 'any')")
        params["meal_type"] = meal_type

    where_clause = "WHERE " + " AND ".join(conditions)

    # Get all matching recipe IDs
    result = db.execute(
        text(f"SELECT id FROM recipes {where_clause}"),
        params
    )

    recipe_ids = [row[0] for row in result]

    if not recipe_ids:
        return {"recipes": []}

    # Randomly select
    selected_ids = random.sample(recipe_ids, min(count, len(recipe_ids)))

    # Fetch full details for selected recipes
    placeholders = ",".join([f":id{i}" for i in range(len(selected_ids))])
    id_params = {f"id{i}": rid for i, rid in enumerate(selected_ids)}

    result = db.execute(
        text(f"""
            SELECT id, name, chapter, meal_type, dish_role,
                   serves, prep_time, cook_time, dietary_info
            FROM recipes
            WHERE id IN ({placeholders})
        """),
        id_params
    )

    recipes = []
    for row in result.mappings():
        dietary = row["dietary_info"]
        if dietary:
            dietary = json.loads(dietary) if isinstance(dietary, str) else dietary
        else:
            dietary = []

        recipes.append({
            "id": row["id"],
            "name": row["name"],
            "chapter": row["chapter"],
            "meal_type": row["meal_type"] or "any",
            "dish_role": row["dish_role"] or "main",
            "serves": row["serves"],
            "prep_time": row["prep_time"],
            "cook_time": row["cook_time"],
            "dietary_info": dietary,
        })

    return {"recipes": recipes}


@router.get("/{recipe_id}", response_model=RecipeDetail)
async def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get full recipe details"""

    result = db.execute(
        text("""
            SELECT * FROM recipes WHERE id = :id
        """),
        {"id": recipe_id}
    )

    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Recipe not found")

    # Parse JSON fields
    def parse_json(val):
        if val is None:
            return []
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return []
        return val

    # Get ingredients
    ing_result = db.execute(
        text("""
            SELECT ingredient_text FROM ingredients
            WHERE recipe_id = :id ORDER BY sort_order
        """),
        {"id": recipe_id}
    )
    ingredients = [r[0] for r in ing_result]

    return RecipeDetail(
        id=row["id"],
        catalog_id=row["catalog_id"],
        name=row["name"],
        chapter=row["chapter"],
        chapter_number=row["chapter_number"],
        page_number=row["page_number"],
        meal_type=row["meal_type"] or "any",
        dish_role=row["dish_role"] or "main",
        serves=row["serves"],
        prep_time=row["prep_time"],
        cook_time=row["cook_time"],
        total_time=row["total_time"],
        calories=row["calories"],
        protein=row["protein"],
        carbs=row["carbs"],
        fat=row["fat"],
        nutrition_full=row["nutrition_full"],
        description=row["description"],
        ingredients=ingredients,
        instructions=parse_json(row["instructions"]),
        tips=parse_json(row["tips"]),
        sub_recipes=parse_json(row["sub_recipes"]),
        dietary_info=parse_json(row["dietary_info"]),
        is_complete=row["is_complete"],
        created_at=row["created_at"],
    )


@router.post("/search", response_model=RecipeListResponse)
async def search_recipes(request: RecipeSearchRequest, db: Session = Depends(get_db)):
    """Search recipes by name, description, or ingredients"""

    conditions = []
    params = {}

    if request.query:
        conditions.append("(name LIKE :query OR description LIKE :query OR chapter LIKE :query)")
        params["query"] = f"%{request.query}%"

    if request.meal_type:
        conditions.append("meal_type = :meal_type")
        params["meal_type"] = request.meal_type.value

    if request.dish_role:
        conditions.append("dish_role = :dish_role")
        params["dish_role"] = request.dish_role.value

    if request.catalog_id:
        conditions.append("catalog_id = :catalog_id")
        params["catalog_id"] = request.catalog_id

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Get total count
    count_result = db.execute(
        text(f"SELECT COUNT(*) FROM recipes {where_clause}"),
        params
    )
    total = count_result.scalar()

    # Calculate pagination
    page = (request.offset // request.limit) + 1 if request.limit > 0 else 1
    total_pages = (total + request.limit - 1) // request.limit if total > 0 else 1

    # Get recipes
    params["limit"] = request.limit
    params["offset"] = request.offset

    result = db.execute(
        text(f"""
            SELECT id, name, chapter, meal_type, dish_role,
                   prep_time, calories, dietary_info
            FROM recipes
            {where_clause}
            ORDER BY name
            LIMIT :limit OFFSET :offset
        """),
        params
    )

    recipes = []
    for row in result.mappings():
        dietary = row["dietary_info"]
        if dietary:
            dietary = json.loads(dietary) if isinstance(dietary, str) else dietary
        else:
            dietary = []

        recipes.append(RecipeList(
            id=row["id"],
            name=row["name"],
            chapter=row["chapter"],
            meal_type=row["meal_type"] or "any",
            dish_role=row["dish_role"] or "main",
            prep_time=row["prep_time"],
            calories=row["calories"],
            dietary_info=dietary,
        ))

    return RecipeListResponse(
        recipes=recipes,
        pagination=PaginationMeta(
            page=page,
            limit=request.limit,
            total=total,
            total_pages=total_pages,
        )
    )
