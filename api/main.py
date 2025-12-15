"""
Meal Planner FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db
from routers import catalogs, recipes

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    print("Starting Meal Planner API...")
    yield
    print("Shutting down Meal Planner API...")


# Create FastAPI application
app = FastAPI(
    title="Meal Planner API",
    description="Backend API for the Meal Planner web application",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for PHP frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Health Check Endpoint
# ============================================
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and connectivity testing"""
    return {"status": "ok", "service": "meal-planner-api"}


# ============================================
# Stats Endpoint (Dashboard)
# ============================================
@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        # Get counts
        recipe_count = db.execute(text("SELECT COUNT(*) FROM recipes")).scalar() or 0
        catalog_count = db.execute(text("SELECT COUNT(*) FROM catalogs")).scalar() or 0
        plan_count = db.execute(text("SELECT COUNT(*) FROM meal_plans")).scalar() or 0
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0

        # Get recent plans
        recent_result = db.execute(text("""
            SELECT mp.id, mp.name, mp.meal_types, mp.recipe_count, mp.created_at,
                   COUNT(mpr.id) as actual_recipe_count
            FROM meal_plans mp
            LEFT JOIN meal_plan_recipes mpr ON mp.id = mpr.plan_id
            GROUP BY mp.id
            ORDER BY mp.created_at DESC
            LIMIT 5
        """))

        recent_plans = []
        for row in recent_result.mappings():
            recent_plans.append({
                "id": row["id"],
                "name": row["name"] or "Unnamed Plan",
                "recipe_count": row["actual_recipe_count"] or row["recipe_count"] or 0,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            })

        return {
            "recipe_count": recipe_count,
            "catalog_count": catalog_count,
            "plan_count": plan_count,
            "user_count": user_count,
            "recent_plans": recent_plans,
        }
    except Exception as e:
        # If database isn't set up yet, return zeros
        return {
            "recipe_count": 0,
            "catalog_count": 0,
            "plan_count": 0,
            "user_count": 0,
            "recent_plans": [],
            "error": str(e),
        }


# ============================================
# Include Routers
# ============================================
app.include_router(catalogs.router, prefix="/api/catalogs", tags=["Catalogs"])
app.include_router(recipes.router, prefix="/api/recipes", tags=["Recipes"])
# app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])  # Module 4


# ============================================
# Root Endpoint
# ============================================
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Meal Planner API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
