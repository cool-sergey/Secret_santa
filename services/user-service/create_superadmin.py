from database import SessionLocal, engine, Base
from models import User, UserRole
from auth import get_password_hash
import os

def create_superadmin():    
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        superadmin = db.query(User).filter(User.role == UserRole.SUPERADMIN).first()
        
        if superadmin:
            print("✅ Суперадмин уже существует:")
            print(f"   ID: {superadmin.id}")
            print(f"   Телефон: {superadmin.phone}")
            return superadmin
        
        admin_phone = "+79991112233"
        admin_password = "admin123456"
        
        hashed_password = get_password_hash(admin_password)
        
        superadmin = User(
            phone=admin_phone,
            hashed_password=hashed_password,
            role=UserRole.SUPERADMIN,
            is_verified=True,
            is_active=True,
            name="Super Admin"
        )
        
        db.add(superadmin)
        db.commit()
        db.refresh(superadmin)
        
        print("\n" + "="*50)
        print("✅ СУПЕРАДМИН СОЗДАН!")
        print("="*50)
        print(f"   ID: {superadmin.id}")
        print(f"   Телефон: {admin_phone}")
        print(f"   Пароль: {admin_password}")
        print("="*50 + "\n")
        
        return superadmin
        
    except Exception as e:
        print(f"❌ Ошибка при создании суперадмина: {e}")
        db.rollback()
        return None
        
    finally:
        db.close()
