"""
Authentication API router
Handles user registration, login, and session management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, EmailStr
from typing import Optional
import hashlib
import secrets
from datetime import datetime, timedelta

from database import get_db

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: Optional[str] = None


# ============================================
# Password Hashing (compatible with PHP password_hash)
# ============================================

def hash_password(password: str) -> str:
    """
    Hash password using SHA-256 with salt.
    Note: For production, use bcrypt via passlib.
    This simplified version is for MVP compatibility.
    """
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored hash."""
    try:
        salt, hashed = stored_hash.split(":")
        check_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return check_hash == hashed
    except ValueError:
        return False


# ============================================
# Endpoints
# ============================================

@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user"""

    # Check if email already exists
    result = db.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": request.email}
    )
    if result.first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if username already exists
    result = db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": request.username}
    )
    if result.first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Validate password length
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Hash password and create user
    password_hash = hash_password(request.password)

    result = db.execute(
        text("""
            INSERT INTO users (username, email, password_hash)
            VALUES (:username, :email, :password_hash)
        """),
        {
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
        }
    )
    user_id = result.lastrowid
    db.commit()

    return {
        "success": True,
        "message": "Registration successful",
        "user": {
            "id": user_id,
            "username": request.username,
            "email": request.email,
        }
    }


@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return user data"""

    # Find user by email
    result = db.execute(
        text("""
            SELECT id, username, email, password_hash, created_at
            FROM users WHERE email = :email
        """),
        {"email": request.email}
    )
    user = result.mappings().first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last login
    db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :id"),
        {"id": user["id"]}
    )
    db.commit()

    return {
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        }
    }


@router.get("/user/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user details by ID"""

    result = db.execute(
        text("""
            SELECT id, username, email, created_at, last_login
            FROM users WHERE id = :id
        """),
        {"id": user_id}
    )
    user = result.mappings().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"].isoformat() if user["created_at"] else None,
        "last_login": user["last_login"].isoformat() if user["last_login"] else None,
    }


@router.put("/user/{user_id}")
async def update_user(
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update user profile"""

    # Check if user exists
    result = db.execute(
        text("SELECT id FROM users WHERE id = :id"),
        {"id": user_id}
    )
    if not result.first():
        raise HTTPException(status_code=404, detail="User not found")

    updates = []
    params = {"id": user_id}

    if username:
        # Check if username is taken
        result = db.execute(
            text("SELECT id FROM users WHERE username = :username AND id != :id"),
            {"username": username, "id": user_id}
        )
        if result.first():
            raise HTTPException(status_code=400, detail="Username already taken")
        updates.append("username = :username")
        params["username"] = username

    if email:
        # Check if email is taken
        result = db.execute(
            text("SELECT id FROM users WHERE email = :email AND id != :id"),
            {"email": email, "id": user_id}
        )
        if result.first():
            raise HTTPException(status_code=400, detail="Email already registered")
        updates.append("email = :email")
        params["email"] = email

    if updates:
        db.execute(
            text(f"UPDATE users SET {', '.join(updates)} WHERE id = :id"),
            params
        )
        db.commit()

    return {"success": True, "message": "Profile updated"}
