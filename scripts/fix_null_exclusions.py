import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(override=True)

# DB Config (Same as before)
DB_USER = os.getenv("DB_USERNAME", "meal_user")
DB_PASS = os.getenv("DB_PASSWORD", "1luvMySQL!")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "8889")
DB_NAME = os.getenv("DB_DATABASE", "meal_planner")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def fix_data():
    print(f"Connecting to Database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("Updating NULL exclusions to '[]'...")
            # Handle native NULL
            sql_null = text("UPDATE meal_plans SET excluded_ingredients = '[]' WHERE excluded_ingredients IS NULL;")
            res1 = conn.execute(sql_null)
            print(f"Fixed NULLs: {res1.rowcount} rows.")
            
            # Handle string "null" (JSON null) if any
            sql_json_null = text("UPDATE meal_plans SET excluded_ingredients = '[]' WHERE JSON_TYPE(excluded_ingredients) = 'NULL';")
            # Might throw error if JSON_TYPE not supported in this version, wrap in try/catch?
            try:
                res2 = conn.execute(sql_json_null)
                print(f"Fixed JSON NULLs: {res2.rowcount} rows.")
            except Exception as e:
                print(f"JSON_TYPE check failed (might be old MySQL): {e}")
                
            conn.commit()
            print("Fix Complete.")
            
    except Exception as e:
        print(f"Fix Failed: {e}")

if __name__ == "__main__":
    fix_data()
