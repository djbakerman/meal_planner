
import sys
import os
import json
import argparse
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
# Load .env explicitly so api.database picks it up
env_path = Path(__file__).parent.parent / "api" / ".env"
load_dotenv(env_path)

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from api.database import SessionLocal as DefaultSessionLocal, engine as default_engine

def compare_data(json_path: str, db_user=None, db_pass=None, db_host="localhost", db_name="meal_planner", db_port=3306, db_socket=None):
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    # Load JSON
    print(f"Reading JSON: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    json_recipes = data.get("recipes", [])
    print(f"Found {len(json_recipes)} recipes in JSON.")

    # Connect to DB
    if db_user and db_pass:
        if db_socket:
             db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}/{db_name}?unix_socket={db_socket}"
        else:
             db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
    else:
        # Use environment vars handled by api.database
        engine = default_engine
        Session = DefaultSessionLocal

    db = Session()
    
    print("\n🔍 Checking Database...")
    
    issues = 0
    
    for r_json in json_recipes:
        name = r_json.get("name")
        # Find in DB
        # Use raw SQL for speed or ORM
        # Let's use raw SQL to see exactly what is stored
        existing = db.execute(
            text("SELECT id, instructions, tips FROM recipes WHERE name = :name"),
            {"name": name}
        ).mappings().first()
        
        if not existing:
            print(f"❌ MISSING in DB: {name}")
            issues += 1
            continue
            
        # Check ingredients (normalized table)
        ing_count_db = db.execute(
            text("SELECT COUNT(*) FROM ingredients WHERE recipe_id = :rid"),
            {"rid": existing["id"]}
        ).scalar()
        
        ing_json = r_json.get("ingredients", [])
        if ing_count_db == 0 and len(ing_json) > 0:
             print(f"❌ EMPTY in DB: Ingredients for '{name}' (JSON has {len(ing_json)})")
             issues += 1
        elif ing_count_db != len(ing_json):
             print(f"⚠️ Ingredient count mismatch for '{name}': DB={ing_count_db}, JSON={len(ing_json)}")

        # Check instructions
        instr_db = existing["instructions"]
        instr_json = r_json.get("instructions", [])
        
        # Check if DB instructions is a string (bad) or list (good)
        if isinstance(instr_db, str):
             # It might be double-JSON encoded or just a string
             try:
                 parsed = json.loads(instr_db)
                 if isinstance(parsed, list):
                     pass # Good, it was just JSON string from DB driver
                 else:
                     print(f"⚠️ Instructions format warning for '{name}': Stored as string, not list.")
             except:
                 print(f"⚠️ Instructions format warning for '{name}': Stored as raw string.")
                 
        if not instr_json:
             print(f"⚠️ Source JSON has NO instructions for '{name}'")

        if not instr_db and instr_json:
             print(f"❌ EMPTY in DB: Instructions for '{name}' (JSON has {len(instr_json)} steps)")
             issues += 1
             
    print(f"\nDone. Found {issues} potential issues.")
    db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("json_path")
    parser.add_argument("--db-user", "-u")
    parser.add_argument("--db-pass", "-p")
    parser.add_argument("--db-socket", "-S")
    args = parser.parse_args()
    
    compare_data(args.json_path, args.db_user, args.db_pass, db_socket=args.db_socket)
