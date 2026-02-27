from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class EventStatusEnum(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class InvitationStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class EventBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: bool = True
    start_date: datetime
    end_date: datetime
    registration_deadline: datetime
    min_gift_amount: Optional[float] = Field(None, gt=0)
    max_gift_amount: Optional[float] = Field(None, gt=0)
    
    @validator('end_date')
    def end_date_after_start(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('Дата окончания должна быть позже даты начала')
        return v
    
    @validator('registration_deadline')
    def deadline_before_start(cls, v, values):
        if 'start_date' in values and v >= values['start_date']:
            raise ValueError('Дедлайн регистрации должен быть до начала мероприятия')
        return v

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_private: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None
    min_gift_amount: Optional[float] = Field(None, gt=0)
    max_gift_amount: Optional[float] = Field(None, gt=0)
    status: Optional[EventStatusEnum] = None

class EventResponse(EventBase):
    id: int
    organizer_id: int
    status: EventStatusEnum
    draw_completed: bool
    draw_date: Optional[datetime] = None
    created_at: datetime
    participants_count: int = 0
    invitations_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class EventStatusResponse(BaseModel):
    id: int
    name: str
    status: EventStatusEnum
    participants_count: int
    registration_deadline: datetime
    start_date: datetime
    end_date: datetime
    can_join: bool
    can_start: bool
    can_draw: bool
    can_complete: bool
    
    model_config = ConfigDict(from_attributes=True)


class InvitationCreate(BaseModel):
    user_id: int

class InvitationResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    invited_by: int
    status: InvitationStatusEnum
    invited_at: datetime
    responded_at: Optional[datetime] = None
    event_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class InvitationRespond(BaseModel):
    status: InvitationStatusEnum


class ParticipantJoin(BaseModel):
    wishlist_id: Optional[int] = None

class ParticipantResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    joined_at: datetime
    is_active: bool
    selected_wishlist_id: Optional[int] = None
    gift_sent: bool
    gift_sent_confirmation: bool
    
    model_config = ConfigDict(from_attributes=True)

class GiftSentUpdate(BaseModel):
    gift_sent: bool = True


class AssignmentResponse(BaseModel):
    id: int
    event_id: int
    santa_id: int
    recipient_id: int
    recipient_wishlist_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
