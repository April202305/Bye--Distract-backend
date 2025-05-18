from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Boolean, text, Float, Date
from datetime import datetime
from app.database.database import Base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, expression
import random
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(50), unique=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    study_room_id = Column(Integer, ForeignKey('study_rooms.room_id'), nullable=True)
    reference_expression1 = Column(String(50))  # 默认空字符串
    reference_expression2 = Column(String(50)) # 默认空字符串
    avatar_url = Column(String(255), nullable=True)  # 允许为空，初始值可以是 None
    # 明确指定外键关系
    study_rooms = relationship("StudyRoom", 
                             back_populates="creator",
                             foreign_keys="StudyRoom.creator_id")
    current_room = relationship("StudyRoom",
                              foreign_keys=[study_room_id],
                              backref="members")
    tasks = relationship("Task", back_populates="user")

    stats = relationship("StudyStatistics", back_populates="user", uselist=False)
    daily_stats = relationship("DailyStatistics", back_populates="user")

class StudyRoom(Base):
    __tablename__ = 'study_rooms'
    room_id = Column(
        Integer, 
        primary_key=True,
        default=lambda: random.randint(10000, 99999)  # 生成5位随机数
    )
    creator_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    room_name = Column(String(255))
    created_time = Column(DateTime, server_default=func.now())
    member_count = Column(Integer, default=1)
    members_list = Column(JSON)  # 存储用户ID列表，例如 [1, 2, 3]
    room_description = Column(String(255), default="")

    # 与 User 模型的关联
    creator = relationship("User", back_populates="study_rooms", foreign_keys=[creator_id])

class Task(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(255))
    expected_mode = Column(Integer)  # 0=正计时，1=倒计时
    time = Column(Integer)
    is_finished = Column(
        Boolean, 
        default=False,            # Python 层面的默认值（代码插入时自动填充）
        server_default=expression.false(),  # 数据库层面的默认值（直接写入 SQL）
        nullable=False            # 禁止空值，确保必须为 True/False
    )
    build_time = Column(DateTime, server_default=func.now())
    given_up = Column(Boolean, server_default=text('false'))
    focus = Column(Boolean, server_default=text('false'))
    focus_ratio = Column(Float, default=0.0)  # 专注比率（0-1）
    finish_time = Column(DateTime, server_default=func.now())

    # 与 User 模型的关ms联
    user = relationship("User", back_populates="tasks")

class StudyStatistics(Base):
    """学习总统计数据表"""
    __tablename__ = "study_statistics"
    
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    total_frequency = Column(Integer, default=0)  # 累计完成次数
    total_duration = Column(Integer, default=0)   # 累计专注时长（秒）
    average_daily_duration = Column(Float, default=0.0)  # 日均时长（秒）
    last_updated = Column(Date, default=date.today)
    
    user = relationship("User", back_populates="stats")

class DailyStatistics(Base):
    """每日统计数据表"""
    __tablename__ = "daily_statistics"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    date = Column(Date, default=date.today)
    frequency_day = Column(Integer, default=0)    # 当日完成次数
    duration_day = Column(Integer, default=0)     # 当日专注时长（秒）
    given_up_day = Column(Integer, default=0)     # 当日放弃次数
    task_breakdown = Column(JSON)                 # 任务时间分布
    
    user = relationship("User", back_populates="daily_stats")


