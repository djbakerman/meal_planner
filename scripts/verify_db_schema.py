import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Force reload for local env
load_dotenv(override=True)

# DB Config
DB_USER = os.getenv("DB_USERNAME", "meal_user")
DB_PASS = os.getenv("DB_PASSWORD", "1luvMySQL!")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "8889")
DB_NAME = os.getenv("DB_DATABASE", "meal_planner")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def verify_schema():
    print(f"Connecting to Database: {DB_NAME} on {DB_HOST}:{DB_PORT}...")
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        # 1. Check Table Existence
        tables = inspector.get_table_names()
        required_tables = ['meal_plans', 'recipes', 'ingredients', 'users']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ CRITICAL FAILURE: Missing tables: {missing_tables}")
            return
        else:
            print(f"✅ Core tables found: {required_tables}")
            
        # 2. Check Specific Columns
        # Check meal_plans for excluded_ingredients
        columns = [c['name'] for c in inspector.get_columns('meal_plans')]
        if 'excluded_ingredients' in columns:
            print(f"✅ SUCCESS: 'excluded_ingredients' column found in 'meal_plans'.")
        else:
            print(f"❌ FAILURE: 'excluded_ingredients' column MISSING in 'meal_plans'.")
            
        print("\n--- Schema Verification Complete ---")

    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    verify_schema()
