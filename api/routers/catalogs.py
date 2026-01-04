
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import os

from api.database import get_db
from api.models import orm
from api import schemas
from scripts.import_catalog import import_catalog

router = APIRouter(
    prefix="/api/catalogs",
    tags=["catalogs"]
)

@router.get("/", response_model=List[schemas.Catalog])
def read_catalogs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all catalogs."""
    catalogs = db.query(orm.Catalog).offset(skip).limit(limit).all()
    return catalogs

@router.get("/{catalog_id}", response_model=schemas.Catalog)
def read_catalog(catalog_id: int, db: Session = Depends(get_db)):
    """Get a specific catalog by ID."""
    catalog = db.query(orm.Catalog).filter(orm.Catalog.id == catalog_id).first()
    if catalog is None:
        raise HTTPException(status_code=404, detail="Catalog not found")
    return catalog

@router.post("/import")
def import_catalog_endpoint(
    file: UploadFile = File(...), 
    enrich: bool = Form(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Import a catalog from an uploaded JSON file.
    """
    # Ensure upload directory exists
    upload_dir = "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    
    with open(file_path, "wb") as buffer:
        import shutil
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(import_catalog_task, file_path, enrich=enrich)
    
    return {"message": "Import started in background", "file": file.filename}

def import_catalog_task(file_path: str, enrich: bool = False):
    # Create a fresh session for the background thread
    from api.database import SessionLocal
    db = SessionLocal()
    try:
        import_catalog(file_path, db, verbose=True, enrich=enrich)
    finally:
        db.close()

@router.put("/{catalog_id}", response_model=schemas.Catalog)
def update_catalog(catalog_id: int, catalog_update: schemas.CatalogUpdate, db: Session = Depends(get_db)):
    """Update a catalog name."""
    catalog = db.query(orm.Catalog).filter(orm.Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    
    if catalog_update.name:
        catalog.name = catalog_update.name
    
    db.commit()
    db.refresh(catalog)
    return catalog

@router.delete("/{catalog_id}")
def delete_catalog(catalog_id: int, db: Session = Depends(get_db)):
    """Delete a catalog and all its recipes."""
    catalog = db.query(orm.Catalog).filter(orm.Catalog.id == catalog_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Catalog not found")
    
    # Smart Cleanup Strategy:
    # 1. Iterate all recipes in this catalog.
    # 2. If recipe is used in ANY meal plan -> Keep it, but set catalog_id = None (Archive).
    # 3. If recipe is NOT used -> Delete it (Garbage Collection).
    
    deleted_count = 0
    archived_count = 0
    
    # We must iterate a copy of the list because we are modifying it (deleting/unlinking)
    # Actually, iterating the relationship is fine, but deleting from db might affect iteration if not careful.
    # Safer to fetch list first.
    recipes = list(catalog.recipes)
    
    for recipe in recipes:
        # Check usage
        # Note: 'meal_plan_links' is the relationship to MealPlanRecipe
        if recipe.meal_plan_links: 
             recipe.catalog_id = None # Archive / Orphan
             archived_count += 1
        else:
             db.delete(recipe) # Garbage Collect
             deleted_count += 1
             
    db.delete(catalog)
    db.commit()
    
    return {
        "status": "success", 
        "message": f"Catalog deleted. {deleted_count} recipes purged, {archived_count} archived."
    }
