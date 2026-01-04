
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Database URL - default to local MariaDB/MySQL
# Format: mysql+pymysql://user:password@host:port/dbname
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Try to construct from individual DB_ vars (common in PHP/Laravel setups)
    host = os.environ.get("DB_HOST", "localhost")
    user = os.environ.get("DB_USERNAME", "mealplanner")
    password = os.environ.get("DB_PASSWORD", "mealplanner")
    db_name = os.environ.get("DB_DATABASE", "meal_planner")
    port = os.environ.get("DB_PORT", "3306")
    socket = os.environ.get("DB_SOCKET") # Custom one usually not in std env but logical to add

    if socket:
         DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}/{db_name}?unix_socket={socket}"
    else:
         DATABASE_URL = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}"

SQLALCHEMY_DATABASE_URL = DATABASE_URL
print(f"DEBUG: database.py using URL: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
