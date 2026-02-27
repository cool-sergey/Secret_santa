from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class WishlistItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    link: Optional[str] = None
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[float] = Field(None, gt=0)

class WishlistItemCreate(WishlistItemBase):
    pass

class WishlistItemResponse(WishlistItemBase):
    id: int
    wishlist_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class WishlistBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_primary: bool = False

class WishlistCreate(WishlistBase):
    pass

class WishlistUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    is_primary: Optional[bool] = None

class WishlistResponse(WishlistBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[WishlistItemResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
