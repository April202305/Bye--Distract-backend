from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.models import User,Task
from app.schemas.login_schemas import UserCreate, UserLogin, UserResponse
from app.services.auth import get_password_hash, verify_password
from datetime import datetime
from app.utilts.video_in import analyze_video_emotions
from app.utilts.video_out import analyze_focus_emotions
import os
import oss2
import tempfile
from typing import Optional
import asyncio
from fastapi.responses import JSONResponse
from fastapi import FastAPI, UploadFile, File
from app.api.users import get_db

# OSS配置
OSS_ACCESS_KEY_ID = "REMOVED"
OSS_ACCESS_KEY_SECRET = "REMOVED"
OSS_ENDPOINT = "oss-cn-shenzhen.aliyuncs.com"
OSS_BUCKET_NAME = "ai-face-reg"

# 分片大小（5MB）
CHUNK_SIZE = 5 * 1024 * 1024

router = APIRouter(prefix="/videos", tags=["videos"])

async def save_temp_video(video: UploadFile) -> str:
    """保存上传的视频到临时文件"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{video.filename}")
    
    with open(temp_path, "wb") as buffer:
        content = await video.read()
        buffer.write(content)
    
    return temp_path

async def upload_to_oss(file_path: str, object_name: str) -> str:
    """使用分片上传将文件上传到OSS"""
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    # 初始化分片上传
    upload_id = bucket.init_multipart_upload(object_name).upload_id
    parts = []
    
    try:
        with open(file_path, 'rb') as f:
            part_number = 1
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                    
                # 上传分片
                result = bucket.upload_part(
                    object_name,
                    upload_id,
                    part_number,
                    chunk
                )
                parts.append(oss2.models.PartInfo(part_number, result.etag))
                part_number += 1
        
        # 完成分片上传
        bucket.complete_multipart_upload(object_name, upload_id, parts)
        return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
    except Exception as e:
        # 取消分片上传
        bucket.abort_multipart_upload(object_name, upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )


@router.post("/upload/reference")
async def upload_reference(
    video: UploadFile,
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)  # 注入数据库会话
):
    temp_path=None
    try:
        # 生成唯一的对象名称
        object_name = f"videos/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"

        # 保存到临时文件
        temp_path = await save_temp_video(video)

        # ---------- 关键修改：同步等待分析完成 ----------
        # 先执行视频分析（确保分析完成）
        emotions = await asyncio.to_thread(analyze_video_emotions, temp_path)

        # 更新用户表
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")

        user.reference_expression1 = emotions[0] if emotions[0] else ""
        user.reference_expression2 = emotions[1] if emotions[1] else ""

        db.commit()  # 提交事务

        # 再上传到OSS
        oss_url = await upload_to_oss(temp_path, object_name)

        # 删除临时文件
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "user_id":user_id,
                "status": "success",
                "message": "视频上传及分析完成",
                "emo1": user.reference_expression1,
                "emo2": user.reference_expression2,# 返回分析结果
                "video_url": oss_url
            }
        )

    except Exception as e:
        # 异常时清理临时文件
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"处理失败: {str(e)}"
            }
        )

# @router.post("/test-upload")
# async def test_upload(file: UploadFile = File(...)):
#     temp_path = await save_temp_video(file)
#     return {"temp_path": temp_path}

@router.post("/upload/ans")
async def upload_reference(
    video: UploadFile,
    user_id: int,
    task_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)  # 注入数据库会话
):
    # 检查用户是否存在
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查任务是否存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    temp_path=None
    try:
        # 生成唯一的对象名称
        object_name = f"videos/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"

        # 保存到临时文件
        temp_path = await save_temp_video(video)
        user=db.query(User).filter(User.user_id == user_id).first()
        emo=[]
        emo = [e for e in [user.reference_expression1, user.reference_expression2] if e]
        if not emo:
            raise HTTPException(status_code=400, detail="用户未设置参考表情")        # ---------- 关键修改：同步等待分析完成 ----------
        # 先执行视频分析（确保分析完成）
        focus_ans = await asyncio.to_thread(analyze_focus_emotions, temp_path,emo,verbose=False)

        # 更新任务表
        task = db.query(Task).filter(Task.task_id == task_id).first()

        # 更新任务状态（事务管理）
        task.focus = 1
        task.focus_ratio = round(focus_ans * 100, 2)  # 存为百分比
        db.commit()

        # 上传到OSS（可后台执行）
        oss_url = await upload_to_oss(temp_path, object_name)

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "focus_ratio": f"{task.focus_ratio}%",
                "video_url": oss_url
            }
        )

    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"处理失败: {str(e)}"}
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)