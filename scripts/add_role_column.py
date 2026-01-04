import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force loaded env
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api', '.env')
load_dotenv(env_path)

print(f"Loading env from: {env_path}")
print(f"DB Host: {os.getenv('DB_HOST')}")

from sqlalchemy import text
from api.database import SessionLocal, engine, DATABASE_URL

print(f"Connecting using: {DATABASE_URL}")

def migrate():
    print("Running migration: Adding 'role' column to users table...")
    
    with engine.connect() as connection:
        # Check if column exists first (simple try/catch approach for potential re-runs)
        try:
            connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
            print("Column 'role' added.")
        except Exception as e:
            if "Duplicate column name" in str(e):
                print("Column 'role' already exists. Skipping ADD.")
            else:
                print(f"Update note: {e}")

        # Update 'dan' to admin
        print("Promoting user 'dan' to admin...")
        result = connection.execute(text("UPDATE users SET role = 'admin' WHERE username = 'dan'"))
        print(f"Rows updated: {result.rowcount}")
        
        # Ensure others are 'user' (handled by default but good to force if nulls exist)
        connection.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL"))
        
        connection.commit()
    
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
