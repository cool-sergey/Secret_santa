from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
import shutil
import uuid
from typing import List


from database import engine, Base, get_db
from models import User, UserRole
from schemas import (
    UserRegister, VerifyCode, UserProfileUpdate, 
    ChangePhoneRequest, ChangePhoneVerify, ChangePassword,
    UserProfileResponse
)
from auth import (
    get_current_user, verify_password, get_password_hash,
    logout_user, create_access_token, oauth2_scheme
)
from sms_service import SMSService
from create_superadmin import create_superadmin

sms_service = SMSService()

Base.metadata.create_all(bind=engine)

os.makedirs("uploads/avatars", exist_ok=True)

app = FastAPI(title="User Profile API")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

temp_storage: Dict[str, dict] = {}

@app.on_event("startup")
def startup_event():
    create_superadmin()
    print("🚀 Приложение запущено")


@app.post("/register")
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):    
    existing_user = db.query(User).filter(User.phone == user_data.phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Телефон уже зарегистрирован"
        )
    
    code = sms_service.send_code(user_data.phone)    
    hashed_password = get_password_hash(user_data.password)    
    temp_storage[user_data.phone] = {
        "hashed_password": hashed_password,
        "code": code,
        "created_at": datetime.now()
    }
    
    return {
        "message": "Код подтверждения отправлен",
        "phone": user_data.phone
    }

@app.post("/verify")
async def verify(
    verify_data: VerifyCode,
    db: Session = Depends(get_db)
):    
    if verify_data.phone not in temp_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессия истекла. Начните регистрацию заново."
        )
    
    temp_data = temp_storage[verify_data.phone]
    
    time_diff = datetime.now() - temp_data["created_at"]
    if time_diff > timedelta(minutes=5):
        del temp_storage[verify_data.phone]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код истек. Запросите новый."
        )    
    if verify_data.code != temp_data["code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код"
        )
    
    new_user = User(
        phone=verify_data.phone,
        hashed_password=temp_data["hashed_password"],
        role=UserRole.USER,
        is_verified=True,
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    del temp_storage[verify_data.phone]    
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "message": "Регистрация успешна",
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserProfileResponse.from_orm(new_user)
    }

@app.post("/resend")
async def resend_code(phone: str):    
    if phone not in temp_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессия не найдена"
        )
    
    new_code = sms_service.send_code(phone)
    temp_storage[phone]["code"] = new_code
    temp_storage[phone]["created_at"] = datetime.now()
    
    return {"message": "Код отправлен повторно"}

@app.post("/login")
async def login(
    phone: str,
    password: str,
    db: Session = Depends(get_db)
):    
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный телефон или пароль"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь заблокирован"
        )    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=30)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_role": user.role
    }

@app.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme)
):
    return await logout_user(token)

@app.get("/profile/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
@app.patch("/profile/me", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if profile_data.name is not None:
        current_user.name = profile_data.name
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio
    if profile_data.email is not None:
        current_user.email = profile_data.email
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.post("/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно загружать только изображения"
        )
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой (макс 5MB)"
        )
    
    file_extension = os.path.splitext(file.filename)[1]
    file_name = f"{uuid.uuid4()}{file_extension}"
    file_path = f"uploads/avatars/{file_name}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    avatar_url = f"/uploads/avatars/{file_name}"    
    if current_user.avatar_url:
        old_file = current_user.avatar_url.lstrip("/")
        if os.path.exists(old_file):
            os.remove(old_file)    
    current_user.avatar_url = avatar_url
    db.commit()
    
    return {
        "message": "Аватарка успешно загружена",
        "avatar_url": avatar_url
    }

@app.delete("/profile/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if current_user.avatar_url:
        file_path = current_user.avatar_url.lstrip("/")
        if os.path.exists(file_path):
            os.remove(file_path)
        current_user.avatar_url = None
        db.commit()
    
    return {"message": "Аватарка удалена"}

@app.post("/profile/change-phone/request")
async def request_phone_change(
    request: ChangePhoneRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    existing_user = db.query(User).filter(User.phone == request.new_phone).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот номер телефона уже используется"
        )    
    code = sms_service.send_code(request.new_phone)    
    temp_storage[f"change:{current_user.phone}"] = {
        "new_phone": request.new_phone,
        "code": code,
        "created_at": datetime.now()
    }
    
    return {
        "message": "Код подтверждения отправлен на новый номер"
    }

@app.post("/profile/change-phone/verify")
async def verify_phone_change(
    verify_data: ChangePhoneVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    key = f"change:{current_user.phone}"
    if key not in temp_storage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Сессия смены телефона не найдена"
        )
    
    temp_data = temp_storage[key]    
    if verify_data.code != temp_data["code"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код"
        )    
    if datetime.now() - temp_data["created_at"] > timedelta(minutes=5):
        del temp_storage[key]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код истек"
        )    
    current_user.phone = temp_data["new_phone"]
    db.commit()    
    del temp_storage[key]
    
    return {
        "message": "Номер телефона успешно изменен",
        "new_phone": current_user.phone
    }

@app.post("/profile/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):    
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль"
        )    
    if verify_password(password_data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль должен отличаться от текущего"
        )    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    
    return {"message": "Пароль успешно изменен"}

@app.get("/admin/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):    
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    users = db.query(User).offset(skip).limit(limit).all()
    return [UserProfileResponse.from_orm(user) for user in users]

@app.post("/admin/users/{user_id}/make-organizer")
async def make_organizer(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):    
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    user.role = UserRole.ORGANIZER
    db.commit()
    
    return {"message": f"Пользователь {user.phone} назначен организатором"}

@app.get("/users/{user_id}")
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )    
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url
    }

@app.get("/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "name": user.name or f"User {user.id}",
            "email": user.email,
            "phone": user.phone,
            "avatar_url": user.avatar_url
        }
        for user in users
    ]

@app.post("/users/batch")
async def get_users_batch(
    user_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"🔥 get_users_batch вызван с {len(user_ids)} ID")
    print(f"🔥 Текущий пользователь: {current_user.id} - {current_user.name}")
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    print(f"🔥 Найдено {len(users)} пользователей в БД")
    
    user_dict = {user.id: user for user in users}
    
    result = []
    for uid in user_ids:
        if uid in user_dict:
            user = user_dict[uid]
            result.append({
                "id": user.id,
                "name": user.name or f"User {user.id}",
                "email": user.email,
                "phone": user.phone,
                "avatar_url": user.avatar_url
            })
        else:
            result.append({
                "id": uid,
                "name": f"User {uid} (deleted)",
                "email": None,
                "phone": None,
                "avatar_url": None
            })
    
    print(f"🔥 Возвращаем {len(result)} записей")
    return result

@app.get("/users/search")
async def search_users(
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(User)
    
    if query:
        q = q.filter(
            (User.name.contains(query)) | 
            (User.phone.contains(query))
        )
    
    users = q.offset(skip).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "name": user.name or f"User {user.id}",
            "phone": user.phone,
            "email": user.email,
            "avatar_url": user.avatar_url
        }
        for user in users
    ]
