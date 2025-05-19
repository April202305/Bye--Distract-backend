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

try:
    from oss_config import *
except ImportError:
    raise Exception("Please copy oss_config.example.py to oss_config.py and fill in the configuration")


# Chunk size (5MB)
CHUNK_SIZE = 5 * 1024 * 1024

router = APIRouter(prefix="/videos", tags=["videos"])

async def save_temp_video(video: UploadFile) -> str:
    """Save uploaded video to temporary file"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{video.filename}")
    
    with open(temp_path, "wb") as buffer:
        content = await video.read()
        buffer.write(content)
    
    return temp_path

async def upload_to_oss(file_path: str, object_name: str) -> str:
    """Upload file to OSS using multipart upload"""
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    # Initialize multipart upload
    upload_id = bucket.init_multipart_upload(object_name).upload_id
    parts = []
    
    try:
        with open(file_path, 'rb') as f:
            part_number = 1
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                    
                # Upload chunks
                result = bucket.upload_part(
                    object_name,
                    upload_id,
                    part_number,
                    chunk
                )
                parts.append(oss2.models.PartInfo(part_number, result.etag))
                part_number += 1
        
        # Complete multipart upload
        bucket.complete_multipart_upload(object_name, upload_id, parts)
        return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
    except Exception as e:
        # Cancel multipart upload
        bucket.abort_multipart_upload(object_name, upload_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/upload/reference")
async def upload_reference(
    video: UploadFile,
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)  # Inject database session
):
    temp_path=None
    try:
        # Generate unique object name
        object_name = f"videos/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"

        # Save to temporary file
        temp_path = await save_temp_video(video)

        # ---------- Key modification: Synchronously wait for analysis to complete ----------
        # Execute video analysis first (ensure analysis is complete)
        emotions = await asyncio.to_thread(analyze_video_emotions, temp_path)

        # Update user table
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User does not exist")

        user.reference_expression1 = emotions[0] if emotions[0] else ""
        user.reference_expression2 = emotions[1] if emotions[1] else ""

        db.commit()  # Commit transaction

        # Upload to OSS
        oss_url = await upload_to_oss(temp_path, object_name)

        # Delete temporary file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "user_id":user_id,
                "status": "success",
                "message": "Video upload and analysis completed",
                "emo1": user.reference_expression1,
                "emo2": user.reference_expression2,# Return analysis results
                "video_url": oss_url
            }
        )

    except Exception as e:
        # Clean up temporary file on exception
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Processing failed: {str(e)}"
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
    db: Session = Depends(get_db)  # Inject database session
):
    # Check if user exists
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist")

    # Check if task exists
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task does not exist")
    temp_path=None
    try:
        # Generate unique object name
        object_name = f"videos/{user_id}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{video.filename}"

        # Save to temporary file
        temp_path = await save_temp_video(video)
        user=db.query(User).filter(User.user_id == user_id).first()
        emo=[]
        emo = [e for e in [user.reference_expression1, user.reference_expression2] if e]
        if not emo:
            raise HTTPException(status_code=400, detail="User has not set reference expression")        # ---------- Key modification: Synchronously wait for analysis to complete ----------
        # Execute video analysis first (ensure analysis is complete)
        focus_ans = await asyncio.to_thread(analyze_focus_emotions, temp_path,emo,verbose=False)

        # Update task table
        task = db.query(Task).filter(Task.task_id == task_id).first()

        # Update task status (transaction management)
        task.focus = 1
        task.focus_ratio = round(focus_ans * 100, 2)  # Save as percentage
        db.commit()

        # Upload to OSS (can be executed in the background)
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
            content={"status": "error", "message": f"Processing failed: {str(e)}"}
        )
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)