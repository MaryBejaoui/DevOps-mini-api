from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import logging
import sys

# Prometheus metrics
from prometheus_fastapi_instrumentator import Instrumentator

# OpenTelemetry tracing
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)

# Initialize FastAPI app
app = FastAPI(
    title="Task Manager API",
    description="A simple task management API with DevOps best practices",
    version="1.0.0"
)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Instrument FastAPI with Prometheus
Instrumentator().instrument(app).expose(app)

# Pydantic models
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Task title")
    description: Optional[str] = Field(None, max_length=500, description="Task description")
    completed: bool = Field(default=False, description="Task completion status")

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True

# In-memory storage
tasks_db: List[dict] = []
task_id_counter = 1

# API Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return {
        "message": "Welcome to Task Manager API",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics"
    }

@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    with tracer.start_as_current_span("health_check"):
        logger.info("Health check performed")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "task-manager-api"
        }

@app.get("/tasks", response_model=List[Task], tags=["Tasks"])
async def get_tasks():
    """Get all tasks"""
    with tracer.start_as_current_span("get_all_tasks"):
        logger.info(f"GET /tasks - Retrieved {len(tasks_db)} tasks")
        return tasks_db

@app.get("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def get_task(task_id: int):
    """Get a specific task by ID"""
    with tracer.start_as_current_span("get_task_by_id"):
        logger.info(f"GET /tasks/{task_id}")
        
        task = next((task for task in tasks_db if task["id"] == task_id), None)
        
        if not task:
            logger.error(f"Task {task_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )
        
        return task

@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
async def create_task(task: TaskCreate):
    """Create a new task"""
    global task_id_counter
    
    with tracer.start_as_current_span("create_task"):
        new_task = {
            "id": task_id_counter,
            "title": task.title,
            "description": task.description,
            "completed": task.completed,
            "created_at": datetime.utcnow().isoformat()
        }
        
        tasks_db.append(new_task)
        logger.info(f"POST /tasks - Created task {task_id_counter}: {task.title}")
        task_id_counter += 1
        
        return new_task

@app.put("/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def update_task(task_id: int, task_update: TaskCreate):
    """Update an existing task"""
    with tracer.start_as_current_span("update_task"):
        logger.info(f"PUT /tasks/{task_id}")
        
        task = next((task for task in tasks_db if task["id"] == task_id), None)
        
        if not task:
            logger.error(f"Task {task_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )
        
        task["title"] = task_update.title
        task["description"] = task_update.description
        task["completed"] = task_update.completed
        
        logger.info(f"Task {task_id} updated successfully")
        return task

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"])
async def delete_task(task_id: int):
    """Delete a task"""
    with tracer.start_as_current_span("delete_task"):
        logger.info(f"DELETE /tasks/{task_id}")
        
        task_index = next((i for i, task in enumerate(tasks_db) if task["id"] == task_id), None)
        
        if task_index is None:
            logger.error(f"Task {task_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )
        
        tasks_db.pop(task_index)
        logger.info(f"Task {task_id} deleted successfully")
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)