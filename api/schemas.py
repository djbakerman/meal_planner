
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ChapterBase(BaseModel):
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    recipe_list: List[str] = []

class Chapter(ChapterBase):
    id: int
    catalog_id: int

    class Config:
        from_attributes = True

class CatalogBase(BaseModel):
    name: str
    source_folder: Optional[str] = None
    model_used: Optional[str] = None
    recipe_count: int = 0
    metadata_info: Optional[Any] = None

class Catalog(CatalogBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    chapters: List[Chapter] = []

    class Config:
        from_attributes = True

class CatalogUpdate(BaseModel):
    name: Optional[str] = None

class ImportRequest(BaseModel):
    file_path: str

class Ingredient(BaseModel):
    id: int
    ingredient_text: str
    sort_order: int

    class Config:
        from_attributes = True

class RecipeBase(BaseModel):
    name: str
    chapter: Optional[str] = None
    page_number: Optional[str] = None
    meal_type: Optional[str] = "any"
    dish_role: Optional[str] = "main"
    serves: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    calories: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[Any] = []
    tips: Optional[Any] = []
    dietary_info: Optional[Any] = []
    
    # We use Any above because sometimes DB returns None or empty string for JSON columns
    #Ideally we would use a validator to force them to list, but Any is safest for now to unblock.

class Recipe(RecipeBase):
    id: int
    catalog_id: Optional[int] = None
    catalog: Optional[Catalog] = None
    ingredients: List[Ingredient] = []
    
    class Config:
        from_attributes = True

class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    meal_type: Optional[str] = None
    dish_role: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    serves: Optional[str] = None
    calories: Optional[str] = None

class PlanGenerateRequest(BaseModel):
    recipe_count: int = 5
    days: Optional[int] = None # If provided, overrides recipe_count logic
    meal_types: List[str] = ["dinner"]
    user_id: Optional[int] = None
    catalog_id: Optional[int] = None
    excluded_ingredients: List[str] = []

class MealPlanRecipe(BaseModel):
    recipe_id: int
    position: int
    recipe: Optional[Recipe] = None

    class Config:
        from_attributes = True

class SwapRequest(BaseModel):
    recipe_ids: List[int]
    mode: str = "random"  # "random" or "similar" or "catalog"
    catalog_id: Optional[int] = None
    user_id: Optional[int] = None

class RecipeListRequest(BaseModel):
    recipe_ids: List[int]
    user_id: Optional[int] = None

class RecipeAddRequest(BaseModel):
    recipe_id: Optional[int] = None
    random: bool = False
    catalog_id: Optional[int] = None
    meal_type: Optional[str] = None # Optional filter for random add
    user_id: Optional[int] = None

class PlanUpdateRequest(BaseModel):
    name: Optional[str] = None
    user_id: Optional[int] = None

class MealPlan(BaseModel):
    id: int
    user_id: Optional[int] = None
    name: str
    is_public: bool = False
    likes_count: int = 0
    meal_types: Optional[List[str]] = None
    recipe_count: int
    created_at: datetime
    plan_recipes: List[MealPlanRecipe] = []
    grocery_list: Optional[Any] = None
    prep_plan: Optional[Any] = None

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class OAuthLoginRequest(BaseModel):
    email: str
    google_id: str
    avatar_url: Optional[str] = None
    name: Optional[str] = None

class User(UserBase):
    id: int
    role: str = "user"
    created_at: datetime
    
    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    success: bool
    user: Optional[User] = None
    error: Optional[str] = None
