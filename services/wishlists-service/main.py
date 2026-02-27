from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from database import engine, Base, get_db
from models import Wishlist, WishlistItem
from schemas import (
    WishlistCreate, WishlistUpdate, WishlistResponse,
    WishlistItemCreate, WishlistItemResponse
)
from auth import get_current_user_id

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Wishlist Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/wishlists", response_model=WishlistResponse)
def create_wishlist(
    wishlist_data: WishlistCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):    
    if wishlist_data.is_primary:
        db.query(Wishlist).filter(
            Wishlist.user_id == user_id,
            Wishlist.is_primary == True
        ).update({"is_primary": False})
    
    wishlist = Wishlist(
        user_id=user_id,
        **wishlist_data.dict()
    )
    db.add(wishlist)
    db.commit()
    db.refresh(wishlist)
    return wishlist

@app.get("/wishlists", response_model=List[WishlistResponse])
def get_my_wishlists(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlists = db.query(Wishlist).filter(Wishlist.user_id == user_id).all()
    return wishlists

@app.get("/wishlists/{wishlist_id}", response_model=WishlistResponse)
def get_wishlist(
    wishlist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not wishlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wishlist не найден"
        )
    return wishlist

@app.patch("/wishlists/{wishlist_id}", response_model=WishlistResponse)
def update_wishlist(
    wishlist_id: int,
    wishlist_data: WishlistUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist не найден")
    
    if wishlist_data.is_primary:
        db.query(Wishlist).filter(
            Wishlist.user_id == user_id,
            Wishlist.id != wishlist_id,
            Wishlist.is_primary == True
        ).update({"is_primary": False})
    
    for field, value in wishlist_data.dict(exclude_unset=True).items():
        setattr(wishlist, field, value)
    
    db.commit()
    db.refresh(wishlist)
    return wishlist

@app.get("/wishlists/{wishlist_id}/public")
def get_wishlist_public(
    wishlist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(Wishlist.id == wishlist_id).first()
    
    if not wishlist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вишлист не найден"
        )    
    return {
        "id": wishlist.id,
        "name": wishlist.name,
        "description": wishlist.description,
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "link": item.link,
                "price": item.price
            } for item in wishlist.items
        ]
    }


@app.delete("/wishlists/{wishlist_id}")
def delete_wishlist(
    wishlist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist не найден")
    
    db.delete(wishlist)
    db.commit()
    
    return {"message": "Wishlist удален"}

@app.post("/wishlists/{wishlist_id}/items", response_model=WishlistItemResponse)
def create_item(
    wishlist_id: int,
    item_data: WishlistItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist не найден")
    
    item = WishlistItem(
        wishlist_id=wishlist_id,
        **item_data.dict()
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.patch("/wishlists/items/{item_id}", response_model=WishlistItemResponse)
def update_item(
    item_id: int,
    item_data: WishlistItemCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    item = db.query(WishlistItem).join(Wishlist).filter(
        WishlistItem.id == item_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item не найден")
    
    for field, value in item_data.dict().items():
        setattr(item, field, value)
    
    db.commit()
    db.refresh(item)
    return item

@app.delete("/wishlists/items/{item_id}")
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    item = db.query(WishlistItem).join(Wishlist).filter(
        WishlistItem.id == item_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item не найден")
    
    db.delete(item)
    db.commit()
    
    return {"message": "Item удален"}

@app.post("/wishlists/{wishlist_id}/set-primary")
def set_primary_wishlist(
    wishlist_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.id == wishlist_id,
        Wishlist.user_id == user_id
    ).first()
    
    if not wishlist:
        raise HTTPException(status_code=404, detail="Wishlist не найден")
    
    db.query(Wishlist).filter(
        Wishlist.user_id == user_id,
        Wishlist.is_primary == True
    ).update({"is_primary": False})
    
    wishlist.is_primary = True
    db.commit()
    
    return {"message": "Основной wishlist установлен"}

@app.get("/wishlists/primary", response_model=WishlistResponse)
def get_primary_wishlist(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    wishlist = db.query(Wishlist).filter(
        Wishlist.user_id == user_id,
        Wishlist.is_primary == True
    ).first()
    
    if not wishlist:
        raise HTTPException(status_code=404, detail="Основной wishlist не найден")
    
    return wishlist
