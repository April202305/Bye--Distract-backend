from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.api.users import get_db
from app.models.models import User, Task, StudyStatistics, DailyStatistics
from app.schemas.sta import StatisticsResponse

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/{user_id}", response_model=StatisticsResponse)
async def get_user_stats(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user statistics"""
    stats = db.query(StudyStatistics).filter(
        StudyStatistics.user_id == user_id
    ).first()
    
    if not stats:
        stats = StudyStatistics(user_id=user_id)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    
    user = db.query(User).get(user_id)
    days_since_join = (date.today() - user.created_at.date()).days
    avg_duration = stats.total_duration / max(days_since_join, 1)
    
    daily = db.query(DailyStatistics).filter(
        DailyStatistics.user_id == user_id,
        DailyStatistics.date == date.today()
    ).first()
    today_tasks = db.query(Task).filter(
        Task.user_id == user_id,
        func.date(Task.finish_time) == date.today(),
        Task.is_finished == True
    ).all()
    
    task_stats = []
    for task in today_tasks:
        if task.focus_ratio is not None:
            focused_time = task.time * task.focus_ratio/100 if task.focus_ratio else 0
            task_stats.append({
            "title": task.title,
            "total_time": task.time,
            "focus_ratio": task.focus_ratio/100 or 0.0,
            "focused_time": round(focused_time, 2)
            })    
    
    
    return {
        "total": {
            "total_frequency": stats.total_frequency,
            "total_duration": stats.total_duration,
            "average_daily_duration": avg_duration
        },
        "today": daily,
        "tasks": task_stats
    }

