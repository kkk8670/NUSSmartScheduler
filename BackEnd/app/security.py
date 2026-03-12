# security.py
import logging
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt
from pydantic import BaseModel

SECRET_KEY = "CHANGE_ME"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class TokenData(BaseModel):
    sub: str
    email: str | None = None
    exp: int | None = None

def create_access_token(sub: str, email: str | None = None, minutes: int = 60*24):
    payload = {"sub": sub, "email": email, "exp": datetime.utcnow() + timedelta(minutes=minutes)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    try:
        # 打点：方便你在控制台看到传入的 token（生产环境删掉）
        logging.info(f"[auth] got bearer token (first 20): {token[:20]}...")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except jwt.InvalidSignatureError:
        raise HTTPException(status_code=401, detail="invalid_signature_check_secret")
    except jwt.DecodeError:
        raise HTTPException(status_code=401, detail="decode_error_bad_token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"auth_error: {type(e).__name__}")
