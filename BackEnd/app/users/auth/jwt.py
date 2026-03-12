import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# —— 从 core.config 读取更理想；这里提供环境变量回退
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> tuple[str, int]:
    expire_minutes = int(expires_delta.total_seconds() // 60) if expires_delta else ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode = {"sub": str(subject), "exp": expire}
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire_minutes

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

class JWTAuthError(Exception):
    pass

def get_subject(token: str) -> str:
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise JWTAuthError("Token missing subject")
        return str(sub)
    except JWTError as e:
        raise JWTAuthError(str(e))
