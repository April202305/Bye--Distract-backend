# 自习室管理系统

这是一个基于FastAPI开发的自习室管理系统，提供用户管理、任务管理和自习室管理等功能。

## 功能特性

### 用户管理
- 用户注册和登录
- 用户信息管理
- 用户认证和授权

### 自习室管理
- 创建自习室
- 加入自习室
- 自习室成员管理
- 自习室信息展示

### 任务管理
- 创建学习任务
- 任务计时功能（正计时/倒计时）
- 任务完成状态追踪
- 任务放弃功能

## 技术栈

- **后端框架**: FastAPI
- **数据库**: SQLAlchemy (ORM)
- **数据库迁移**: Alembic
- **认证**: JWT (JSON Web Tokens)
- **API文档**: Swagger UI (自动生成)

## 项目结构

```
app/
├── api/            # API路由和端点
├── models/         # 数据库模型
├── schemas/        # Pydantic模型
├── services/       # 业务逻辑
├── database/       # 数据库配置
└── main.py         # 应用入口
```

## 安装说明

1. 克隆项目
```powershell
git clone [项目地址]
cd [项目目录]
```

2. 创建虚拟环境
```powershell
python -m venv myenv
.\myenv\Scripts\activate
```

3. 安装依赖
```powershell
pip install -r requirements.txt
```

4. 初始化数据库
```powershell
alembic upgrade head
```

5. 运行应用
```powershell
python -m app.main
```

## API文档

启动应用后，访问以下地址查看API文档：
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## 主要API端点

### 用户相关
- POST /users/register - 用户注册
- POST /users/login - 用户登录
- GET /users/me - 获取当前用户信息

### 自习室相关
- POST /study_room/add - 创建自习室
- POST /study_room/join - 加入自习室

### 任务相关
- POST /tasks - 创建任务
- GET /tasks - 获取任务列表
- PUT /tasks/{task_id} - 更新任务状态

## 开发说明

- 使用FastAPI框架开发RESTful API
- 采用SQLAlchemy作为ORM工具
- 使用Alembic进行数据库迁移
- 实现了完整的错误处理机制
- 支持异步操作

## 注意事项

- 确保数据库配置正确
- 运行前需要激活虚拟环境
- 首次运行需要执行数据库迁移
- 建议使用Python 3.8+版本 