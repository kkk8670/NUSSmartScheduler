import bcrypt

def get_password_hash(password: str) -> str:
    # input type: bytes
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:

    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    # check by bcrypt - checkpw  
    return bcrypt.checkpw(password_bytes, hashed_bytes)