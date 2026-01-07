import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# DB Config
DB_USER = os.getenv("DB_USERNAME", "meal_user")
DB_PASS = os.getenv("DB_PASSWORD", "1luvMySQL!")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "8889")
DB_NAME = os.getenv("DB_DATABASE", "meal_planner")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def apply_migration():
    print(f"Connecting to Database...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Check if column exists
            check_sql = text("""
                SELECT count(*) 
                FROM information_schema.columns 
                WHERE table_schema = DATABASE()
                AND table_name = 'meal_plans' 
                AND column_name = 'excluded_ingredients';
            """)
            result = conn.execute(check_sql)
            exists = result.scalar()
            
            if exists:
                print("Column 'excluded_ingredients' already exists.")
            else:
                print("Adding column 'excluded_ingredients'...")
                alter_sql = text("ALTER TABLE meal_plans ADD COLUMN excluded_ingredients JSON NOT NULL;")
                # Note: 'DEFAULT (JSON_ARRAY())' syntax depends on version, let's keep it simple NOT NULL 
                # but we need a default for existing rows? 
                # MySQL 5.7 doesn't support DEFAULT for JSON. 
                # We'll set NOT NULL and rely on app logic or UPDATE existing rows if needed.
                # Actually, safest is: ADD COLUMN excluded_ingredients JSON; then UPDATE to []; then ALTER to NOT NULL.
                # Or just Allow NULL for safety.
                # User requested NOT NULL + Default.
                # Let's try flexible approach.
                conn.execute(alter_sql)
                
                # Update existing rows to empty list
                update_sql = text("UPDATE meal_plans SET excluded_ingredients = '[]' WHERE excluded_ingredients IS NULL;")
                conn.execute(update_sql)
                conn.commit()
                
                print("Migration successful.")
            
    except Exception as e:
        print(f"Migration Failed: {e}")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

if __name__ == "__main__":
    apply_migration()
