from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer

SECRET_KEY = "test-secret-key-for-development-only"
ALGORITHM = "HS256"

security = HTTPBearer()
oauth2_scheme = security  
blacklisted_tokens: Dict[str, datetime] = {}

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )

def get_current_user_id(token: str = Depends(security)) -> int:
    if token.credentials in blacklisted_tokens:
        if datetime.now() > blacklisted_tokens[token.credentials]:
            del blacklisted_tokens[token.credentials]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен недействителен (выполнен logout)"
            )
    
    payload = verify_token(token.credentials)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID пользователя не найден в токене"
        )
    
    return int(user_id)

def get_current_user_role(token: str = Depends(security)) -> str:
    payload = verify_token(token.credentials)
    role = payload.get("role", "user") 
    return role

def is_token_blacklisted(token: str) -> bool:
    if token in blacklisted_tokens:
        if datetime.now() > blacklisted_tokens[token]:
            del blacklisted_tokens[token]
            return False
        return True
    return False
