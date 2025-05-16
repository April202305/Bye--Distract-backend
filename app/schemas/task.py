# schemas/task.py
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class TaskCreate(BaseModel):
    user_id: int
    expected_mode: int  # 0=正计时，1=倒计时
    title: str
    time: int

class TaskResponse(BaseModel):
    task_id: int
    user_id: int  # 新增字段，对应数据库中的外键
    title: str
    expected_mode: int
    time: int
    is_finished: bool  # 新增字段
    build_time: datetime
    given_up: bool  # 新增字段
    finish_time: datetime

    class Config:
        from_attributes = True  # 允许从ORM对象自动转换

class Taskmodify(BaseModel):
    task_id: int
    expected_mode: int  # 0=正计时，1=倒计时
    title: str
    time: int

class Taskfinished(BaseModel):
    task_id: int
    time: int
    given_up: bool 

class BaseResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None


class Taskdel(BaseModel):
    task_id: int    

