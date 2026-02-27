from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt

from database import get_db, SessionLocal
from models import User

SECRET_KEY = "test-secret-key-for-development-only"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def get_password_hash(password: str) -> str:
    if isinstance(password, (int, float)):
        password = str(password)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if isinstance(plain_password, (int, float)):
        plain_password = str(plain_password)
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    user_id = data.get("sub")
    if user_id:
        db = SessionLocal()
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user:
            to_encode["role"] = user.role.value 
        db.close()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):    
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен (выполнен logout)"
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные"
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user


blacklisted_tokens: Dict[str, datetime] = {}

async def logout_user(token: str = Depends(oauth2_scheme)):
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        
        if exp:
            blacklisted_tokens[token] = datetime.fromtimestamp(exp)
        
        return {"message": "Успешный выход из системы"}
    except Exception as e:
        print(f"Ошибка при logout: {e}")
        return {"message": "Выход выполнен"}

def is_token_blacklisted(token: str) -> bool:
    if token in blacklisted_tokens:
        if datetime.now() > blacklisted_tokens[token]:
            del blacklisted_tokens[token]
            return False
        return True
    return False
