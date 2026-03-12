from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.users.repository import UserRepository
from app.users.auth.jwt import get_subject, JWTAuthError

# 与 /auth/login 的 tokenUrl 保持一致
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme),
                     db: Session = Depends(get_db)):
    try:
        sub = get_subject(token)
        user = UserRepository.get(db, int(sub))
    except (ValueError, JWTAuthError):
        user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Inactive user")
    return user
