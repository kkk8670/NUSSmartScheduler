from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, UniqueConstraint
from sqlalchemy.orm import validates
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @validates("email")
    def validate_email(self, key, value: str):
        assert value and "@" in value, "invalid email"
        return value
