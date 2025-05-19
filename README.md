# Pomodoro Timer Backend

A robust backend system for managing Pomodoro timer sessions, built with FastAPI. This system provides comprehensive functionality for tracking work sessions, managing tasks, and monitoring productivity.

## Features

### Timer Management
- Create and manage Pomodoro sessions
- Support for both countdown and count-up timers
- Customizable work/break intervals
- Session statistics and history

### Task Management
- Create and organize tasks
- Track task completion status
- Task abandonment handling
- Task categorization and prioritization

### User Management
- User registration and authentication
- User profile management
- Session history per user
- Productivity analytics

## Tech Stack

- **Backend Framework**: FastAPI
- **Database**: SQLAlchemy (ORM)
- **Database Migration**: Alembic
- **Authentication**: JWT (JSON Web Tokens)
- **API Documentation**: Swagger UI (Auto-generated)

## Project Structure

```
app/
├── api/            # API routes and endpoints
├── models/         # Database models
├── schemas/        # Pydantic models
├── services/       # Business logic
├── database/       # Database configuration
└── main.py         # Application entry point
```

## Installation

1. Clone the repository
```powershell
git clone [https://github.com/April202305/Bye--Distract-backend]
cd [project-directory]
```

2. Create virtual environment
```powershell
python -m venv myenv
.\myenv\Scripts\activate
```

3. Install dependencies
```powershell
pip install -r requirements.txt
```

4. Initialize database
```powershell
alembic upgrade head
```

5. Run the application
```powershell
python -m app.main
```

## API Documentation

Once the application is running, access the API documentation at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## Key API Endpoints

### Timer Related
- POST /timer/start - Start a new Pomodoro session
- GET /timer/status - Get current timer status
- POST /timer/pause - Pause current session
- POST /timer/resume - Resume paused session
- POST /timer/stop - Stop current session

### Task Related
- POST /tasks - Create a new task
- GET /tasks - List all tasks
- PUT /tasks/{task_id} - Update task status
- DELETE /tasks/{task_id} - Delete a task

### User Related
- POST /users/register - Register new user
- POST /users/login - User login
- GET /users/me - Get current user info

## Development Notes

- Built with FastAPI for high performance
- Uses SQLAlchemy for database operations
- Implements comprehensive error handling
- Supports asynchronous operations
- Includes detailed logging for debugging

## Requirements

- Python 3.8+
- PostgreSQL (or your preferred database)
- Virtual environment (recommended)

## Notes

- Ensure proper database configuration
- Activate virtual environment before running
- Execute database migrations on first run
- Check logs for debugging information 