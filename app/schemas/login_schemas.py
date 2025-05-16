from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserCreate(BaseModel):
    user_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    user_name: str
    user_id: int
    email: str
    created_at: datetime

    class Config:
        from_attributes = True  # 修正拼写错误