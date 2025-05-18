from pydantic import BaseModel
from datetime import date, datetime
from typing import Dict, List, Optional

class StatisticsBase(BaseModel):
    total_frequency: int
    total_duration: int
    average_daily_duration: float
    
class DailyStatistics(BaseModel):
    date: date
    frequency_day: int
    duration_day: int
    given_up_day: int
    task_breakdown: Dict[str, float]

class TodayFocus(BaseModel):
    task_name: str
    completion_time: datetime  # 完成时间（分钟）
    focus_ratio: float    # 专注比率（百分比）
    focus_time: float     # 专注时间（分钟）

class TaskStat(BaseModel):
    title: str
    total_time: int
    focus_ratio: float
    focused_time: float

    
class StatisticsResponse(BaseModel):
    total: StatisticsBase
    today: Optional[DailyStatistics]
    tasks: Optional[List[TaskStat]]
    class Config:
        from_attributes = True
