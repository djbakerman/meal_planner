
import sys
import os
import json
import argparse
from pathlib import Path

# Add parent directory to path to import api
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.database import SessionLocal as DefaultSessionLocal, engine as default_engine, Base
from api.models.orm import Catalog, Chapter, Recipe, Ingredient
from backend.llm import query_llm, parse_json_response
import time

def import_catalog(json_path: str, db: Session, verbose: bool = False, enrich: bool = False):
    """Import a JSON catalog into the database."""
    print(f"Reading catalog from {json_path}...")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Create Catalog entry
    # Infer name from filename if not in metadata
    catalog_name = Path(json_path).stem.replace('_', ' ').title()
    metadata = data.get("metadata", {})
    
    # Check if catalog already exists (by name and source folder combo roughly)
    # For now simplicity: just create new one or update if name matches exactly?
    # Let's create new for safety, user can delete old ones.
    
    catalog = Catalog(
        name=catalog_name,
        source_folder=metadata.get("source_folder"),
        model_used=metadata.get("model_used"),
        metadata_info=metadata,
        recipe_count=len(data.get("recipes", []))
    )
    
    db.add(catalog)
    db.commit()
    db.refresh(catalog)
    print(f"✅ Created Catalog: {catalog.name} (ID: {catalog.id})")

    # Import Chapters
    chapters_data = data.get("chapters", [])
    for chap_data in chapters_data:
        chapter = Chapter(
            catalog_id=catalog.id,
            chapter_number=str(chap_data.get("chapter_number", "")),
            chapter_title=chap_data.get("chapter_title"),
            recipe_list=chap_data.get("recipe_list", [])
        )
        db.add(chapter)
    
    print(f"✅ Imported {len(chapters_data)} chapters")

    # Import Recipes
    recipes_data = data.get("recipes", [])
    recipe_count = 0
    
    for r_data in recipes_data:
        # Clean up some fields
        try:
            # Handle list fields for JSON columns
            instructions = r_data.get("instructions", [])
            
            # Validation: Skip recipes with missing instructions
            if not instructions:
                if verbose:
                    print(f"  ⚠️  Skipping: '{r_data.get('name')}' (missing instructions)")
                continue

            # Title Case Helper
            def to_title_case(s):
                if not s:
                    return s
                import string
                return string.capwords(s)

            recipe_name = r_data.get("name") or "Unknown Recipe"
            recipe_name = to_title_case(recipe_name)
            
            ingredients = r_data.get("ingredients", [])
            
            # Use r_data references for internal logic, but recipe_name for display/AI prompt
        
            # --- AI ENRICHMENT START ---
            if enrich:
                # Check for missing critical fields
                missing_fields = []
                if not r_data.get("calories") or r_data.get("calories") == "": missing_fields.append("calories")
                if not r_data.get("prep_time") or r_data.get("prep_time") == "": missing_fields.append("prep_time")
                if not r_data.get("cook_time") or r_data.get("cook_time") == "": missing_fields.append("cook_time")
                if not r_data.get("meal_type") or r_data.get("meal_type") == "any": missing_fields.append("meal_type")

                if missing_fields:
                    if verbose:
                        print(f"  🧠 Enriching '{recipe_name}' (Missing: {', '.join(missing_fields)})...")
                    
                    # Construct Prompt
                    prompt = f"""
                    Analyze this recipe and provide the missing metadata in JSON format.
                    Recipe: {recipe_name}
                    Ingredients: {'; '.join(ingredients)}
                    Instructions: {'; '.join(instructions[:5])}...

                    Return a JSON object with these keys (estimate if needed):
                    {{
                        "calories": "e.g. 500 kcal per serving",
                        "protein": "e.g. 30g per serving",
                        "carbs": "e.g. 40g per serving", 
                        "fat": "e.g. 20g per serving",
                        "prep_time": "e.g. 15 mins",
                        "cook_time": "e.g. 30 mins",
                        "total_time": "e.g. 45 mins",
                        "serves": "e.g. 4",
                        "meal_type": "One of: breakfast, lunch, dinner, snack, dessert",
                        "meal_type": "One of: breakfast, lunch, dinner, snack, dessert",
                        "dish_role": "One of: main, side, sub_recipe",
                        "sub_recipes": ["List of recipe names mentioned in ingredients, e.g. 'Basic Pie Crust', 'Tartar Sauce'. Empty if none."]
                    }}
                    Output ONLY JSON.
                    """
                    
                    # Call AI
                    ai_response = query_llm(prompt, json_mode=True)
                    enriched_data = parse_json_response(ai_response)
                    
                    if enriched_data:
                        # --- SANITIZATION HELPERS ---
                        def clean_meal_type(mt):
                            if not mt: return "any"
                            mt = mt.lower().strip()
                            valid_types = {'breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'main', 'side', 'any'}
                            if mt in valid_types:
                                return mt
                            # Mappings
                            if "condiment" in mt or "sauce" in mt: return "side"
                            if "appetizer" in mt: return "snack"
                            if "soup" in mt or "salad" in mt: return "lunch" # Arbitrary but safer
                            return "any"

                        def clean_short_string(s, max_len=20):
                            if not s: return ""
                            s = str(s).strip()
                            if s.lower() in ["not provided", "n/a", "unavailable", "unknown"]:
                                return ""
                            # If too long, try to extract digits + unit
                            if len(s) > max_len:
                                import re
                                # Extract "123 kcal" or "10 mins"
                                match = re.search(r'(\d+(?:-\d+)?\s*\w+)', s)
                                if match:
                                    return match.group(1)[:max_len]
                                return s[:max_len]
                            return s

                        # Update fields if they were missing
                        if not r_data.get("calories"): r_data["calories"] = clean_short_string(enriched_data.get("calories", ""))
                        if not r_data.get("protein"): r_data["protein"] = clean_short_string(enriched_data.get("protein", ""))
                        if not r_data.get("carbs"): r_data["carbs"] = clean_short_string(enriched_data.get("carbs", ""))
                        if not r_data.get("fat"): r_data["fat"] = clean_short_string(enriched_data.get("fat", ""))
                        
                        # Times can be a bit longer (50 chars), but clean anyway
                        if not r_data.get("prep_time"): r_data["prep_time"] = clean_short_string(enriched_data.get("prep_time", ""), 45)
                        if not r_data.get("cook_time"): r_data["cook_time"] = clean_short_string(enriched_data.get("cook_time", ""), 45)
                        if not r_data.get("total_time"): r_data["total_time"] = clean_short_string(enriched_data.get("total_time", ""), 45)
                        
                        if not r_data.get("meal_type") or r_data.get("meal_type") == "any": 
                            r_data["meal_type"] = clean_meal_type(enriched_data.get("meal_type", "dinner"))
                        
                        if not r_data.get("dish_role"): 
                            role = enriched_data.get("dish_role", "main").lower()
                            r_data["dish_role"] = role if role in ['main', 'side', 'sub_recipe'] else 'main'
                            
                        # Enrich sub_recipes if missing
                        if not r_data.get("sub_recipes") and enriched_data.get("sub_recipes"):
                            r_data["sub_recipes"] = enriched_data.get("sub_recipes", [])
                            
                        if not r_data.get("serves"): r_data["serves"] = clean_short_string(str(enriched_data.get("serves", "1")), 45)
                        
                        if verbose: print(f"    ✨ Enriched: {r_data.get('meal_type')} | {r_data.get('calories')}")
                    else:
                        print(f"    ⚠️ Failed to enrich '{recipe_name}'")
            # --- AI ENRICHMENT END ---

            tips = r_data.get("tips", [])
            sub = r_data.get("sub_recipes", [])
            diet = r_data.get("dietary_info", [])
            imgs = r_data.get("source_images", []) # or "source_image" handling
            
            # Normalize source_images
            if "source_image" in r_data and not imgs:
                imgs = [r_data["source_image"]]

            # recipe_name variable is already defined above

            recipe = Recipe(
                catalog_id=catalog.id,
                name=recipe_name,
                chapter=r_data.get("chapter"),
                chapter_number=str(r_data.get("chapter_number", "")),
                page_number=str(r_data.get("page_number", "")),  # might not exist in JSON yet
                meal_type=r_data.get("meal_type") or "any",
                dish_role=r_data.get("dish_role", "main"),
                serves=str(r_data.get("serves", "")),
                prep_time=str(r_data.get("prep_time", "")),
                cook_time=str(r_data.get("cook_time", "")),
                total_time=str(r_data.get("total_time", "")),
                calories=str(r_data.get("calories", "")),
                protein=str(r_data.get("protein", "")),
                carbs=str(r_data.get("carbs", "")),
                fat=str(r_data.get("fat", "")),
                nutrition_full=r_data.get("nutrition_full"),
                description=r_data.get("description"),
                instructions=instructions,
                tips=tips,
                sub_recipes=sub,
                dietary_info=diet,
                is_complete=r_data.get("is_complete", True),
                source_images=imgs
            )
            
            db.add(recipe)
            db.flush() # Get recipe.id
            
            # Import Ingredients
            # ingredients already extracted above
            for idx, ing_text in enumerate(ingredients):
                ing = Ingredient(
                    recipe_id=recipe.id,
                    ingredient_text=ing_text,
                    sort_order=idx
                )
                db.add(ing)
                
            recipe_count += 1
            if verbose:
                print(f"  Imported: {recipe.name}")
                
        except Exception as e:
            print(f"❌ Error importing recipe {r_data.get('name')}: {e}")
            db.rollback()
            continue

    db.commit()
    print(f"✅ Successfully imported {recipe_count} recipes and their ingredients.")


def main():
    parser = argparse.ArgumentParser(description="Import JSON recipe catalog into MariaDB")
    parser.add_argument("catalog_path", help="Path to the JSON catalog file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print details during import")
    parser.add_argument("--enrich", action="store_true", help="Use AI to fill missing metadata (calories, times, etc)")
    parser.add_argument("--init-db", action="store_true", help="Initialize database tables before importing")
    
    parser.add_argument("--db-user", "-u", help="Database username")
    parser.add_argument("--db-pass", "-p", help="Database password")
    parser.add_argument("--db-host", "-H", default="localhost", help="Database host")
    parser.add_argument("--db-name", "-d", default="meal_planner", help="Database name")
    parser.add_argument("--db-port", "-P", default="8890", help="Database port")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.catalog_path):
        print(f"Error: File not found: {args.catalog_path}")
        return

    # Determine DB connection
    if args.db_user and args.db_pass:
        print(f"Connecting to database as {args.db_user}...")
        db_url = f"mysql+pymysql://{args.db_user}:{args.db_pass}@{args.db_host}:{args.db_port}/{args.db_name}"
        active_engine = create_engine(db_url, pool_pre_ping=True)
        ActiveSession = sessionmaker(autocommit=False, autoflush=False, bind=active_engine)
    else:
        active_engine = default_engine
        ActiveSession = DefaultSessionLocal

    # Check for Tables
    if args.init_db:
        print("Initializing database tables...")
        Base.metadata.create_all(bind=active_engine)
        print("Tables created.")

    # Create session
    db = ActiveSession()
    try:
        import_catalog(args.catalog_path, db, verbose=args.verbose, enrich=args.enrich)
    finally:
        db.close()

if __name__ == "__main__":
    main()
