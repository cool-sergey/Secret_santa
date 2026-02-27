from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum
from datetime import datetime

class EventStatus(str, enum.Enum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class InvitationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    organizer_id = Column(Integer, index=True, nullable=False)
    
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    is_private = Column(Boolean, default=True) 
    
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    registration_deadline = Column(DateTime, nullable=False)
    
    min_gift_amount = Column(Float, nullable=True)
    max_gift_amount = Column(Float, nullable=True)
    
    status = Column(Enum(EventStatus), default=EventStatus.CREATED)
    
    draw_completed = Column(Boolean, default=False)
    draw_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    participants = relationship("EventParticipant", back_populates="event", cascade="all, delete-orphan")
    invitations = relationship("EventInvitation", back_populates="event", cascade="all, delete-orphan")
    assignments = relationship("SecretSantaAssignment", back_populates="event", cascade="all, delete-orphan")

class EventInvitation(Base):
    __tablename__ = "event_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    user_id = Column(Integer, index=True, nullable=False)
    invited_by = Column(Integer, nullable=False)
    
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime, nullable=True)
    
    event = relationship("Event", back_populates="invitations")

class EventParticipant(Base):
    __tablename__ = "event_participants"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    user_id = Column(Integer, index=True, nullable=False)
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    selected_wishlist_id = Column(Integer, nullable=True)
    
    gift_sent = Column(Boolean, default=False)
    gift_sent_at = Column(DateTime, nullable=True)
    gift_sent_confirmation = Column(Boolean, default=False)
    
    event = relationship("Event", back_populates="participants")

class SecretSantaAssignment(Base):
    __tablename__ = "secret_santa_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"))
    
    santa_id = Column(Integer, nullable=False)
    recipient_id = Column(Integer, nullable=False)
    recipient_wishlist_id = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    event = relationship("Event", back_populates="assignments")
