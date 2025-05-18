from fastapi import UploadFile, HTTPException
from datetime import datetime
import os
# 使用 Pillow 库处理图片
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

# OSS配置
OSS_ACCESS_KEY_ID = "REMOVED"
OSS_ACCESS_KEY_SECRET = "REMOVED"
OSS_ENDPOINT = "oss-cn-shenzhen.aliyuncs.com"
OSS_BUCKET_NAME = "ai-face-reg"

# 初始化 OSS 客户端
def get_oss_client():
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)

# 分片大小（1MB，照片文件较小）
CHUNK_SIZE = 1 * 1024 * 1024

async def upload_avatar(user_id: int, file: UploadFile):
    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(400, "仅支持 JPEG/PNG/WEBP 格式")
    
    # 验证文件大小（例如最大 5MB）
    max_size = 5 * 1024 * 1024  # 5MB
    file.file.seek(0, 2)  # 移动指针到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置指针
    if file_size > max_size:
        raise HTTPException(400, "文件大小超过限制")


def generate_avatar_name(user_id: int, filename: str) -> str:
    # 提取文件后缀（如 .jpg）
    ext = os.path.splitext(filename)[1]
    # 生成唯一名称（示例：avatars/123/20231010_153045_abc123.jpg）
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
        raise HTTPException(404, "用户不存在")
    user.avatar_url = avatar_url
    db.commit()

async def save_temp_photo(photo: UploadFile) -> str:
    """保存上传的照片到临时文件"""
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{photo.filename}")
    
    with open(temp_path, "wb") as buffer:
        content = await photo.read()
        buffer.write(content)
    
    return temp_path

async def upload_to_oss(file_path: str, object_name: str) -> str:
    """使用简单上传将文件上传到OSS"""
    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
    
    try:
        # 直接使用简单上传
        bucket.put_object_from_file(object_name, file_path)
        return f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{object_name}"
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传失败: {str(e)}"
        )

router = APIRouter(prefix="/photos", tags=["photos"])

@router.post("/upload")
async def upload_photo(
    photo: UploadFile = File(...),
    user_id: int = None,
    db: Session = Depends(get_db)
):
    """上传用户照片"""
    temp_path = None
    try:
        # 验证文件类型
        if not photo.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持图片文件上传"
            )
        
        # 验证文件大小（限制为5MB）
        content = await photo.read()
        if len(content) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件大小不能超过5MB"
            )
        await photo.seek(0)  # 重置文件指针
        
        # 检查用户是否存在
        if user_id:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在"
                )
            
            # 如果用户已有头像，先删除旧头像
            if user.avatar_url:
                try:
                    # 从URL中提取对象名称
                    old_object_name = user.avatar_url.split(f"{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[-1]
                    # 删除OSS中的旧文件
                    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
                    bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
                    bucket.delete_object(old_object_name)
                except Exception as e:
                    print(f"删除旧头像失败: {str(e)}")  # 记录错误但继续执行
        
        # 生成唯一的对象名称
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        object_name = f"photos/{user_id or 'public'}/{timestamp}_{photo.filename}"
        
        # 保存到临时文件
        temp_path = await save_temp_photo(photo)
        
        # 上传到OSS
        photo_url = await upload_to_oss(temp_path, object_name)
        
        # 如果指定了用户，更新用户头像
        if user_id:
            user.avatar_url = photo_url
            db.commit()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "message": "照片上传成功",
                "user_id": user_id,
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
                "message": f"处理失败: {str(e)}"
            }
        )
    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

# @router.delete("/{user_id}")
# async def delete_photo(
#     user_id: int,
#     db: Session = Depends(get_db)
# ):
#     """删除用户照片"""
#     try:
#         user = db.query(User).filter(User.user_id == user_id).first()
#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_404_NOT_FOUND,
#                 detail="用户不存在"
#             )
        
#         if not user.avatar_url:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="用户没有上传照片"
#             )
        
#         # 从URL中提取对象名称
#         object_name = user.avatar_url.split(f"{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/")[-1]
        
#         # 删除OSS中的文件
#         auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
#         bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET_NAME)
#         bucket.delete_object(object_name)
        
#         # 更新用户头像URL
#         user.avatar_url = None
#         db.commit()
        
#         return JSONResponse(
#             status_code=status.HTTP_200_OK,
#             content={
#                 "status": "success",
#                 "message": "照片删除成功"
#             }
#         )
        
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "status": "error",
#                 "message": f"删除失败: {str(e)}"
#             }
#         )

@router.post("/")
async def get_user_avatars(
    user_ids: str,  # 接收逗号分隔的用户ID字符串
    db: Session = Depends(get_db)
):
    """批量获取用户头像URL
    
    Args:
        user_ids: 逗号分隔的用户ID字符串，例如 "1,2,3"
    """
    try:
        # 将字符串转换为整数列表
        id_list = [int(id_str.strip()) for id_str in user_ids.split(',') if id_str.strip()]
        
        if not id_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请提供有效的用户ID列表"
            )
        
        # 查询用户头像URL
        users = db.query(User).filter(
            User.user_id.in_(id_list)
        ).all()
        
        # 构建响应数据
        avatar_dict = {user.user_id: user.avatar_url for user in users}
        
        # 确保返回所有请求的用户ID，没有头像的返回null
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
            detail="用户ID格式不正确"
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": f"获取头像失败: {str(e)}"
            }
        ) 