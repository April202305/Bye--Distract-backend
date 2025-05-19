# routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.users import get_db
from app.models.models import Task, StudyStatistics, DailyStatistics
from app.schemas.task import TaskCreate, TaskResponse, Taskmodify, Taskfinished, BaseResponse, Taskdel
from app.models.models import User
from datetime import datetime, date
from sqlalchemy import func
# from app.api.sta import force_update_daily_stats


router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{user_id}")
async def get_user_tasks(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all tasks for a user"""
    tasks = db.query(Task).filter(
        Task.user_id == user_id,
        Task.is_finished == False
    ).order_by(Task.build_time.desc()).all()

    
    return tasks

def validate_user_exists(db: Session, user_id: int):
    """Validate if user exists"""
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/add", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    # Validate user exists
    validate_user_exists(db, task_data.user_id)
    
    

    # Create task
    new_task = Task(
        user_id=task_data.user_id,
        expected_mode=task_data.expected_mode,
        title=task_data.title,
        time=task_data.time
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

def validate_task_exists(db: Session, task_id: int):
    """Validate if task exists"""
    task_id = db.query(Task).get(task_id)
    if not task_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_id



@router.post("/modify", response_model=TaskResponse)
async def modify_task(
    task_data: Taskmodify,
    db: Session = Depends(get_db)
):
    # Validate task exists
    validate_task_exists(db, task_data.task_id)
    
    # Get task object to modify
    db_task = db.query(Task).filter(Task.task_id == task_data.task_id).first()
    
    # Update task fields (excluding task_id itself)
    if task_data.expected_mode is not None:
        db_task.expected_mode = task_data.expected_mode
    if task_data.title is not None:
        db_task.title = task_data.title
    if task_data.time is not None:
        db_task.time = task_data.time

    db.commit()
    db.refresh(db_task)
    return db_task

@router.post("/del", response_model=BaseResponse)
async def delete_task(
    task_data: Taskdel,
    db: Session = Depends(get_db)
):
    # Validate task exists
    validate_task_exists(db, task_data.task_id)
    
    # Get task object to delete
    db_task = db.query(Task).filter(Task.task_id == task_data.task_id).first()
    
    # Execute delete operation
    db.delete(db_task)
    db.commit()  # Ensure immediate commit of delete operation
    
    # Verify task has been deleted
    deleted_task = db.query(Task).filter(Task.task_id == task_data.task_id).first()
    
    if deleted_task:
        raise HTTPException(status_code=500, detail="Failed to delete task")
    
    # Return success response (needs to match BaseResponse model)
    return BaseResponse(
        code=200,
        message="Delete successful",
        data=None
    )
@router.post("/finish", response_model=TaskResponse)
async def modify_task(
    task_data: Taskfinished,
    db: Session = Depends(get_db)
):
    # Validate task exists
    validate_task_exists(db, task_data.task_id)
    
    # Get task object to modify
    db_task = db.query(Task).filter(Task.task_id == task_data.task_id).first()
    
    if task_data.time is not None:
        db_task.time = task_data.time
    db_task.is_finished = True
    db_task.finish_time = datetime.now()
    db_task.given_up = task_data.given_up   

    # Update statistics
    # 1. Update total statistics
    stats = db.query(StudyStatistics).filter(
        StudyStatistics.user_id == db_task.user_id
    ).first()
    
    if not stats:
        stats = StudyStatistics(user_id=db_task.user_id)
        db.add(stats)
        db.commit()
    print(task_data.given_up == 0)   
    if task_data.given_up == 0:
        stats.total_frequency += 1
        stats.total_duration += db_task.time
        stats.last_updated = date.today()
    
    # 2. Update daily statistics
    today = date.today()
    daily = db.query(DailyStatistics).filter(
        DailyStatistics.user_id == db_task.user_id,
        DailyStatistics.date == today,
    ).first()
    
    if not daily:
        daily = DailyStatistics(
            user_id=db_task.user_id,
            date=today,
            frequency_day=0,
            duration_day=0,
            given_up_day=0,
            task_breakdown={}
        )
        db.add(daily)
    if daily.task_breakdown is None:
       daily.task_breakdown = {}
    if task_data.given_up == 0:
        daily.frequency_day += 1
        daily.duration_day += db_task.time
        
        # Commit current task update first
        db.commit()
        
        # Get all valid tasks for today (including the one just updated)
        finished_tasks = db.query(Task).filter(
            Task.user_id == db_task.user_id,
            func.date(Task.finish_time) == today,
            Task.is_finished == True,
            Task.given_up == False
        ).all()
        
        total_duration = sum(task.time for task in finished_tasks)
        
        # Merge time for tasks with same name
        from collections import defaultdict
        duration_by_title = defaultdict(int)
        for task in finished_tasks:
            duration_by_title[task.title] += task.time

        # Generate new distribution ratio
        new_breakdown = {}
        if total_duration > 0:
            new_breakdown = {
                title: round((duration / total_duration) * 100, 2)
                for title, duration in duration_by_title.items()
            }
        
        # Update daily statistics
        daily.task_breakdown = new_breakdown                        
    else:
       daily.given_up_day+=1   
    
    db.commit()
    db.refresh(db_task)


    return db_task