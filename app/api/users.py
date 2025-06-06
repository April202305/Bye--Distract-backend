from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.models import User
from app.schemas.login_schemas import UserCreate, UserLogin, UserResponse
from app.services.auth import get_password_hash, verify_password
from datetime import datetime

router = APIRouter()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        user_name=user.user_name,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # Verify user
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Update last login time
    db_user.last_login = datetime.utcnow()
    db.commit()
    
    return {"user_id": db_user.user_id, "user_name": db_user.user_name, "study_room_id":db_user.study_room_id} 