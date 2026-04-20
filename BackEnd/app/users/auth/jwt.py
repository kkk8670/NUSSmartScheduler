import os
from datetime import datetime, timedelta, timezone
import jwt  # 1. 导入名从 jose 改为 jwt


# —— 从 core.config 读取更理想
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> tuple[str, int]:
    expire_minutes = int(expires_delta.total_seconds() // 60) if expires_delta else ACCESS_TOKEN_EXPIRE_MINUTES
    # PyJWT 处理带时区的 datetime 非常完美
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    
    to_encode = {"sub": str(subject), "exp": expire}
    # 2. PyJWT 的 encode 方法
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, expire_minutes

def decode_token(token: str) -> dict:
    # 3. PyJWT 的 decode 方法（参数名一致，但内部逻辑更现代）
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
    # 4. 捕获 PyJWT 的异常
    except jwt.PyJWTError as e:
        raise JWTAuthError(str(e))