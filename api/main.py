"""
Meal Planner FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import routers (will be created in Module 2+)
# from routers import recipes, plans, catalogs

# Database connection (will be configured in Module 2)
# from database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown"""
    # Startup
    print("Starting Meal Planner API...")
    # Create database tables (uncomment when database.py is ready)
    # Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
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
async def get_stats():
    """
    Get dashboard statistics
    TODO: Replace with actual database queries in Module 2
    """
    return {
        "recipe_count": 0,
        "catalog_count": 0,
        "plan_count": 0,
        "user_count": 0,
        "recent_plans": [],
    }


# ============================================
# Include Routers (uncomment as modules are completed)
# ============================================
# app.include_router(catalogs.router, prefix="/api/catalogs", tags=["Catalogs"])
# app.include_router(recipes.router, prefix="/api/recipes", tags=["Recipes"])
# app.include_router(plans.router, prefix="/api/plans", tags=["Plans"])


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
