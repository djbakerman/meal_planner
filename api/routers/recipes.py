
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from api.database import get_db
from api.models import orm
from api import schemas

router = APIRouter(
    prefix="/api/recipes",
    tags=["recipes"]
)

@router.get("/", response_model=List[schemas.Recipe])
def read_recipes(
    skip: int = 0, 
    limit: int = 20, 
    meal_type: Optional[str] = None,
    dish_role: Optional[str] = None,
    search: Optional[str] = None,
    catalog_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    List recipes with optional filters and search.
    """
    query = db.query(orm.Recipe)
    
    if meal_type:
        query = query.filter(orm.Recipe.meal_type == meal_type)
        
    if dish_role:
        query = query.filter(orm.Recipe.dish_role == dish_role)
        
    if catalog_id:
        query = query.filter(orm.Recipe.catalog_id == catalog_id)
    else:
        # Default: Hide orphaned/archived recipes (where catalog was deleted)
        query = query.filter(orm.Recipe.catalog_id != None)
        
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                orm.Recipe.name.ilike(search_term),
                orm.Recipe.description.ilike(search_term),
                orm.Recipe.chapter.ilike(search_term)
            )
        )
        
    recipes = query.order_by(orm.Recipe.name).offset(skip).limit(limit).all()
    return recipes

@router.get("/count", response_model=dict)
def count_recipes(db: Session = Depends(get_db)):
    """Get total count of recipes."""
    count = db.query(orm.Recipe).count()
    return {"count": count}

@router.get("/{recipe_id}", response_model=schemas.Recipe)
def read_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Get a specific recipe by ID."""
    recipe = db.query(orm.Recipe).filter(orm.Recipe.id == recipe_id).first()
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

@router.put("/{recipe_id}", response_model=schemas.Recipe)
def update_recipe(recipe_id: int, recipe_update: schemas.RecipeUpdate, db: Session = Depends(get_db)):
    """Update a recipe."""
    recipe = db.query(orm.Recipe).filter(orm.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    update_data = recipe_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(recipe, key, value)
    
    db.commit()
    db.refresh(recipe)
    return recipe

@router.delete("/{recipe_id}")
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """Delete a recipe."""
    recipe = db.query(orm.Recipe).filter(orm.Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    
    db.delete(recipe)
    db.commit()
    return {"status": "success", "message": "Recipe deleted"}
