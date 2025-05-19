from app.models.models import Task
from app.models.models import User
from app.models.models import StudyRoom
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.users import get_db
from app.schemas.study_room import StudyRoomCreate,RoomResponse,StudyRoomJoin,StudyRoomLeave
from sqlalchemy import text
from sqlalchemy import func
from datetime import date
from app.models.models import User, StudyRoom, DailyStatistics
from fastapi import status

router = APIRouter(prefix="/study_room", tags=["study_room"])

def validate_user_exists(db: Session, user_id: int):
    """Validate if user exists"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/add", response_model=RoomResponse)
async def create_task(
    room_data: StudyRoomCreate,
    db: Session = Depends(get_db)
):
    # Validate user exists
    validate_user_exists(db, room_data.user_id)
    # Check if user has already joined another study room
    target_user = db.query(User).filter(
        User.user_id == room_data.user_id
    ).first()
    if target_user.study_room_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has already joined another study room, please leave first before creating a new room"
        )
    # Create study room
    new_study_room = StudyRoom(
        creator_id=room_data.user_id,
        room_name=room_data.room_name,
        room_description=room_data.room_description,
        members_list=[room_data.user_id]
    )
    
    db.add(new_study_room)
    db.commit()
    # Update user's study_room_id
    db.query(User).filter(
        User.user_id == new_study_room.creator_id
    ).update({
        "study_room_id": new_study_room.room_id
    })
    db.commit()
    db.refresh(new_study_room)
    return new_study_room

@router.post("/join", response_model=RoomResponse)
async def join_study_room(
    join_data: StudyRoomJoin,
    db: Session = Depends(get_db)
):
    # Validate user exists
    validate_user_exists(db, join_data.user_id)
    
    # 1. Query target study room
    target_room = db.query(StudyRoom).filter(
        StudyRoom.room_id == join_data.room_id
    ).first()
    
    if not target_room:
        raise HTTPException(status_code=404, detail="Study room not found")
    
    # 2. Check if already joined
    if join_data.user_id in (target_room.members_list or []):
        raise HTTPException(status_code=400, detail="User already in this study room")
    
    try:
        # 3. Update member list and count
        # Handle empty list case
        new_members = target_room.members_list or []
        new_members.append(join_data.user_id)
        
        # Use SQLAlchemy update to ensure atomic operation
        db.query(StudyRoom).filter(
            StudyRoom.room_id == join_data.room_id
        ).update({
            "member_count": StudyRoom.member_count + 1,
            "members_list": new_members
        })
        
        # Update user's study_room_id
        db.query(User).filter(
            User.user_id == join_data.user_id
        ).update({
            "study_room_id": join_data.room_id
        })
        
        db.commit()
        
        # 4. Refresh to get latest data
        db.refresh(target_room)
        return target_room
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to join study room: {str(e)}"
        )

@router.post("/leave")
async def leave_study_room(
    leave_data: StudyRoomLeave,
    db: Session = Depends(get_db)
):
    # Validate user exists
    validate_user_exists(db, leave_data.user_id)
    
    # 1. Query target study room
    target_room = db.query(StudyRoom).filter(
        StudyRoom.room_id == leave_data.room_id
    ).first()
    
    if not target_room:
        raise HTTPException(status_code=404, detail="Study room not found")
    
    # 2. Check if user is in the study room
    if not target_room.members_list or leave_data.user_id not in target_room.members_list:
        raise HTTPException(status_code=400, detail="User not in this study room")
    
    try:
        # 3. Update member list and count
        new_members = [m for m in target_room.members_list if m != leave_data.user_id]
        
        # Update user's study_room_id to None
        db.query(User).filter(
            User.user_id == leave_data.user_id
        ).update({
            "study_room_id": None
        })
        
        # If study room is empty, delete it
        if not new_members:
            db.delete(target_room)
            db.commit()
            return {"message": "Study room deleted"}
        
        # Otherwise update member list
        db.query(StudyRoom).filter(
            StudyRoom.room_id == leave_data.room_id
        ).update({
            "member_count": StudyRoom.member_count - 1,
            "members_list": new_members
        })
        
        db.commit()
        
        # 4. Refresh to get latest data
        db.refresh(target_room)
        return target_room
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to leave study room: {str(e)}"
        )

@router.get("/{study_room_id}/{study_user_id}/leaderboard")
async def get_study_room_leaderboard(
    study_room_id: int,
    study_user_id: int,
    db: Session = Depends(get_db)
):
    # 1. Validate study room exists
    study_room = db.query(StudyRoom).get(study_room_id)
    if not study_room:
        raise HTTPException(status_code=404, detail="Study room not found")

    # 2. Get all members and their focus time today
    today = date.today()

    # Explicitly specify select_from(User) to avoid multiple source conflicts
    members = db.query(
        User.user_id,
        User.user_name.label("name"),
        func.coalesce(DailyStatistics.duration_day, 0).label("duration")
    ).select_from(User).join(
        StudyRoom,
        text("JSON_CONTAINS(study_rooms.members_list, CAST(users.user_id AS JSON), '$')")
    ).outerjoin(
        DailyStatistics,
        (User.user_id == DailyStatistics.user_id) &
        (DailyStatistics.date == today)
    ).filter(
        StudyRoom.room_id == study_room_id
    ).order_by(
        func.coalesce(DailyStatistics.duration_day, 0).desc()
    ).all()

    # 3. Generate dense ranking
    ranked_members = []
    current_user_info = None
    if not members:
        return ranked_members

    current_rank = 1
    prev_duration = members[0].duration
    for idx, member in enumerate(members):
        if idx > 0 and member.duration != prev_duration:
            current_rank = idx + 1
            prev_duration = member.duration
        
        member_info = {
            "user_id": member.user_id,
            "name": member.name,
            "rank": current_rank,
            "duration": member.duration
        }
        ranked_members.append(member_info)

        if member.user_id == study_user_id:
            current_user_info = member_info
    target_room = db.query(StudyRoom).filter(
        StudyRoom.room_id == study_room_id
    ).first()
    room_des=target_room.room_description
        
    return {
        "room_description":room_des,
        "leaderboard": ranked_members,
        "current_user": current_user_info
    }

def update_user_study_room_id(db: Session):
    """Update study_room_id for all users"""
    try:
        # Get all study rooms
        study_rooms = db.query(StudyRoom).all()
        
        # Iterate through each study room
        for room in study_rooms:
            if room.members_list:
                # Update study_room_id for all members of this room
                db.query(User).filter(
                    User.user_id.in_(room.members_list)
                ).update({
                    "study_room_id": room.room_id
                })
        
        db.commit()
        return {"message": "User study room IDs updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update user study room IDs: {str(e)}"
        )

@router.post("/update_user_rooms")
async def update_user_rooms(
    db: Session = Depends(get_db)
):
    """Update study_room_id for all users"""
    return update_user_study_room_id(db)