from fastapi import UploadFile, HTTPException
from datetime import datetime
import os
# Use Pillow library for image processing
from PIL import Image
import io
from alibabacloud_oss_v2.client import Client
from alibabacloud_oss_v2.models import PutObjectRequest

from sqlalchemy.orm import Session
from app.models.models import User
from fastapi import APIRouter, UploadFile, Depends, status
from sqlalchemy.orm import Session
from app.api.users import get_db


from fastapi import APIRouter, UploadFile, Depends, status
from sqlalchemy.orm import Session

import oss2
import tempfile
from fastapi.responses import JSONResponse
import asyncio
from fastapi import FastAPI, UploadFile, File

try:
    from oss_config import *
except ImportError:
    raise Exception("Please copy oss_config.example.py to oss_config.py and fill in the configuration")

# Initialize OSS client
def get_oss_client():
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

# Chunk size (1MB, photos are relatively small)
CHUNK_SIZE = 1 * 1024 * 1024

async def upload_avatar(user_id: int, file: UploadFile):
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Only JPEG/PNG/WEBP formats are supported")
    
    # Validate file size (e.g., max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    file.file.seek(0, 2)  # Move pointer to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset pointer
    if file_size > max_size:
        raise HTTPException(400, "File size exceeds limit")


def generate_avatar_name(user_id: int, filename: str) -> str:
    # Extract file extension (e.g., .jpg)
    ext = os.path.splitext(filename)[1]
    # Generate unique name (example: avatars/123/20231010_153045_abc123.jpg)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = 123456
    return f"avatars/{user_id}/{timestamp}_{unique_id}{ext}"   


def resize_image(content: bytes, size=(200, 200)) -> bytes:
    image = Image.open(io.BytesIO(content))
    image.thumbnail(size)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85)
    return output.getvalue()

async def delete_old_avatar(old_url: str):
    if not old_url:
        return
    object_name = old_url.split(f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[1]
    client = get_oss_client()
    client.delete_object(bucket=OSS_BUCKET_NAME, key=object_name)


def update_user_avatar(db: Session, user_id: int, avatar_url: str):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.avatar_url = avatar_url
    db.commit()

async def save_temp_photo(photo: UploadFile) -> str:
    """Save uploaded photo to temporary file"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{photo.filename}")
    
    with open(temp_path, "wb") as buffer:
        content = await photo.read()
        buffer.write(content)
    
    return temp_path

async def upload_to_oss(file_path: str, object_name: str) -> str:
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    try:
        bucket.put_object_from_file(object_name, file_path)
        return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"upload error: {str(e)}"
        )

router = APIRouter(prefix="/photos", tags=["photos"])

@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    user_id: int = None,
    db: Session = Depends(get_db)
):
    temp_path = None
    try:
        # Validate file type
        if not photo.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="only support image"
            )
        
        # Validate file size (限制为5MB)
        content = await photo.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file not bigger than 5MB"
            )
        await photo.seek(0)  
        
        # Check if user exists
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
        
        # Generate unique object name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        object_name = f"photos/{user_id or 'public'}/{timestamp}_{photo.filename}"
        
        # Save to temporary file
        temp_path = await save_temp_photo(photo)
        
        # Upload to OSS
        photo_url = await upload_to_oss(temp_path, object_name)
        
        # If specified user, update user avatar
        if user_id:
            user.avatar_url = photo_url
            db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "Photo uploaded successfully",
                "user_id":user_id,
                "photo_url": photo_url
            }
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Processing failed: {str(e)}"
            }
        )
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# @router.delete("/{user_id}")
# async def delete_photo(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):
#     """Delete user photo"""
#     try:
#         user = db.query(User).filter(User.user_id == user_id).first()
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="User not found"
#             )
        
#         if not user.avatar_url:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="User has no photo"
#             )
        
#         # Extract object name from URL
#         object_name = user.avatar_url.split(f"{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[-1]
        
#         # Delete file from OSS
#         auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
#         bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
#         bucket.delete_object(object_name)
        
#         # Update user avatar URL
#         user.avatar_url = None
#         db.commit()
        
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status": "success",
#                 "message": "Photo deleted successfully"
#             }
#         )
        
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status": "error",
#                 "message": f"Delete failed: {str(e)}"
#             }
#         )
    

@router.post("/")
async def get_user_avatars(
    user_ids: str,  # Receive comma-separated user ID string
    db: Session = Depends(get_db)
):
    """Get user avatar URLs in batch
    
    Args:
        user_ids: Comma-separated user ID string, e.g. "1,2,3"
    """
    try:
        # Convert string to integer list
        id_list = [int(id_str.strip()) for id_str in user_ids.split(',') if id_str.strip()]
        
        if not id_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide valid user ID list"
            )
        
        # Query user avatar URLs
        users = db.query(User).filter(
            User.user_id.in_(id_list)
        ).all()
        
        # Build response data
        avatar_dict = {user.user_id: user.avatar_url for user in users}
        
        # Ensure all requested user IDs are returned, return null for those without avatars
        result = {
            str(user_id): avatar_dict.get(user_id) for user_id in id_list
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "data": result
            }
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"Failed to get avatars: {str(e)}"
            }
        )     