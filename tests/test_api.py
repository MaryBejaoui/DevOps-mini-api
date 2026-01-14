import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Welcome to Task Manager API"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "timestamp" in response.json()

def test_get_empty_tasks():
    """Test getting tasks when none exist"""
    # Clear tasks first
    response = client.get("/tasks")
    for task in response.json():
        client.delete(f"/tasks/{task['id']}")
    
    response = client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []

def test_create_task():
    """Test creating a new task"""
    task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "completed": False
    }
    
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 201
    assert response.json()["title"] == task_data["title"]
    assert response.json()["description"] == task_data["description"]
    assert "id" in response.json()
    assert "created_at" in response.json()

def test_create_task_without_description():
    """Test creating a task without description"""
    task_data = {
        "title": "Task without description",
        "completed": False
    }
    
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 201
    assert response.json()["title"] == task_data["title"]
    assert response.json()["description"] is None

def test_create_task_validation_error():
    """Test creating a task with invalid data"""
    task_data = {
        "title": "",  # Empty title should fail
        "completed": False
    }
    
    response = client.post("/tasks", json=task_data)
    assert response.status_code == 422

def test_get_task_by_id():
    """Test getting a specific task"""
    # Create a task first
    task_data = {
        "title": "Get Task Test",
        "description": "Task to test GET by ID",
        "completed": False
    }
    create_response = client.post("/tasks", json=task_data)
    task_id = create_response.json()["id"]
    
    # Get the task
    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["title"] == task_data["title"]

def test_get_nonexistent_task():
    """Test getting a task that doesn't exist"""
    response = client.get("/tasks/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_update_task():
    """Test updating a task"""
    # Create a task first
    task_data = {
        "title": "Original Title",
        "description": "Original description",
        "completed": False
    }
    create_response = client.post("/tasks", json=task_data)
    task_id = create_response.json()["id"]
    
    # Update the task
    updated_data = {
        "title": "Updated Title",
        "description": "Updated description",
        "completed": True
    }
    response = client.put(f"/tasks/{task_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["title"] == updated_data["title"]
    assert response.json()["completed"] == True

def test_update_nonexistent_task():
    """Test updating a task that doesn't exist"""
    task_data = {
        "title": "Update Test",
        "description": "This won't work",
        "completed": False
    }
    response = client.put("/tasks/99999", json=task_data)
    assert response.status_code == 404

def test_delete_task():
    """Test deleting a task"""
    # Create a task first
    task_data = {
        "title": "Task to Delete",
        "description": "Will be deleted",
        "completed": False
    }
    create_response = client.post("/tasks", json=task_data)
    task_id = create_response.json()["id"]
    
    # Delete the task
    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 204
    
    # Verify it's deleted
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_task():
    """Test deleting a task that doesn't exist"""
    response = client.delete("/tasks/99999")
    assert response.status_code == 404

def test_metrics_endpoint():
    """Test that Prometheus metrics endpoint exists"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "http_request" in response.text