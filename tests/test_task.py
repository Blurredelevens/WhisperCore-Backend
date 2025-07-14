import json
from unittest.mock import Mock, patch

from models.memory import Memory


class TestTaskAPI:
    """Test cases for task API."""

    @patch("routes.task.celery.send_task")
    def test_create_task_with_chat_id_and_mood_emoji(self, mock_send_task, client, db_session, auth_headers, user):
        """Test creating a task with chat_id and mood_emoji."""
        # Mock the Celery task
        mock_task = Mock()
        mock_task.id = "test-task-id-123"
        mock_send_task.return_value = mock_task

        data = {"content": "Test task content", "chat_id": "test_chat_123", "mood_emoji": "😊"}

        response = client.post(
            "/api/task/query",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 202  # Accepted for async processing
        result = json.loads(response.data)
        assert result["message"] == "Task started successfully"
        assert result["status"] == "processing"
        assert "task_id" in result

        # Verify memory was created with correct chat_id and mood_emoji
        # Get the most recent memory for this user
        memory = Memory.query.filter_by(user_id=user.id).order_by(Memory.created_at.desc()).first()
        assert memory is not None
        assert memory.chat_id == "test_chat_123"
        assert memory.mood_emoji == "😊"

    @patch("routes.task.celery.send_task")
    def test_create_task_without_chat_id_and_mood_emoji(self, mock_send_task, client, db_session, auth_headers, user):
        """Test creating a task without chat_id and mood_emoji."""
        # Mock the Celery task
        mock_task = Mock()
        mock_task.id = "test-task-id-456"
        mock_send_task.return_value = mock_task

        data = {"content": "Test task content without chat_id"}

        response = client.post(
            "/api/task/query",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 202  # Accepted for async processing
        result = json.loads(response.data)
        assert result["message"] == "Task started successfully"
        assert result["status"] == "processing"
        assert "task_id" in result

        # Verify memory was created without chat_id and mood_emoji
        # Get the most recent memory for this user
        memory = Memory.query.filter_by(user_id=user.id).order_by(Memory.created_at.desc()).first()
        assert memory is not None
        assert memory.chat_id is None
        assert memory.mood_emoji is None

    def test_create_task_missing_content(self, client, db_session, auth_headers):
        """Test creating a task without content."""
        data = {"chat_id": "test_chat_123", "mood_emoji": "😊"}

        response = client.post(
            "/api/task/query",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Missing 'content' in request body" in result["error"]

    def test_create_task_no_auth(self, client, db_session):
        """Test creating a task without authentication."""
        data = {"content": "Test task content", "chat_id": "test_chat_123", "mood_emoji": "😊"}

        response = client.post("/api/task/query", data=json.dumps(data), content_type="application/json")

        assert response.status_code == 401
