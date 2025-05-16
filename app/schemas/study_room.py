# schemas/task.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class StudyRoomCreate(BaseModel):
    user_id: int
    room_name: str  # 0=正计时，1=倒计时
    room_description:str

class RoomResponse(BaseModel):
    creator_id: int  # 新增字段，对应数据库中的外键
    room_name: str
    room_description: str
    created_time: datetime
    room_id: int

    class Config:
        from_attributes = True  # 允许从ORM对象自动转换


class StudyRoomJoin(BaseModel):
    user_id:int
    room_id:int     

class StudyRoomLeave(BaseModel):
    user_id: int
    room_id: int       