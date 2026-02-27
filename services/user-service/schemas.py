from pydantic import BaseModel, Field, validator, ConfigDict, EmailStr
from typing import Optional
import re
from enum import Enum
from datetime import datetime

class UserRoleEnum(str, Enum):
    SUPERADMIN = "superadmin"
    ORGANIZER = "organizer"
    USER = "user"

class UserRegister(BaseModel):
    phone: str
    password: str = Field(..., min_length=4)
    confirm_password: str
    
    @validator('phone')
    def validate_phone(cls, v):
        phone = re.sub(r'\D', '', v)
        if len(phone) < 10:
            raise ValueError('Телефон должен содержать минимум 10 цифр')
        return f"+{phone}"

class VerifyCode(BaseModel):
    phone: str
    code: str = Field(..., min_length=6, max_length=6)

class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            v = v.strip()
            if v and len(v) < 2:
                raise ValueError('Имя слишком короткое')
        return v

class ChangePhoneRequest(BaseModel):
    new_phone: str
    
    @validator('new_phone')
    def validate_phone(cls, v):
        phone = re.sub(r'\D', '', v)
        if len(phone) < 10:
            raise ValueError('Телефон должен содержать минимум 10 цифр')
        return f"+{phone}"

class ChangePhoneVerify(BaseModel):
    new_phone: str
    code: str = Field(..., min_length=6, max_length=6)

class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=4)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Новые пароли не совпадают')
        return v

class UserProfileResponse(BaseModel):
    id: int
    phone: str
    name: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRoleEnum
    is_verified: bool
    created_at: datetime 
    
    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    phone: str
    role: UserRoleEnum
    is_verified: bool
    
    model_config = ConfigDict(from_attributes=True)
