
import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from the same directory as this file
env_path = Path(__file__).parent / ".env"
success = load_dotenv(env_path, override=True)

print(f"DEBUG: Loaded env from {env_path} Result: {success}")
print(f"DEBUG: DATABASE_URL in env: {os.environ.get('DATABASE_URL')}")
print(f"DEBUG: All Env Keys: {[k for k in os.environ.keys() if 'DB' in k or 'DATA' in k]}")

from api.routers import catalogs, recipes, plans, auth

app = FastAPI(
    title="Meal Planner API",
    description="Backend API for Meal Planner application",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def verify_internal_secret(request: fastapi.Request, call_next):
    # Public endpoints
    if request.url.path in ["/", "/docs", "/redoc", "/openapi.json", "/health"]:
        return await call_next(request)
        
    expected_secret = os.getenv("INTERNAL_API_KEY")
    if expected_secret:
        token = request.headers.get("X-Internal-Secret")
        if token != expected_secret:
            return fastapi.responses.JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Missing or invalid Internal API Key"}
            )
            
    return await call_next(request)

app.include_router(catalogs.router)
app.include_router(recipes.router)
app.include_router(plans.router)
app.include_router(auth.router)

@app.get("/")
async def root():
    return {"message": "Meal Planner API is running", "status": "ok"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
