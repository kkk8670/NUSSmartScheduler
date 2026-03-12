from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.users.service import UserService
from app.users.schemas import Token
from app.users.auth.jwt import create_access_token

router = APIRouter()

@router.post("/login", response_model=Token, summary="账号密码登录换取JWT")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm 只有 username 字段，这里我们用作 email
    user = UserService.authenticate(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect email or password")
    token, exp = create_access_token(user.id, expires_delta=timedelta(minutes=60))
    return Token(access_token=token, expires_in=exp)

# 可选：邮箱+密码注册（也可放到 users/router.py）
from app.users.schemas import UserCreate, UserOut
@router.post("/register", response_model=UserOut, summary="注册用户（简单版）")
def register_user(data: UserCreate, db: Session = Depends(get_db)):
    return UserService.register(db, data)
