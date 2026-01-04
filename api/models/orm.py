
from sqlalchemy import Column, Integer, String, Text, ForeignKey, JSON, Enum, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base

class Catalog(Base):
    __tablename__ = "catalogs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    source_folder = Column(String(500))
    model_used = Column(String(100))
    recipe_count = Column(Integer, default=0)
    metadata_info = Column("metadata", JSON)  # 'metadata' is reserved in SQLAlchemy Base
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chapters = relationship("Chapter", back_populates="catalog", cascade="all, delete-orphan")
    recipes = relationship("Recipe", back_populates="catalog")

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=False)
    chapter_number = Column(String(50))
    chapter_title = Column(String(255))
    recipe_list = Column(JSON)

    catalog = relationship("Catalog", back_populates="chapters")

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"))
    name = Column(String(255), nullable=False, index=True)
    chapter = Column(String(255))
    chapter_number = Column(String(50))
    page_number = Column(String(20))
    meal_type = Column(Enum('breakfast', 'lunch', 'dinner', 'dessert', 'snack', 'main', 'side', 'any'), default='any')
    dish_role = Column(Enum('main', 'side', 'sub_recipe'), default='main')
    serves = Column(String(50))
    prep_time = Column(String(50))
    cook_time = Column(String(50))
    total_time = Column(String(50))
    calories = Column(String(20))
    protein = Column(String(20))
    carbs = Column(String(20))
    fat = Column(String(20))
    nutrition_full = Column(Text)
    description = Column(Text)
    instructions = Column(JSON)
    tips = Column(JSON)
    sub_recipes = Column(JSON)
    dietary_info = Column(JSON)
    is_complete = Column(Boolean, default=True)
    source_images = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    catalog = relationship("Catalog", back_populates="recipes")
    ingredients = relationship("Ingredient", back_populates="recipe", cascade="all, delete-orphan")
    meal_plan_links = relationship("MealPlanRecipe", back_populates="recipe")

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    ingredient_text = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)

    recipe = relationship("Recipe", back_populates="ingredients")

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    name = Column(String(255))
    is_public = Column(Boolean, default=False)
    meal_types = Column(JSON)
    recipe_count = Column(Integer, default=5)
    target_servings = Column(Integer, default=4)
    grocery_list = Column(JSON)
    prep_plan = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    plan_recipes = relationship("MealPlanRecipe", back_populates="meal_plan", cascade="all, delete-orphan")
    likes = relationship("PlanLike", cascade="all, delete-orphan")

    @property
    def likes_count(self):
        return len(self.likes)

class MealPlanRecipe(Base):
    __tablename__ = "meal_plan_recipes"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    position = Column(Integer, default=0)

    meal_plan = relationship("MealPlan", back_populates="plan_recipes")
    recipe = relationship("Recipe", back_populates="meal_plan_links")

class PlanLike(Base):
    __tablename__ = "plan_likes"
    
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    plan_id = Column(Integer, ForeignKey("meal_plans.id"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default='user') # 'admin' or 'user'
    google_id = Column(String(255), unique=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    preferences = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
