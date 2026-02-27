from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text
from sqlalchemy.sql import func
from database import Base
import enum

class UserRole(str, enum.Enum):
    SUPERADMIN = "superadmin"
    ORGANIZER = "organizer"
    USER = "user"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    avatar_url = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    temp_phone = Column(String, nullable=True)
    temp_phone_code = Column(String, nullable=True)
    temp_phone_expires = Column(DateTime, nullable=True)
    
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User {self.phone} ({self.role.value})>"
