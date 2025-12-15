"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================
# Enums
# ============================================

class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    dessert = "dessert"
    snack = "snack"
    any = "any"


class DishRole(str, Enum):
    main = "main"
    side = "side"
    sub_recipe = "sub_recipe"


# ============================================
# Recipe Schemas
# ============================================

class RecipeBase(BaseModel):
    name: str
    chapter: Optional[str] = None
    meal_type: MealType = MealType.any
    dish_role: DishRole = DishRole.main
    serves: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    calories: Optional[str] = None
    protein: Optional[str] = None
    carbs: Optional[str] = None
    fat: Optional[str] = None
    description: Optional[str] = None


class RecipeList(RecipeBase):
    """Recipe summary for list views"""
    id: int
    dietary_info: List[str] = []

    class Config:
        from_attributes = True


class RecipeDetail(RecipeBase):
    """Full recipe details"""
    id: int
    catalog_id: Optional[int] = None
    chapter_number: Optional[str] = None
    page_number: Optional[str] = None
    total_time: Optional[str] = None
    nutrition_full: Optional[str] = None
    ingredients: List[str] = []
    instructions: List[str] = []
    tips: List[str] = []
    sub_recipes: List[dict] = []
    dietary_info: List[str] = []
    is_complete: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RecipeSearchRequest(BaseModel):
    """Search/filter request"""
    query: Optional[str] = None
    meal_type: Optional[MealType] = None
    dish_role: Optional[DishRole] = None
    dietary: Optional[List[str]] = None
    catalog_id: Optional[int] = None
    limit: int = Field(default=20, le=100)
    offset: int = 0


# ============================================
# Catalog Schemas
# ============================================

class CatalogBase(BaseModel):
    name: str
    source_folder: Optional[str] = None
    model_used: Optional[str] = None


class CatalogList(CatalogBase):
    """Catalog summary for list views"""
    id: int
    recipe_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CatalogImportRequest(BaseModel):
    """Request to import a JSON catalog"""
    file_path: str
    name: Optional[str] = None


class CatalogImportResponse(BaseModel):
    """Response after importing a catalog"""
    success: bool
    catalog_id: Optional[int] = None
    catalog_name: Optional[str] = None
    recipes_imported: int = 0
    chapters_imported: int = 0
    ingredients_imported: int = 0
    skipped: int = 0
    errors: List[str] = []


# ============================================
# Meal Plan Schemas
# ============================================

class MealPlanBase(BaseModel):
    name: Optional[str] = None
    meal_types: List[MealType] = [MealType.dinner]
    recipe_count: int = 5


class MealPlanCreate(MealPlanBase):
    """Request to generate a new meal plan"""
    pass


class MealPlanList(MealPlanBase):
    """Meal plan summary for list views"""
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MealPlanDetail(MealPlanBase):
    """Full meal plan with recipes"""
    id: int
    recipes: List[RecipeList] = []
    grocery_list: Optional[dict] = None
    prep_plan: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================
# Pagination
# ============================================

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    pagination: PaginationMeta


class RecipeListResponse(PaginatedResponse):
    recipes: List[RecipeList]


class CatalogListResponse(BaseModel):
    catalogs: List[CatalogList]


class MealPlanListResponse(BaseModel):
    plans: List[MealPlanList]


# ============================================
# Stats / Dashboard
# ============================================

class DashboardStats(BaseModel):
    recipe_count: int = 0
    catalog_count: int = 0
    plan_count: int = 0
    user_count: int = 0
    recent_plans: List[MealPlanList] = []
