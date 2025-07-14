import json
from datetime import datetime, timedelta, timezone

from extensions import db
from models.reflection import Reflection
from models.user import User


class TestReflectionCreateAPI:
    """Test cases for reflection creation API."""

    def test_create_reflection_weekly_success(self, client, db_session, auth_headers, user):
        """Test successful weekly reflection creation."""
        data = {"content": "This is my weekly reflection", "reflection_type": "weekly"}

        response = client.post(
            "/api/reflections/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        assert result["content"] == "This is my weekly reflection"
        assert result["reflection_type"] == "weekly"
        assert result["user_id"] == user.id
        assert "id" in result
        assert "period_start" in result
        assert "period_end" in result

    def test_create_reflection_monthly_success(self, client, db_session, auth_headers, user):
        """Test successful monthly reflection creation."""
        data = {"content": "This is my monthly reflection", "reflection_type": "monthly"}

        response = client.post(
            "/api/reflections/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        assert result["content"] == "This is my monthly reflection"
        assert result["reflection_type"] == "monthly"
        assert result["user_id"] == user.id

    def test_create_reflection_missing_content(self, client, db_session, auth_headers):
        """Test reflection creation with missing content."""
        data = {"reflection_type": "weekly"}

        response = client.post(
            "/api/reflections/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Content and reflection type are required" in result["error"]

    def test_create_reflection_missing_type(self, client, db_session, auth_headers):
        """Test reflection creation with missing reflection type."""
        data = {"content": "Test reflection"}

        response = client.post(
            "/api/reflections/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Content and reflection type are required" in result["error"]

    def test_create_reflection_invalid_type(self, client, db_session, auth_headers):
        """Test reflection creation with invalid reflection type."""
        data = {"content": "Test reflection", "reflection_type": "daily"}

        response = client.post(
            "/api/reflections/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Invalid reflection type" in result["error"]

    def test_create_reflection_no_auth(self, client, db_session):
        """Test reflection creation without authentication."""
        data = {"content": "Test reflection", "reflection_type": "weekly"}

        response = client.post("/api/reflections/", data=json.dumps(data), content_type="application/json")

        assert response.status_code == 401


class TestReflectionListAPI:
    """Test cases for reflection list API."""

    def test_get_reflections_success(self, client, db_session, auth_headers, user):
        """Test successful retrieval of reflections."""
        # Create test reflections
        reflection1 = Reflection(
            user_id=user.id,
            content="Weekly reflection 1",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        reflection2 = Reflection(
            user_id=user.id,
            content="Monthly reflection 1",
            reflection_type="monthly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(reflection1)
        db_session.add(reflection2)
        db_session.commit()

        response = client.get("/api/reflections/", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 2
        assert result["pagination"]["total"] == 2
        assert result["pagination"]["page"] == 1

    def test_get_reflections_filtered_by_type(self, client, db_session, auth_headers, user):
        """Test getting reflections filtered by type."""
        # Create test reflections
        reflection1 = Reflection(
            user_id=user.id,
            content="Weekly reflection",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        reflection2 = Reflection(
            user_id=user.id,
            content="Monthly reflection",
            reflection_type="monthly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db_session.add(reflection1)
        db_session.add(reflection2)
        db_session.commit()

        # Test weekly filter
        response = client.get("/api/reflections/?type=weekly", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 1
        assert result["reflections"][0]["reflection_type"] == "weekly"

        # Test monthly filter
        response = client.get("/api/reflections/?type=monthly", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 1
        assert result["reflections"][0]["reflection_type"] == "monthly"

    def test_get_reflections_pagination(self, client, db_session, auth_headers, user):
        """Test reflection pagination."""
        # Create multiple reflections
        for i in range(15):
            reflection = Reflection(
                user_id=user.id,
                content=f"Reflection {i}",
                reflection_type="weekly",
                period_start=datetime.now(timezone.utc),
                period_end=datetime.now(timezone.utc) + timedelta(days=7),
            )
            db_session.add(reflection)
        db_session.commit()

        # Test first page
        response = client.get("/api/reflections/?page=1&per_page=10", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 10
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 10
        assert result["pagination"]["total"] == 15
        assert result["pagination"]["pages"] == 2

        # Test second page
        response = client.get("/api/reflections/?page=2&per_page=10", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 5
        assert result["pagination"]["page"] == 2

    def test_get_reflections_no_auth(self, client, db_session):
        """Test getting reflections without authentication."""
        response = client.get("/api/reflections/")
        assert response.status_code == 401

    def test_get_reflections_empty(self, client, db_session, auth_headers, user):
        """Test getting reflections when none exist."""
        response = client.get("/api/reflections/", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["reflections"]) == 0
        assert result["pagination"]["total"] == 0


class TestReflectionDetailAPI:
    """Test cases for reflection detail API."""

    def test_get_reflection_success(self, client, db_session, auth_headers, user):
        """Test successful retrieval of a specific reflection."""
        reflection = Reflection(
            user_id=user.id,
            content="Test reflection for detail",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(reflection)
        db_session.commit()

        response = client.get(f"/api/reflections/{reflection.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["content"] == "Test reflection for detail"
        assert result["reflection_type"] == "weekly"
        assert result["id"] == reflection.id

    def test_get_reflection_not_found(self, client, db_session, auth_headers):
        """Test getting non-existent reflection."""
        response = client.get("/api/reflections/99999", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Reflection not found" in result["error"]

    def test_get_reflection_unauthorized(self, client, db_session, auth_headers, user):
        """Test getting reflection from another user."""
        # Create reflection for a different user
        other_user = User(email="other@example.com", first_name="Other", last_name="User")
        other_user.set_password("password123")
        db_session.add(other_user)
        db_session.commit()

        reflection = Reflection(
            user_id=other_user.id,
            content="Other user's reflection",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(reflection)
        db_session.commit()

        response = client.get(f"/api/reflections/{reflection.id}", headers=auth_headers)

        assert response.status_code == 404  # Should not find it due to user filtering
        result = json.loads(response.data)
        assert "Reflection not found" in result["error"]

    def test_get_reflection_no_auth(self, client, db_session):
        """Test getting reflection without authentication."""
        response = client.get("/api/reflections/1")
        assert response.status_code == 401


class TestReflectionDeleteAPI:
    """Test cases for reflection deletion API."""

    def test_delete_reflection_success(self, client, db_session, auth_headers, user):
        """Test successful reflection deletion."""
        reflection = Reflection(
            user_id=user.id,
            content="Reflection to delete",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(reflection)
        db_session.commit()

        response = client.delete(f"/api/reflections/{reflection.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert "Reflection deleted successfully" in result["message"]

        # Verify reflection was deleted
        deleted_reflection = db.session.get(Reflection, reflection.id)
        assert deleted_reflection is None

    def test_delete_reflection_not_found(self, client, db_session, auth_headers):
        """Test deleting non-existent reflection."""
        response = client.delete("/api/reflections/99999", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Reflection not found" in result["error"]

    def test_delete_reflection_unauthorized(self, client, db_session, auth_headers, user):
        """Test deleting reflection from another user."""
        # Create reflection for a different user
        other_user = User(email="other@example.com", first_name="Other", last_name="User")
        other_user.set_password("password123")
        db_session.add(other_user)
        db_session.commit()

        reflection = Reflection(
            user_id=other_user.id,
            content="Other user's reflection",
            reflection_type="weekly",
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db_session.add(reflection)
        db_session.commit()

        response = client.delete(f"/api/reflections/{reflection.id}", headers=auth_headers)

        assert response.status_code == 404  # Should not find it due to user filtering
        result = json.loads(response.data)
        assert "Reflection not found" in result["error"]

    def test_delete_reflection_no_auth(self, client, db_session):
        """Test deleting reflection without authentication."""
        response = client.delete("/api/reflections/1")
        assert response.status_code == 401
