import asyncio
from app.api.video import upload_to_oss  # 替换为实际模块路径
import os
from datetime import datetime

async def test_upload():
    # 测试文件路径（本地生成一个测试文件）
    test_file_path = "1.mp4"
    # # 确保 file_path 存在
    # if not os.path.exists(test_file_path):
    #     raise ValueError(f"文件路径 {test_file_path} 不存在！")
    #
    # # 安全提取文件名和后缀
    # filename = os.path.basename(test_file_path)  # 获取文件名（带后缀）
    # file_name_without_ext, file_ext = os.path.splitext(filename)  # 分离主名和后缀
    #
    # # 处理无后缀的情况（如直接传入了 "video" 而非 "video.mp4"）
    # if not file_ext:
    #     file_ext = ".mp4"  # 默认后缀
    # else:
    #     file_ext = file_ext.lower().strip()  # 统一转为小写并去空格
    #
    # # 生成唯一的 object_name（示例：按时间戳命名）
    # timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # object_name = f"uploads/{timestamp}_{file_name_without_ext.strip()}{file_ext}"

    # 继续后续上传逻辑...
    
    # # 生成测试文件（如果本地没有）
    # with open(test_file_path, "w") as f:
    #     f.write("This is a test file for OSS upload.")
    
    # OSS 上的目标文件名（确保唯一性，避免覆盖已有文件）
    object_name = "test_upload/test_file.mp4"
    
    try:
        # 调用上传函数
        url = await upload_to_oss(test_file_path, object_name)
        print(f"✅ 上传成功！文件URL: {url}")
    except Exception as e:
        print(f"❌ 上传失败: {str(e)}")
    finally:
        # 清理本地测试文件（可选）
        if os.path.exists(test_file_path):
            os.remove(test_file_path)

if __name__ == "__main__":
    asyncio.run(test_upload())