from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from api.database import get_db
from api.models import orm

router = APIRouter(
    prefix="/api/ingredients",
    tags=["ingredients"]
)

class DensitySchema(BaseModel):
    ingredient_key: str
    display_name: str
    density_g_per_ml: float
    confidence_level: str
    source: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        orm_mode = True

@router.get("/density", response_model=List[DensitySchema])
def get_ingredient_densities(db: Session = Depends(get_db)):
    return db.query(orm.IngredientDensity).all()
