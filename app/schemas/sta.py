from pydantic import BaseModel
from datetime import date
from typing import Dict

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
    
class StatisticsResponse(BaseModel):
    total: StatisticsBase
    today: DailyStatistics
    
    class Config:
        orm_mode = True