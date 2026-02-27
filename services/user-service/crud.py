from sqlalchemy.orm import Session
from models import User

def get_user_by_phone(db: Session, phone: str):
    return db.query(User).filter(User.phone == phone).first()

def get_user(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, phone: str, hashed_password: str):
    db_user = User(
        phone=phone,
        hashed_password=hashed_password,
        is_verified=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
