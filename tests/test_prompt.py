import json

from extensions import db
from models.prompt import Prompt
from models.user import User


class TestPromptListAPI:
    """Test cases for prompt list API."""

    def test_get_prompts_success(self, client, db_session, auth_headers, user):
        """Test successful retrieval of all prompts."""
        # Create some test prompts
        prompt1 = Prompt(user_id=user.id, text="Test prompt 1", is_active=True)
        prompt2 = Prompt(user_id=user.id, text="Test prompt 2", is_active=False)
        db_session.add(prompt1)
        db_session.add(prompt2)
        db_session.commit()

        response = client.get("/api/prompts/", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result) == 2
        assert any(p["text"] == "Test prompt 1" for p in result)
        assert any(p["text"] == "Test prompt 2" for p in result)

    def test_get_prompts_no_auth(self, client, db_session):
        """Test getting prompts without authentication."""
        response = client.get("/api/prompts/")
        assert response.status_code == 401

    def test_create_prompt_admin_success(self, client, db_session, admin_auth_headers, admin_user):
        """Test successful prompt creation by admin."""
        data = {"text": "New admin prompt", "is_active": True}

        response = client.post(
            "/api/prompts/",
            data=json.dumps(data),
            content_type="application/json",
            headers=admin_auth_headers,
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        assert result["text"] == "New admin prompt"
        assert result["is_active"] is True
        assert "id" in result

    def test_create_prompt_non_admin_fails(self, client, db_session, auth_headers, user):
        """Test prompt creation fails for non-admin users."""
        data = {"text": "New prompt", "is_active": True}

        response = client.post(
            "/api/prompts/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 403
        result = json.loads(response.data)
        assert "Admin privileges required" in result["error"]

    def test_create_prompt_no_data(self, client, db_session, admin_auth_headers):
        """Test prompt creation with no data."""
        response = client.post(
            "/api/prompts/",
            data=json.dumps({}),
            content_type="application/json",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400  # text field is required
        result = json.loads(response.data)
        assert "error" in result


class TestPromptDetailAPI:
    """Test cases for prompt detail API."""

    def test_get_prompt_success(self, client, db_session, auth_headers, user):
        """Test successful retrieval of a specific prompt."""
        prompt = Prompt(user_id=user.id, text="Test prompt for detail", is_active=True)
        db_session.add(prompt)
        db_session.commit()

        response = client.get(f"/api/prompts/{prompt.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["text"] == "Test prompt for detail"
        assert result["id"] == prompt.id

    def test_get_prompt_not_found(self, client, db_session, auth_headers):
        """Test getting non-existent prompt."""
        response = client.get("/api/prompts/99999", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Prompt not found" in result["error"]

    def test_update_prompt_admin_success(self, client, db_session, admin_auth_headers, admin_user):
        """Test successful prompt update by admin."""
        prompt = Prompt(user_id=admin_user.id, text="Original prompt", is_active=True)
        db_session.add(prompt)
        db_session.commit()

        data = {"text": "Updated prompt", "is_active": False}

        response = client.put(
            f"/api/prompts/{prompt.id}",
            data=json.dumps(data),
            content_type="application/json",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["text"] == "Updated prompt"
        assert result["is_active"] is False

    def test_update_prompt_non_admin_fails(self, client, db_session, auth_headers, user):
        """Test prompt update fails for non-admin users."""
        prompt = Prompt(user_id=user.id, text="Original prompt", is_active=True)
        db_session.add(prompt)
        db_session.commit()

        data = {"text": "Updated prompt"}

        response = client.put(
            f"/api/prompts/{prompt.id}",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 403
        result = json.loads(response.data)
        assert "Admin privileges required" in result["error"]

    def test_update_prompt_not_found(self, client, db_session, admin_auth_headers):
        """Test updating non-existent prompt."""
        data = {"text": "Updated prompt"}

        response = client.put(
            "/api/prompts/99999",
            data=json.dumps(data),
            content_type="application/json",
            headers=admin_auth_headers,
        )

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Prompt not found" in result["error"]

    def test_delete_prompt_admin_success(self, client, db_session, admin_auth_headers, admin_user):
        print("admin_user.id in test:", admin_user.id)
        db_session.rollback()  # Ensure clean state
        prompt = Prompt(user_id=admin_user.id, text="Prompt to delete", is_active=True)
        db_session.add(prompt)
        db_session.commit()

        response = client.delete(f"/api/prompts/{prompt.id}", headers=admin_auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert "Prompt deleted" in result["message"]

        # Verify prompt was deleted
        deleted_prompt = db.session.get(Prompt, prompt.id)
        assert deleted_prompt is None

    def test_delete_prompt_other_admin_fails(self, client, db_session, admin_auth_headers, admin_user):
        """Test that admin cannot delete prompt created by another user."""
        # Create a different user
        other_user = User(email="other@example.com", first_name="Other", last_name="User")
        other_user.set_password("password123")
        db_session.add(other_user)
        db_session.commit()

        # Create prompt by other user
        prompt = Prompt(user_id=other_user.id, text="Prompt to delete", is_active=True)
        db_session.add(prompt)
        db_session.commit()

        # Try to delete with admin user
        response = client.delete(f"/api/prompts/{prompt.id}", headers=admin_auth_headers)

        assert response.status_code == 403
        result = json.loads(response.data)
        assert "Unauthorized" in result["error"]

    def test_delete_prompt_not_found(self, client, db_session, admin_auth_headers):
        """Test deleting non-existent prompt."""
        response = client.delete("/api/prompts/99999", headers=admin_auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Prompt not found" in result["error"]


class TestTodayPromptAPI:
    """Test cases for today prompt API."""

    def test_get_today_prompt_success(self, client, db_session, auth_headers, user):
        """Test successful retrieval of today's prompt."""
        # Create a prompt for today
        from datetime import datetime, timezone

        prompt = Prompt(user_id=user.id, text="Today's prompt", is_active=True)
        prompt.created_at = datetime.now(timezone.utc)
        db_session.add(prompt)
        db_session.commit()

        response = client.get("/api/prompts/today", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["prompt"] == "Today's prompt"
        assert "prompt_id" in result
        assert "prompt_date" in result

    def test_get_today_prompt_not_found(self, client, db_session, auth_headers):
        """Test getting today's prompt when none exists."""
        response = client.get("/api/prompts/today", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert result["prompt"] is None
        assert "No prompt set for today" in result["message"]

    def test_get_today_prompt_no_auth(self, client, db_session):
        """Test getting today's prompt without authentication."""
        response = client.get("/api/prompts/today")
        assert response.status_code == 401
