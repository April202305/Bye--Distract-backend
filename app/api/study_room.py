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
from fastapi import status  # 推荐直接从 FastAPI 导入

router = APIRouter(prefix="/study_room", tags=["study_room"])

def validate_user_exists(db: Session, user_id: int):
    """验证用户是否存在"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@router.post("/add", response_model=RoomResponse)
async def create_task(
    room_data: StudyRoomCreate,
    db: Session = Depends(get_db)
):
    # 验证用户存在
    validate_user_exists(db, room_data.user_id)
    # 检查用户是否已加入其他自习室
    target_user = db.query(User).filter(
        User.user_id == room_data.user_id
    ).first()
    if target_user.study_room_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户已加入其他自习室，请先退出后再创建新房间"
        )
    # 创建任务
    new_study_room = StudyRoom(
        creator_id=room_data.user_id,
        room_name=room_data.room_name,
        room_description=room_data.room_description,
        members_list=[room_data.user_id]
    )
    

    db.add(new_study_room)
    db.commit()
        # 更新用户的study_room_id
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
    # 验证用户存在
    validate_user_exists(db, join_data.user_id)
    
    # 1. 查询目标自习室
    target_room = db.query(StudyRoom).filter(
        StudyRoom.room_id == join_data.room_id
    ).first()
    
    if not target_room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    
    # 2. 检查是否已经加入
    if join_data.user_id in (target_room.members_list or []):
        raise HTTPException(status_code=400, detail="用户已在该自习室")
    
    try:
        # 3. 更新成员列表和数量
        # 处理空列表的情况
        new_members = target_room.members_list or []
        new_members.append(join_data.user_id)
        
        # 使用SQLAlchemy的更新方式确保原子操作
        db.query(StudyRoom).filter(
            StudyRoom.room_id == join_data.room_id
        ).update({
            "member_count": StudyRoom.member_count + 1,
            "members_list": new_members
        })
        
        # 更新用户的study_room_id
        db.query(User).filter(
            User.user_id == join_data.user_id
        ).update({
            "study_room_id": join_data.room_id
        })
        
        db.commit()
        
        # 4. 刷新获取最新数据
        db.refresh(target_room)
        return target_room
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"加入自习室失败: {str(e)}"
        )

@router.post("/leave")
async def leave_study_room(
    leave_data: StudyRoomLeave,
    db: Session = Depends(get_db)
):
    # 验证用户存在
    validate_user_exists(db, leave_data.user_id)
    
    # 1. 查询目标自习室
    target_room = db.query(StudyRoom).filter(
        StudyRoom.room_id == leave_data.room_id
    ).first()
    
    if not target_room:
        raise HTTPException(status_code=404, detail="自习室不存在")
    
    # 2. 检查用户是否在自习室中
    if not target_room.members_list or leave_data.user_id not in target_room.members_list:
        raise HTTPException(status_code=400, detail="用户不在该自习室")
    
    try:
        # 3. 更新成员列表和数量
        new_members = [m for m in target_room.members_list if m != leave_data.user_id]
        
        # 更新用户的study_room_id为None
        db.query(User).filter(
            User.user_id == leave_data.user_id
        ).update({
            "study_room_id": None
        })
        
        # 如果自习室空了，删除自习室
        if not new_members:
            db.delete(target_room)
            db.commit()
            return {"message": "自习室已删除"}
        
        # 否则更新成员列表
        db.query(StudyRoom).filter(
            StudyRoom.room_id == leave_data.room_id
        ).update({
            "member_count": StudyRoom.member_count - 1,
            "members_list": new_members
        })
        
        db.commit()
        
        # 4. 刷新获取最新数据
        db.refresh(target_room)
        return target_room
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"退出自习室失败: {str(e)}"
        )



@router.get("/{study_room_id}/{study_user_id}/leaderboard")
async def get_study_room_leaderboard(
    study_room_id: int,
    study_user_id: int,
    db: Session = Depends(get_db)
):
    # 1. 验证自习室存在
    study_room = db.query(StudyRoom).get(study_room_id)
    if not study_room:
        raise HTTPException(status_code=404, detail="自习室不存在")

    # 2. 获取所有成员及其今日专注时间
    today = date.today()

    # 明确指定 select_from(User)，避免多来源冲突
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

    # 3. 生成密集排名
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
    """更新所有用户的study_room_id"""
    try:
        # 获取所有自习室
        study_rooms = db.query(StudyRoom).all()
        
        # 遍历每个自习室
        for room in study_rooms:
            if room.members_list:
                # 更新该自习室所有成员的study_room_id
                db.query(User).filter(
                    User.user_id.in_(room.members_list)
                ).update({
                    "study_room_id": room.room_id
                })
        
        db.commit()
        return {"message": "用户自习室ID更新成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"更新用户自习室ID失败: {str(e)}"
        )

@router.post("/update_user_rooms")
async def update_user_rooms(
    db: Session = Depends(get_db)
):
    """更新所有用户的study_room_id"""
    return update_user_study_room_id(db)