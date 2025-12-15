#!/usr/bin/env python3
"""
Import JSON catalog files into MariaDB database.

Usage:
    python import_catalog.py /path/to/catalog.json
    python import_catalog.py /path/to/catalog.json --name "My Cookbook"
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pymysql
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "api" / ".env")


def get_db_connection():
    """Create database connection from environment variables."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USERNAME", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_DATABASE", "meal_planner"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def import_catalog(file_path: str, catalog_name: str = None) -> dict:
    """
    Import a JSON catalog file into the database.

    Returns dict with import statistics.
    """
    # Load JSON file
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Catalog file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract catalog metadata
    metadata = data.get("metadata", {})
    recipes = data.get("recipes", [])
    chapters = data.get("chapters", [])

    if not catalog_name:
        catalog_name = path.stem.replace("_", " ").title()

    conn = get_db_connection()
    stats = {
        "catalog_name": catalog_name,
        "recipes_imported": 0,
        "chapters_imported": 0,
        "ingredients_imported": 0,
        "skipped": 0,
        "errors": [],
    }

    try:
        with conn.cursor() as cursor:
            # Insert catalog record
            cursor.execute(
                """
                INSERT INTO catalogs (name, source_folder, model_used, recipe_count, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    catalog_name,
                    metadata.get("source_folder", str(path.parent)),
                    metadata.get("model_used", "unknown"),
                    len(recipes),
                    json.dumps(metadata),
                )
            )
            catalog_id = cursor.lastrowid
            stats["catalog_id"] = catalog_id

            # Import chapters
            for chapter in chapters:
                cursor.execute(
                    """
                    INSERT INTO chapters (catalog_id, chapter_number, chapter_title, recipe_list)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        catalog_id,
                        chapter.get("chapter_number"),
                        chapter.get("chapter_title"),
                        json.dumps(chapter.get("recipe_list", [])),
                    )
                )
                stats["chapters_imported"] += 1

            # Import recipes
            for recipe in recipes:
                try:
                    recipe_id = import_recipe(cursor, catalog_id, recipe)
                    stats["recipes_imported"] += 1

                    # Import ingredients
                    ingredients = recipe.get("ingredients", [])
                    for idx, ingredient in enumerate(ingredients):
                        ingredient_text = ingredient if isinstance(ingredient, str) else ingredient.get("ingredient_text", str(ingredient))
                        cursor.execute(
                            """
                            INSERT INTO ingredients (recipe_id, ingredient_text, sort_order)
                            VALUES (%s, %s, %s)
                            """,
                            (recipe_id, ingredient_text, idx)
                        )
                        stats["ingredients_imported"] += 1

                except Exception as e:
                    stats["errors"].append(f"Recipe '{recipe.get('name', 'unknown')}': {str(e)}")
                    stats["skipped"] += 1

            conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

    return stats


def import_recipe(cursor, catalog_id: int, recipe: dict) -> int:
    """Import a single recipe and return its ID."""

    # Normalize meal_type
    meal_type = recipe.get("meal_type", "any")
    if meal_type not in ("breakfast", "lunch", "dinner", "dessert", "snack", "any"):
        meal_type = "any"

    # Normalize dish_role
    dish_role = recipe.get("dish_role", "main")
    if dish_role not in ("main", "side", "sub_recipe"):
        dish_role = "main"

    cursor.execute(
        """
        INSERT INTO recipes (
            catalog_id, name, chapter, chapter_number, page_number,
            meal_type, dish_role, serves, prep_time, cook_time, total_time,
            calories, protein, carbs, fat, nutrition_full,
            description, instructions, tips, sub_recipes, dietary_info,
            is_complete, source_images
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s
        )
        """,
        (
            catalog_id,
            recipe.get("name", "Untitled"),
            recipe.get("chapter"),
            recipe.get("chapter_number"),
            str(recipe.get("page_number", "")) if recipe.get("page_number") else None,
            meal_type,
            dish_role,
            recipe.get("serves"),
            recipe.get("prep_time"),
            recipe.get("cook_time"),
            recipe.get("total_time"),
            recipe.get("calories"),
            recipe.get("protein"),
            recipe.get("carbs"),
            recipe.get("fat"),
            recipe.get("nutrition_full"),
            recipe.get("description"),
            json.dumps(recipe.get("instructions", [])),
            json.dumps(recipe.get("tips", [])),
            json.dumps(recipe.get("sub_recipes", [])),
            json.dumps(recipe.get("dietary_info", [])),
            recipe.get("is_complete", True),
            json.dumps(recipe.get("source_images", [recipe.get("source_image")])),
        )
    )

    return cursor.lastrowid


def main():
    parser = argparse.ArgumentParser(description="Import JSON catalog into MariaDB")
    parser.add_argument("file", help="Path to JSON catalog file")
    parser.add_argument("--name", "-n", help="Catalog name (default: derived from filename)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    print(f"Importing catalog: {args.file}")

    try:
        stats = import_catalog(args.file, args.name)

        print(f"\n✓ Import complete!")
        print(f"  Catalog: {stats['catalog_name']} (ID: {stats['catalog_id']})")
        print(f"  Recipes: {stats['recipes_imported']}")
        print(f"  Chapters: {stats['chapters_imported']}")
        print(f"  Ingredients: {stats['ingredients_imported']}")

        if stats["skipped"]:
            print(f"  Skipped: {stats['skipped']}")

        if stats["errors"] and args.verbose:
            print("\nErrors:")
            for error in stats["errors"]:
                print(f"  - {error}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
