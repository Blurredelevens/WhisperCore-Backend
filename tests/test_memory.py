import json

from models.memory import Memory


class TestMemoryCRUD:
    """Test cases for memory CRUD operations."""

    def test_create_memory_success(self, client, db_session, auth_headers, user):
        """Test successful memory creation."""
        data = {"content": "This is a test memory content.", "model_response": "Test model response"}

        response = client.post(
            "/api/memories/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        assert result["memory"]["content"] == "This is a test memory content."
        assert result["memory"]["user_id"] == user.id

    def test_create_memory_no_auth(self, client, db_session):
        """Test memory creation without authentication."""
        data = {"content": "This is a test memory content.", "model_response": "Test model response"}

        response = client.post("/api/memories/", data=json.dumps(data), content_type="application/json")

        assert response.status_code == 401

    def test_create_memory_empty_content(self, client, db_session, auth_headers):
        """Test memory creation with empty content."""
        data = {"content": "", "model_response": "Test model response"}

        response = client.post(
            "/api/memories/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Content cannot be empty" in result["error"]

    def test_get_memories_success(self, client, db_session, auth_headers, user, memory):
        """Test successful memories retrieval."""
        response = client.get("/api/memories/", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["memories"]) >= 1
        assert result["memories"][0]["content"] == "This is a test memory content."

    def test_get_memories_pagination(self, client, db_session, auth_headers, user):
        """Test memories retrieval with pagination."""
        # Create multiple memories
        for i in range(5):
            memory = Memory(user_id=user.id, chat_id=f"chat-{i}")
            memory.set_content(f"Memory {i+1}", user.encryption_key.encode())
            db_session.add(memory)
        db_session.commit()

        response = client.get("/api/memories/?page=1&per_page=3", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert len(result["memories"]) == 3
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["per_page"] == 3

    def test_get_memory_by_id_success(self, client, db_session, auth_headers, memory):
        """Test successful single memory retrieval."""
        response = client.get(f"/api/memories/{memory.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["memory"]["id"] == memory.id
        assert result["memory"]["content"] == "This is a test memory content."

    def test_get_memory_by_id_not_found(self, client, db_session, auth_headers):
        """Test memory retrieval with non-existent ID."""
        response = client.get("/api/memories/99999", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Memory not found" in result["error"]

    def test_get_memory_by_id_unauthorized(self, client, db_session, auth_headers, memory):
        """Test memory retrieval for another user's memory."""
        # Create another user and memory
        from models.user import User

        other_user = User(email="other@example.com", first_name="Other", last_name="User")
        other_user.set_password("password123")
        db_session.add(other_user)
        db_session.commit()

        other_memory = Memory(user_id=other_user.id, chat_id="other-chat")
        other_memory.set_content("Other user's memory", other_user.encryption_key.encode())
        db_session.add(other_memory)
        db_session.commit()

        response = client.get(f"/api/memories/{other_memory.id}", headers=auth_headers)

        assert response.status_code == 404  # Should not find other user's memory

    def test_update_memory_success(self, client, db_session, auth_headers, memory):
        """Test successful memory update."""
        data = {"content": "Updated memory content.", "model_response": "Test model response"}

        response = client.put(
            f"/api/memories/{memory.id}",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["message"] == "Memory updated successfully"
        assert result["memory"]["content"] == "Updated memory content."

    def test_update_memory_not_found(self, client, db_session, auth_headers):
        """Test memory update with non-existent ID."""
        data = {"content": "Updated content.", "model_response": "Test model response"}

        response = client.put(
            "/api/memories/99999",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Memory not found" in result["error"]

    def test_delete_memory_success(self, client, db_session, auth_headers, memory):
        """Test successful memory deletion."""
        response = client.delete(f"/api/memories/{memory.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["message"] == "Memory deleted successfully"

    def test_delete_memory_not_found(self, client, db_session, auth_headers):
        """Test memory deletion with non-existent ID."""
        response = client.delete("/api/memories/99999", headers=auth_headers)

        assert response.status_code == 404
        result = json.loads(response.data)
        assert "Memory not found" in result["error"]


class TestMemoryEncryption:
    """Test cases for memory encryption."""

    def test_memory_encryption(self, client, db_session, auth_headers, user):
        """Test that memory content is properly encrypted."""
        sensitive_content = "This is very sensitive information that should be encrypted."
        data = {"content": sensitive_content, "model_response": "Test model response"}

        response = client.post(
            "/api/memories/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 201
        result = json.loads(response.data)
        memory_id = result["memory"]["id"]

        # Check that the content is encrypted in the database
        memory = db_session.query(Memory).filter_by(id=memory_id).first()
        assert memory.encrypted_content != sensitive_content.encode()  # Should be encrypted
        assert (
            memory._decrypt(memory.encrypted_content, user.encryption_key.encode()) == sensitive_content
        )  # Should decrypt correctly

    def test_memory_decryption(self, client, db_session, auth_headers, user):
        """Test that memory content can be properly decrypted."""
        original_content = "Test content for decryption."

        # Create memory
        memory = Memory(user_id=user.id, chat_id="decrypt-test")
        memory.set_content(original_content, user.encryption_key.encode())
        db_session.add(memory)
        db_session.commit()

        # Retrieve memory via API
        response = client.get(f"/api/memories/{memory.id}", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["memory"]["content"] == original_content  # Should be decrypted


class TestMemoryValidation:
    """Test cases for memory validation."""

    def test_memory_content_type_validation(self, client, db_session, auth_headers):
        """Test memory content type validation."""
        data = {"content": 123, "model_response": "Test model response"}  # Invalid type

        response = client.post(
            "/api/memories/",
            data=json.dumps(data),
            content_type="application/json",
            headers=auth_headers,
        )

        assert response.status_code == 400
        result = json.loads(response.data)
        assert "Content must be a string" in result["error"]

    def test_get_memories_grouped_by_chat_id(self, client, db_session, auth_headers, user):
        """Test getting memories grouped by chat_id."""
        # Create memories with different chat_ids
        encryption_key = user.encryption_key.encode()

        # Create memories for chat_id "chat1"
        for i in range(2):
            memory = Memory(user_id=user.id, chat_id="chat1", mood_emoji="😊")
            memory.set_content(f"Memory {i} for chat1", encryption_key)
            memory.set_model_response(f"Response {i} for chat1", encryption_key)
            db_session.add(memory)

        # Create memories for chat_id "chat2"
        for i in range(3):
            memory = Memory(user_id=user.id, chat_id="chat2", mood_emoji="😢")
            memory.set_content(f"Memory {i} for chat2", encryption_key)
            memory.set_model_response(f"Response {i} for chat2", encryption_key)
            db_session.add(memory)

        # Create a memory without chat_id
        memory = Memory(user_id=user.id, mood_emoji="😐")
        memory.set_content("Memory without chat_id", encryption_key)
        memory.set_model_response("Response without chat_id", encryption_key)
        db_session.add(memory)

        db_session.commit()

        # Test grouped response
        response = client.get("/api/memories/?group_by_chat_id=true", headers=auth_headers)

        assert response.status_code == 200
        result = json.loads(response.data)

        assert result["grouped_by_chat_id"] is True
        assert len(result["memories"]) == 3  # 3 groups: chat1, chat2, no_chat_id
        assert result["total_memories"] == 6

        # Check that memories are grouped correctly
        chat_ids = [group["chat_id"] for group in result["memories"]]
        assert "chat1" in chat_ids
        assert "chat2" in chat_ids
        assert None in chat_ids

        # Check counts
        for group in result["memories"]:
            if group["chat_id"] == "chat1":
                assert group["count"] == 2
            elif group["chat_id"] == "chat2":
                assert group["count"] == 3
            elif group["chat_id"] is None:
                assert group["count"] == 1

    def test_get_memories_by_chat_id_success(self, client, user, auth_headers):
        """Test successful retrieval of memories by chat ID."""
        # Create memories with different chat IDs
        memory_data_1 = {
            "content": "Memory content 1",
            "model_response": "Model response 1",
            "chat_id": "chat1",
            "mood_emoji": "😊",
        }
        memory_data_2 = {
            "content": "Memory content 2",
            "model_response": "Model response 2",
            "chat_id": "chat1",
            "mood_emoji": "😢",
        }
        memory_data_3 = {
            "content": "Memory content 3",
            "model_response": "Model response 3",
            "chat_id": "chat2",
            "mood_emoji": "😊",
        }

        # Create memories
        client.post("/api/memories/", json=memory_data_1, headers=auth_headers)
        client.post("/api/memories/", json=memory_data_2, headers=auth_headers)
        client.post("/api/memories/", json=memory_data_3, headers=auth_headers)

        # Get memories for chat_id "chat1"
        response = client.get("/api/memories/chats/chat1", headers=auth_headers)
        assert response.status_code == 200

        memories = response.json
        assert len(memories) == 2
        assert all(memory["chat_id"] == "chat1" for memory in memories)
        assert any(memory["content"] == "Memory content 1" for memory in memories)
        assert any(memory["content"] == "Memory content 2" for memory in memories)

        # Verify memory structure
        memory = memories[0]
        assert "id" in memory
        assert "content" in memory
        assert "model_response" in memory
        assert "chat_id" in memory
        assert "mood_emoji" in memory
        assert "created_at" in memory
        assert "updated_at" in memory

    def test_get_memories_by_chat_id_empty(self, client, user, auth_headers):
        """Test getting memories for a chat ID that doesn't exist."""
        response = client.get("/api/memories/chats/nonexistent", headers=auth_headers)
        assert response.status_code == 200
        assert response.json == []

    def test_get_memories_by_chat_id_no_auth(self, client):
        """Test getting memories by chat ID without authentication."""
        response = client.get("/api/memories/chats/chat1")
        assert response.status_code == 401
