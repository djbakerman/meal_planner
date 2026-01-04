
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force loaded env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', '.env')
load_dotenv(env_path)

print(f"Loading env from: {env_path}")

from sqlalchemy import text
from api.database import SessionLocal, engine, DATABASE_URL

print(f"Connecting using: {DATABASE_URL}")

def migrate():
    print("Running migration: Adding Social Features...")
    
    with engine.connect() as connection:
        # 1. Add is_public column
        try:
            print("Adding 'is_public' column to meal_plans table...")
            connection.execute(text("ALTER TABLE meal_plans ADD COLUMN is_public BOOLEAN DEFAULT FALSE"))
            print("Column 'is_public' added.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column 'is_public' already exists. Skipping.")
            else:
                print(f"Update note: {e}")

        # 2. Create plan_likes table
        try:
            print("Creating 'plan_likes' table...")
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS plan_likes (
                    user_id INT NOT NULL,
                    plan_id INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, plan_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (plan_id) REFERENCES meal_plans(id) ON DELETE CASCADE
                )
            """))
            print("Table 'plan_likes' created/verified.")
        except Exception as e:
            print(f"Error creating table: {e}")
        
        connection.commit()
    
    print("Social Features Migration complete!")

if __name__ == "__main__":
    migrate()
