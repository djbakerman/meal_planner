"""
Catalog API router
Handles catalog listing and import operations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import json
from pathlib import Path

from database import get_db
from models.schemas import (
    CatalogList,
    CatalogListResponse,
    CatalogImportRequest,
    CatalogImportResponse,
)

router = APIRouter()


@router.get("", response_model=CatalogListResponse)
async def list_catalogs(db: Session = Depends(get_db)):
    """List all imported catalogs"""
    result = db.execute(
        text("""
            SELECT id, name, source_folder, model_used, recipe_count, created_at
            FROM catalogs
            ORDER BY created_at DESC
        """)
    )

    catalogs = []
    for row in result.mappings():
        catalogs.append(CatalogList(
            id=row["id"],
            name=row["name"],
            source_folder=row["source_folder"],
            model_used=row["model_used"],
            recipe_count=row["recipe_count"] or 0,
            created_at=row["created_at"],
        ))

    return CatalogListResponse(catalogs=catalogs)


@router.get("/{catalog_id}", response_model=CatalogList)
async def get_catalog(catalog_id: int, db: Session = Depends(get_db)):
    """Get a single catalog by ID"""
    result = db.execute(
        text("""
            SELECT id, name, source_folder, model_used, recipe_count, created_at
            FROM catalogs WHERE id = :id
        """),
        {"id": catalog_id}
    )

    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Catalog not found")

    return CatalogList(
        id=row["id"],
        name=row["name"],
        source_folder=row["source_folder"],
        model_used=row["model_used"],
        recipe_count=row["recipe_count"] or 0,
        created_at=row["created_at"],
    )


@router.post("/import", response_model=CatalogImportResponse)
async def import_catalog(request: CatalogImportRequest, db: Session = Depends(get_db)):
    """
    Import a JSON catalog file into the database.

    The file_path should point to a JSON file created by recipe_cataloger.py
    """
    file_path = Path(request.file_path)

    if not file_path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {request.file_path}")

    if not file_path.suffix.lower() == ".json":
        raise HTTPException(status_code=400, detail="File must be a JSON file")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    # Extract data
    metadata = data.get("metadata", {})
    recipes = data.get("recipes", [])
    chapters = data.get("chapters", [])

    catalog_name = request.name or file_path.stem.replace("_", " ").title()

    stats = {
        "success": True,
        "catalog_name": catalog_name,
        "recipes_imported": 0,
        "chapters_imported": 0,
        "ingredients_imported": 0,
        "skipped": 0,
        "errors": [],
    }

    try:
        # Insert catalog
        result = db.execute(
            text("""
                INSERT INTO catalogs (name, source_folder, model_used, recipe_count, metadata)
                VALUES (:name, :source_folder, :model_used, :recipe_count, :metadata)
            """),
            {
                "name": catalog_name,
                "source_folder": metadata.get("source_folder", str(file_path.parent)),
                "model_used": metadata.get("model_used", "unknown"),
                "recipe_count": len(recipes),
                "metadata": json.dumps(metadata),
            }
        )
        catalog_id = result.lastrowid
        stats["catalog_id"] = catalog_id

        # Import chapters
        for chapter in chapters:
            db.execute(
                text("""
                    INSERT INTO chapters (catalog_id, chapter_number, chapter_title, recipe_list)
                    VALUES (:catalog_id, :chapter_number, :chapter_title, :recipe_list)
                """),
                {
                    "catalog_id": catalog_id,
                    "chapter_number": chapter.get("chapter_number"),
                    "chapter_title": chapter.get("chapter_title"),
                    "recipe_list": json.dumps(chapter.get("recipe_list", [])),
                }
            )
            stats["chapters_imported"] += 1

        # Import recipes
        for recipe in recipes:
            try:
                recipe_id = _import_recipe(db, catalog_id, recipe)
                stats["recipes_imported"] += 1

                # Import ingredients
                ingredients = recipe.get("ingredients", [])
                for idx, ingredient in enumerate(ingredients):
                    ingredient_text = ingredient if isinstance(ingredient, str) else str(ingredient)
                    db.execute(
                        text("""
                            INSERT INTO ingredients (recipe_id, ingredient_text, sort_order)
                            VALUES (:recipe_id, :ingredient_text, :sort_order)
                        """),
                        {
                            "recipe_id": recipe_id,
                            "ingredient_text": ingredient_text,
                            "sort_order": idx,
                        }
                    )
                    stats["ingredients_imported"] += 1

            except Exception as e:
                stats["errors"].append(f"Recipe '{recipe.get('name', 'unknown')}': {str(e)}")
                stats["skipped"] += 1

        db.commit()

    except Exception as e:
        db.rollback()
        stats["success"] = False
        stats["errors"].append(str(e))
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

    return CatalogImportResponse(**stats)


def _import_recipe(db: Session, catalog_id: int, recipe: dict) -> int:
    """Import a single recipe and return its ID."""

    # Normalize meal_type
    meal_type = recipe.get("meal_type", "any")
    if meal_type not in ("breakfast", "lunch", "dinner", "dessert", "snack", "any"):
        meal_type = "any"

    # Normalize dish_role
    dish_role = recipe.get("dish_role", "main")
    if dish_role not in ("main", "side", "sub_recipe"):
        dish_role = "main"

    result = db.execute(
        text("""
            INSERT INTO recipes (
                catalog_id, name, chapter, chapter_number, page_number,
                meal_type, dish_role, serves, prep_time, cook_time, total_time,
                calories, protein, carbs, fat, nutrition_full,
                description, instructions, tips, sub_recipes, dietary_info,
                is_complete, source_images
            ) VALUES (
                :catalog_id, :name, :chapter, :chapter_number, :page_number,
                :meal_type, :dish_role, :serves, :prep_time, :cook_time, :total_time,
                :calories, :protein, :carbs, :fat, :nutrition_full,
                :description, :instructions, :tips, :sub_recipes, :dietary_info,
                :is_complete, :source_images
            )
        """),
        {
            "catalog_id": catalog_id,
            "name": recipe.get("name", "Untitled"),
            "chapter": recipe.get("chapter"),
            "chapter_number": recipe.get("chapter_number"),
            "page_number": str(recipe.get("page_number", "")) if recipe.get("page_number") else None,
            "meal_type": meal_type,
            "dish_role": dish_role,
            "serves": recipe.get("serves"),
            "prep_time": recipe.get("prep_time"),
            "cook_time": recipe.get("cook_time"),
            "total_time": recipe.get("total_time"),
            "calories": recipe.get("calories"),
            "protein": recipe.get("protein"),
            "carbs": recipe.get("carbs"),
            "fat": recipe.get("fat"),
            "nutrition_full": recipe.get("nutrition_full"),
            "description": recipe.get("description"),
            "instructions": json.dumps(recipe.get("instructions", [])),
            "tips": json.dumps(recipe.get("tips", [])),
            "sub_recipes": json.dumps(recipe.get("sub_recipes", [])),
            "dietary_info": json.dumps(recipe.get("dietary_info", [])),
            "is_complete": recipe.get("is_complete", True),
            "source_images": json.dumps(recipe.get("source_images", [recipe.get("source_image")])),
        }
    )

    return result.lastrowid
