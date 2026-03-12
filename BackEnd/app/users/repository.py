from typing import Optional
from sqlalchemy.orm import Session
from app.users.models import User

class UserRepository:
    @staticmethod
    def get(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def create(db: Session, *, email: str, hashed_password: str, full_name: str | None = None) -> User:
        obj = User(email=email, hashed_password=hashed_password, full_name=full_name)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def update(db: Session, user: User, *, full_name: str | None = None,
               hashed_password: str | None = None, is_active: bool | None = None) -> User:
        if full_name is not None:
            user.full_name = full_name
        if hashed_password is not None:
            user.hashed_password = hashed_password
        if is_active is not None:
            user.is_active = is_active
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
