import sys
import os
from dotenv import load_dotenv

# Add project root to path so we can import 'api'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load .env explicitly
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(env_path)

from sqlalchemy import create_engine, text
from api.database import DATABASE_URL

# Helper to run raw SQL for migration (since we don't have Alembic set up perfectly)
def migrate_user_table():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Migrating 'users' table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN google_id VARCHAR(255) UNIQUE DEFAULT NULL"))
            print("Added google_id column.")
        except Exception as e:
            print(f"Skipping google_id (probably exists): {e}")

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT NULL"))
            print("Added avatar_url column.")
        except Exception as e:
            print(f"Skipping avatar_url (probably exists): {e}")
            
        try:
             # Make password nullable if it isn't already (OAuth users might not have one)
             # MySQL specific syntax
             conn.execute(text("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NULL"))
             print("Made password_hash nullable.")
        except Exception as e:
             print(f"Could not make password_hash nullable: {e}")
             
        conn.commit()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_user_table()
