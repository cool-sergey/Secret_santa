from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random
import httpx 

from database import engine, Base, get_db
from models import Event, EventParticipant, SecretSantaAssignment, EventStatus, InvitationStatus
from schemas import (
    EventCreate, EventUpdate, EventResponse, EventStatusResponse,
    InvitationCreate, InvitationResponse, InvitationRespond,
    ParticipantJoin, ParticipantResponse, GiftSentUpdate,
    AssignmentResponse
)
from auth import get_current_user_id, get_current_user_role, oauth2_scheme

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Event Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_cache = {}


def check_organizer(user_id: int, event: Event):
    if event.organizer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только организатор может выполнить это действие"
        )

def check_event_access(event_id: int, user_id: int, db: Session):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return event

async def get_user_from_service(user_id: int, token: str) -> dict:
    if user_id in user_cache:
        return user_cache[user_id]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://user-service:8000/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            if response.status_code == 200:
                user_data = response.json()
                user_cache[user_id] = user_data
                return user_data
            else:
                return {"id": user_id, "name": f"User {user_id} (deleted)"}
        except Exception:
            return {"id": user_id, "name": f"User {user_id}"}

async def get_users_batch(user_ids: List[int], token: str) -> dict:
    print(f"\n📡📡📡 get_users_batch ВЫЗВАН!")
    print(f"📡 Запрошены ID: {user_ids}")
    
    return {uid: {"name": f"User {uid}"} for uid in user_ids}

async def get_wishlist_from_service(wishlist_id: int, token: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"http://wishlists-service:8000/wishlists/{wishlist_id}/public",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return None


@app.get("/events", response_model=List[EventResponse])
def get_events(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    
    participant_event_ids = db.query(EventParticipant.event_id).filter(
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).subquery()
    
    query = db.query(Event).filter(
        (Event.organizer_id == user_id) | 
        (Event.id.in_(participant_event_ids))
    )
    
    if status_filter:
        query = query.filter(Event.status == status_filter)
    
    events = query.offset(skip).limit(limit).all()
    
    for event in events:
        event.participants_count = db.query(EventParticipant).filter(
            EventParticipant.event_id == event.id,
            EventParticipant.is_active == True
        ).count()
    
    return events

@app.post("/events", response_model=EventResponse)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role)
):
    
    if user_role not in ["organizer", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только организаторы могут создавать мероприятия"
        )
    
    event = Event(
        organizer_id=user_id,
        **event_data.dict()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

@app.post("/events/{event_id}/add-participant")
async def add_participant(
    event_id: int,
    participant_data: InvitationCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == participant_data.user_id
    ).first()
    
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Пользователь уже участвует")
        else:
            existing.is_active = True
            db.commit()
            return {"message": "Пользователь добавлен"}
    
    participant = EventParticipant(
        event_id=event_id,
        user_id=participant_data.user_id,
        is_active=True
    )
    
    db.add(participant)
    db.commit()
    
    return {"message": "Пользователь добавлен"}

@app.get("/events/my", response_model=List[EventResponse])
def get_my_events(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    participant_events = db.query(Event).join(
        EventParticipant, Event.id == EventParticipant.event_id
    ).filter(
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).all()
    
    return participant_events

@app.get("/events/organized", response_model=List[EventResponse])
def get_organized_events(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    events = db.query(Event).filter(Event.organizer_id == user_id).all()
    return events

@app.get("/events/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    event.participants_count = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.is_active == True
    ).count()
    return event

@app.patch("/events/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    event_data: EventUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    check_organizer(user_id, event)
    
    if event.status in [EventStatus.ACTIVE, EventStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя редактировать активное или завершенное мероприятие"
        )
    
    for field, value in event_data.dict(exclude_unset=True).items():
        setattr(event, field, value)
    
    db.commit()
    db.refresh(event)
    return event


@app.post("/events/{event_id}/start")
def start_event(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    check_organizer(user_id, event)
    
    if event.status != EventStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Мероприятие уже начато или завершено"
        )
    
    event.status = EventStatus.ACTIVE
    db.commit()
    
    return {"message": "Мероприятие начато", "event_id": event_id}

@app.post("/events/{event_id}/complete")
def complete_event(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    check_organizer(user_id, event)
    
    if event.status != EventStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Можно завершить только активное мероприятие"
        )
    
    event.status = EventStatus.COMPLETED
    db.commit()
    
    return {"message": "Мероприятие завершено", "event_id": event_id}

@app.post("/events/{event_id}/draw")
def draw_assignments(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    check_organizer(user_id, event)
    
    if event.draw_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Жеребьевка уже проведена"
        )
    
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.is_active == True
    ).all()
    
    if len(participants) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Для жеребьевки нужно минимум 2 участника"
        )
    
    participants_without_wishlist = [p for p in participants if not p.selected_wishlist_id]
    if participants_without_wishlist:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"У {len(participants_without_wishlist)} участников не выбран вишлист"
        )
    
    participant_ids = [p.user_id for p in participants]
    random.shuffle(participant_ids)
    
    assignments = []
    for i in range(len(participant_ids)):
        santa_id = participant_ids[i]
        recipient_id = participant_ids[(i + 1) % len(participant_ids)]
        
        recipient = next(p for p in participants if p.user_id == recipient_id)
        
        assignment = SecretSantaAssignment(
            event_id=event_id,
            santa_id=santa_id,
            recipient_id=recipient_id,
            recipient_wishlist_id=recipient.selected_wishlist_id
        )
        assignments.append(assignment)
    
    db.add_all(assignments)
    
    event.draw_completed = True
    event.draw_date = datetime.now()
    db.commit()
    
    return {
        "message": "Жеребьевка успешно проведена",
        "assignments_count": len(assignments)
    }

@app.get("/events/{event_id}/assignments", response_model=List[AssignmentResponse])
def get_assignments(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant and event.organizer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только участники могут видеть результаты жеребьевки"
        )
    
    assignments = db.query(SecretSantaAssignment).filter(
        SecretSantaAssignment.event_id == event_id
    ).all()
    
    return assignments

@app.get("/events/{event_id}/my-recipient")
def get_my_recipient(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    assignment = db.query(SecretSantaAssignment).filter(
        SecretSantaAssignment.event_id == event_id,
        SecretSantaAssignment.santa_id == user_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не участвуете в мероприятии или жеребьевка еще не проведена"
        )
    
    return {
        "santa_id": assignment.santa_id,
        "recipient_id": assignment.recipient_id
    }


@app.post("/events/{event_id}/join")
async def join_event(
    event_id: int,
    join_data: ParticipantJoin,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme)
):
    event = check_event_access(event_id, user_id, db)
    
    if event.status != EventStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя присоединиться к активному или завершенному мероприятию"
        )
    
    if datetime.now() > event.registration_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Дедлайн регистрации истек"
        )
    
    if join_data.wishlist_id:
        wishlist = await get_wishlist_from_service(join_data.wishlist_id, token)
        if not wishlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вишлист не найден"
            )    
    existing = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id
    ).first()
    
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже участвуете в этом мероприятии"
            )
        else:
            existing.is_active = True
            existing.selected_wishlist_id = join_data.wishlist_id
            db.commit()
            return {"message": "Вы успешно восстановили участие в мероприятии"}
    
    participant = EventParticipant(
        event_id=event_id,
        user_id=user_id,
        selected_wishlist_id=join_data.wishlist_id
    )
    
    db.add(participant)
    db.commit()
    
    return {"message": "Вы успешно присоединились к мероприятию"}

@app.post("/events/{event_id}/leave")
def leave_event(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    if datetime.now() > event.registration_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя покинуть мероприятие после дедлайна регистрации"
        )
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не участвуете в этом мероприятии"
        )
    
    participant.is_active = False
    db.commit()
    
    return {"message": "Вы покинули мероприятие"}

@app.post("/events/{event_id}/select-wishlist")
async def select_wishlist(
    event_id: int,
    wishlist_data: ParticipantJoin,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme)
):
    print(f"🔥 select_wishlist вызван для event_id={event_id}, user_id={user_id}, wishlist_id={wishlist_data.wishlist_id}")
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не участвуете в этом мероприятии"
        )
    
    event = check_event_access(event_id, user_id, db)
    if event.draw_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить вишлист после жеребьевки"
        )
    
    if wishlist_data.wishlist_id:
        wishlist = await get_wishlist_from_service(wishlist_data.wishlist_id, token)
        if not wishlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Вишлист не найден"
            )
    
    participant.selected_wishlist_id = wishlist_data.wishlist_id
    db.commit()
    
    return {"message": "Wishlist выбран", "wishlist_id": wishlist_data.wishlist_id}

@app.post("/events/{event_id}/gift-sent")
def mark_gift_sent(
    event_id: int,
    gift_data: GiftSentUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не участвуете в этом мероприятии"
        )
    
    participant.gift_sent = gift_data.gift_sent
    participant.gift_sent_at = datetime.now() if gift_data.gift_sent else None
    
    db.commit()
    
    return {"message": "Статус отправки подарка обновлен"}


@app.get("/events/{event_id}/status", response_model=EventStatusResponse)
def get_event_status(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    participants_count = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.is_active == True
    ).count()
    
    is_organizer = (event.organizer_id == user_id)
    is_participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first() is not None
    
    now = datetime.now()
    
    return EventStatusResponse(
        id=event.id,
        name=event.name,
        status=event.status,
        participants_count=participants_count,
        registration_deadline=event.registration_deadline,
        start_date=event.start_date,
        end_date=event.end_date,
        can_join=(
            event.status == EventStatus.CREATED and
            now <= event.registration_deadline and
            not is_participant
        ),
        can_start=(
            is_organizer and
            event.status == EventStatus.CREATED
        ),
        can_draw=(
            is_organizer and
            event.status == EventStatus.ACTIVE and
            not event.draw_completed
        ),
        can_complete=(
            is_organizer and
            event.status == EventStatus.ACTIVE
        )
    )


@app.get("/events/{event_id}/non-participants")
async def get_non_participants(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme),
    skip: int = 0,
    limit: int = 20
):
    event = check_event_access(event_id, user_id, db)
    check_organizer(user_id, event)
    
    participant_ids = db.query(EventParticipant.user_id).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.is_active == True
    ).all()
    participant_ids = [p[0] for p in participant_ids]
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://user-service:8000/users",
                headers={"Authorization": f"Bearer {token}"},
                params={"skip": skip, "limit": limit}
            )
            
            if response.status_code == 200:
                all_users = response.json()
                non_participants = [
                    u for u in all_users
                    if u["id"] not in participant_ids
                ]
                return {
                    "users": non_participants,
                    "total": len(non_participants),
                    "skip": skip,
                    "limit": limit
                }
        except Exception as e:
            print(f"Error fetching users: {e}")
    
    return {"message": "Введите ID пользователя для добавления"}

@app.get("/events/{event_id}/participants", response_model=List[ParticipantResponse])
def get_event_participants(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    is_organizer = (event.organizer_id == user_id)
    is_participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first() is not None
    
    if not is_organizer and not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только организатор и участники могут видеть список участников"
        )
    
    participants = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.is_active == True
    ).all()
    
    return participants

@app.post("/events/{event_id}/invitations", response_model=InvitationResponse)
async def invite_user(
    event_id: int,
    invitation: InvitationCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    user_role: str = Depends(get_current_user_role),
    token: str = Depends(oauth2_scheme)
):
    event = check_event_access(event_id, user_id, db)
    
    if event.organizer_id != user_id and user_role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только организатор может приглашать участников"
        )
    
    if event.status != EventStatus.CREATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя приглашать участников в активное или завершенное мероприятие"
        )
    
    user_data = await get_user_from_service(invitation.user_id, token)
    if not user_data or user_data.get("name", "").endswith("(deleted)"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    existing = db.query(EventInvitation).filter(
        EventInvitation.event_id == event_id,
        EventInvitation.user_id == invitation.user_id
    ).first()
    
    if existing:
        if existing.status == InvitationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь уже приглашен"
            )
        elif existing.status == InvitationStatus.ACCEPTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь уже участвует в мероприятии"
            )
    
    new_invitation = EventInvitation(
        event_id=event_id,
        user_id=invitation.user_id,
        invited_by=user_id,
        status=InvitationStatus.PENDING
    )
    
    db.add(new_invitation)
    db.commit()
    db.refresh(new_invitation)
    
    return new_invitation

@app.get("/events/{event_id}/invitations", response_model=List[InvitationResponse])
def get_invitations(
    event_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    event = check_event_access(event_id, user_id, db)
    
    if event.organizer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только организатор может просматривать приглашения"
        )
    
    query = db.query(EventInvitation).filter(EventInvitation.event_id == event_id)
    
    if status_filter:
        query = query.filter(EventInvitation.status == status_filter)
    
    invitations = query.all()
    
    for inv in invitations:
        inv.event_name = event.name
    
    return invitations

@app.get("/events/my-invitations", response_model=List[InvitationResponse])
def get_my_invitations(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    invitations = db.query(EventInvitation).filter(
        EventInvitation.user_id == user_id,
        EventInvitation.status == InvitationStatus.PENDING
    ).all()
    
    for inv in invitations:
        event = db.query(Event).filter(Event.id == inv.event_id).first()
        if event:
            inv.event_name = event.name
    
    return invitations

@app.post("/invitations/{invitation_id}/respond")
def respond_to_invitation(
    invitation_id: int,
    response: InvitationRespond,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    invitation = db.query(EventInvitation).filter(
        EventInvitation.id == invitation_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Приглашение не найдено"
        )
    
    if invitation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Это приглашение не для вас"
        )
    
    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="На это приглашение уже дан ответ"
        )
    
    invitation.status = response.status
    invitation.responded_at = datetime.now()
    
    if response.status == InvitationStatus.ACCEPTED:
        participant = EventParticipant(
            event_id=invitation.event_id,
            user_id=user_id,
            is_active=True
        )
        db.add(participant)
    
    db.commit()
    
    return {
        "message": f"Приглашение {response.status}",
        "invitation_id": invitation_id
    }

@app.get("/events/{event_id}/my-wishlist")
def get_my_selected_wishlist(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не участвуете в этом мероприятии"
        )
    
    return {"wishlist_id": participant.selected_wishlist_id}

@app.get("/events/{event_id}/recipient-wishlist")
async def get_recipient_wishlist(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme)
):
    assignment = db.query(SecretSantaAssignment).filter(
        SecretSantaAssignment.event_id == event_id,
        SecretSantaAssignment.santa_id == user_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Жеребьевка еще не проведена или вы не участвуете"
        )
    
    if not assignment.recipient_wishlist_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="У получателя не выбран вишлист"
        )
    
    wishlist = await get_wishlist_from_service(assignment.recipient_wishlist_id, token)
    
    if not wishlist:
        return {
            "recipient_id": assignment.recipient_id,
            "wishlist_id": assignment.recipient_wishlist_id,
            "error": "Не удалось загрузить вишлист"
        }
    
    return {
        "recipient_id": assignment.recipient_id,
        "wishlist": wishlist
    }

@app.post("/events/{event_id}/confirm-gift")
def confirm_gift_received(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    
    assignment = db.query(SecretSantaAssignment).filter(
        SecretSantaAssignment.event_id == event_id,
        SecretSantaAssignment.recipient_id == user_id
    ).first()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вы не являетесь получателем в этом мероприятии"
        )
    
    participant = db.query(EventParticipant).filter(
        EventParticipant.event_id == event_id,
        EventParticipant.user_id == user_id,
        EventParticipant.is_active == True
    ).first()
    
    if not participant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Участие не найдено"
        )
    
    participant.gift_sent_confirmation = True
    db.commit()
    
    return {"message": "Получение подарка подтверждено"}

@app.get("/events/{event_id}/participants-with-names")
async def get_participants_with_names(
    event_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme)
):
    print("\n" + "="*50)
    print(f"🔥🔥🔥 get_participants_with_names НАЧАЛО")
    print(f"event_id: {event_id}")
    print(f"user_id: {user_id}")
    print(f"token: {token[:30]}...")
    
    try:
        print("1. Проверка доступа к мероприятию...")
        event = check_event_access(event_id, user_id, db)
        print(f"✅ Мероприятие найдено: {event.name}")
        
        print("2. Получение участников из БД...")
        participants = db.query(EventParticipant).filter(
            EventParticipant.event_id == event_id,
            EventParticipant.is_active == True
        ).all()
        print(f"✅ Найдено участников: {len(participants)}")
        
        if not participants:
            print("⚠️ Нет участников, возвращаем пустой список")
            return []
        
        user_ids = [p.user_id for p in participants]
        print(f"3. ID пользователей: {user_ids}")
        
        print("4. Запрос к user-service через get_users_batch...")
        try:
            users_data = await get_users_batch(user_ids, token)
            print(f"✅ Получены данные для {len(users_data)} пользователей")
        except Exception as e:
            print(f"❌ Ошибка в get_users_batch: {e}")
            users_data = {uid: {"name": f"User {uid}"} for uid in user_ids}
        
        print("5. Формирование результата...")
        result = []
        for p in participants:
            user_info = users_data.get(p.user_id, {"name": f"User {p.user_id}"})
            result.append({
                "user_id": p.user_id,
                "name": user_info.get("name", f"User {p.user_id}"),
                "selected_wishlist_id": p.selected_wishlist_id,
                "gift_sent": p.gift_sent,
                "gift_sent_confirmation": p.gift_sent_confirmation
            })
        
        print(f"✅ Возвращаем {len(result)} записей")
        print("="*50 + "\n")
        return result
        
    except Exception as e:
        print(f"❌❌❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
