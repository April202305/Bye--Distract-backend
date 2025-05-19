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
    reference_expression1 = Column(String(50))  # Default empty string
    reference_expression2 = Column(String(50))  # Default empty string
    avatar_url = Column(String(255), nullable=True)  # Can be null, initial value can be None
    # Explicitly specify foreign key relationship
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
        default=lambda: random.randint(10000, 99999)  # Generate 5-digit random number
    )
    creator_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    room_name = Column(String(255))
    created_time = Column(DateTime, server_default=func.now())
    member_count = Column(Integer, default=1)
    members_list = Column(JSON)  # Store user ID list, e.g. [1, 2, 3]
    room_description = Column(String(255), default="")

    # Relationship with User model
    creator = relationship("User", back_populates="study_rooms", foreign_keys=[creator_id])

class Task(Base):
    __tablename__ = 'tasks'

    task_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    title = Column(String(255))
    expected_mode = Column(Integer)  # 0=count up, 1=count down
    time = Column(Integer)
    is_finished = Column(
        Boolean, 
        default=False,            # Default value at Python level (automatically filled when inserting)
        server_default=expression.false(),  # Default value at database level (directly written to SQL)
        nullable=False            # No null values allowed, must be True/False
    )
    build_time = Column(DateTime, server_default=func.now())
    given_up = Column(Boolean, server_default=text('false'))
    focus = Column(Boolean, server_default=text('false'))
    focus_ratio = Column(Float, default=0.0)  # Focus ratio (0-1)
    finish_time = Column(DateTime, server_default=func.now())

    # Relationship with User model
    user = relationship("User", back_populates="tasks")

class StudyStatistics(Base):
    """Total study statistics table"""
    __tablename__ = "study_statistics"
    
    user_id = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    total_frequency = Column(Integer, default=0)  # Total completion count
    total_duration = Column(Integer, default=0)   # Total focus duration (seconds)
    average_daily_duration = Column(Float, default=0.0)  # Average daily duration (seconds)
    last_updated = Column(Date, default=date.today)
    
    user = relationship("User", back_populates="stats")

class DailyStatistics(Base):
    """Daily statistics table"""
    __tablename__ = "daily_statistics"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    date = Column(Date, default=date.today)
    frequency_day = Column(Integer, default=0)    # Daily completion count
    duration_day = Column(Integer, default=0)     # Daily focus duration (seconds)
    given_up_day = Column(Integer, default=0)     # Daily abandonment count
    task_breakdown = Column(JSON)                 # Task time distribution
    
    user = relationship("User", back_populates="daily_stats")


