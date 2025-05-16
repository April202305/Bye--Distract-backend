import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from app.api.users import router as users_router
from app.api.tasks import router as tasks_router
import uvicorn
from app.api.study_room import router as study_room_router
from app.api.sta import router as sta_router

app = FastAPI()

# 注册路由
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(tasks_router)
app.include_router(study_room_router)
app.include_router(sta_router)


if __name__== '__main__':
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001)