from typing import Optional
from pydantic import BaseModel, EmailStr

# —— 输入输出模型（Pydantic）

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True

# —— 认证相关
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class LoginIn(BaseModel):
    email: EmailStr
    password: str
