
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.database import get_db
from api.models import orm
from api import schemas
from passlib.context import CryptContext

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@router.post("/register", response_model=schemas.AuthResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(orm.User).filter(orm.User.email == user.email).first()
    if db_user:
        return {"success": False, "error": "Email already registered"}
    
    db_username = db.query(orm.User).filter(orm.User.username == user.username).first()
    if db_username:
        return {"success": False, "error": "Username already taken"}
        
    hashed_password = get_password_hash(user.password)
    new_user = orm.User(
        email=user.email,
        username=user.username,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"success": True, "user": new_user}

@router.post("/login", response_model=schemas.AuthResponse)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(orm.User).filter(orm.User.email == user_credentials.email).first()
    if not user:
        return {"success": False, "error": "Invalid email or password"}
        
    if not verify_password(user_credentials.password, user.password_hash):
        return {"success": False, "error": "Invalid email or password"}
        
    # Update last login
    # user.last_login = datetime.now() # Requires import
    # db.commit()
    
    return {"success": True, "user": user}

@router.post("/oauth-login", response_model=schemas.AuthResponse)
def oauth_login(request: schemas.OAuthLoginRequest, db: Session = Depends(get_db)):
    """
    Find or create user from Google OAuth data.
    """
    # 1. Try to find by Google ID
    user = db.query(orm.User).filter(orm.User.google_id == request.google_id).first()
    
    if user:
        # Update avatar if changed
        if request.avatar_url and user.avatar_url != request.avatar_url:
            user.avatar_url = request.avatar_url
            db.commit()
        return {"success": True, "user": user}
        
    # 2. Try to find by Email (Link account)
    user = db.query(orm.User).filter(orm.User.email == request.email).first()
    
    if user:
        # Link existing account to Google
        user.google_id = request.google_id
        if request.avatar_url:
            user.avatar_url = request.avatar_url
        db.commit()
        db.refresh(user)
        return {"success": True, "user": user}
        
    # 3. Create New User
    # Generate a random password since they use Google
    import secrets
    random_password = secrets.token_urlsafe(16) 
    hashed_password = get_password_hash(random_password)
    
    # Use provided name or split email
    username = request.name if request.name else request.email.split("@")[0]
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while db.query(orm.User).filter(orm.User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1
        
    new_user = orm.User(
        email=request.email,
        username=username,
        password_hash=hashed_password,
        google_id=request.google_id,
        avatar_url=request.avatar_url,
        role='user'
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"success": True, "user": new_user}
