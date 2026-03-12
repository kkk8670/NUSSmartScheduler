from sqlalchemy.orm import Session
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate
from app.users.auth.password import get_password_hash, verify_password
from fastapi import HTTPException, status

class UserService:
    @staticmethod
    def register(db: Session, data: UserCreate):
        if UserRepository.get_by_email(db, data.email):
            raise HTTPException(status_code=400, detail="Email already registered")
        hashed = get_password_hash(data.password)
        return UserRepository.create(db, email=data.email, hashed_password=hashed, full_name=data.full_name)

    @staticmethod
    def authenticate(db: Session, email: str, password: str):
        user = UserRepository.get_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
        return user

    @staticmethod
    def update(db: Session, user_id: int, data: UserUpdate):
        user = UserRepository.get(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        hashed = get_password_hash(data.password) if data.password else None
        return UserRepository.update(db, user,
                                     full_name=data.full_name,
                                     hashed_password=hashed,
                                     is_active=data.is_active)
