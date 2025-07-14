from unittest.mock import Mock, patch


class TestSummaryAPI:

    @patch("routes.summary.get_llm_client")
    def test_weekly_summary_success(self, mock_get_llm_client, client):
        """Test successful weekly summary generation using API for setup."""
        # Mock the LLM client first, before any API calls
        mock_llm_instance = Mock()
        mock_llm_instance.generate_with_long_polling.return_value = "This is a weekly summary of your memories."
        mock_get_llm_client.return_value = mock_llm_instance

        # Register user
        register_data = {
            "email": "weekly_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        # Login
        login_data = {"email": "weekly_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memories via API
        for i in range(5):
            mem_data = {
                "content": f"Memory content {i}",
                "model_response": f"Model response {i}",
                "chat_id": f"chat_{i}",
                "mood_emoji": "😊",
            }
            resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
            assert resp.status_code == 201
        # Call summary endpoint
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 200
        result = response.json
        assert result["summary_type"] == "weekly"
        assert "summary" in result
        assert "This is a weekly summary" in str(result["summary"])

    @patch("routes.summary.get_llm_client")
    def test_monthly_summary_success(self, mock_get_llm_client, client):
        """Test successful monthly summary generation using API for setup."""
        # Mock the LLM client first, before any API calls
        mock_llm_instance = Mock()
        mock_llm_instance.generate_with_long_polling.return_value = "This is a monthly summary of your memories."
        mock_get_llm_client.return_value = mock_llm_instance

        # Register user
        register_data = {
            "email": "monthly_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        # Login
        login_data = {"email": "monthly_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memories via API
        for i in range(5):
            mem_data = {
                "content": f"Memory content {i}",
                "model_response": f"Model response {i}",
                "chat_id": f"chat_{i}",
                "mood_emoji": "😊",
            }
            resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
            assert resp.status_code == 201
        # Call summary endpoint
        response = client.get("/api/summary/monthly", headers=auth_headers)
        assert response.status_code == 200
        result = response.json
        assert result["summary_type"] == "monthly"
        assert "summary" in result
        assert "This is a monthly summary" in str(result["summary"])

    def test_summary_invalid_type(self, client):
        """Test summary with invalid summary type."""
        # Register and login user
        register_data = {
            "email": "invalid_type_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "invalid_type_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/summary/daily", headers=auth_headers)
        assert response.status_code == 400
        result = response.json
        assert "Invalid summary type" in result["error"]

    def test_summary_no_memories(self, client):
        """Test summary when no memories exist."""
        # Register and login user
        register_data = {
            "email": "no_memories_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "no_memories_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 404
        result = response.json
        assert "No memories found for summary" in result["error"]

    def test_summary_no_auth(self, client):
        """Test summary without authentication."""
        response = client.get("/api/summary/weekly")
        assert response.status_code == 401

    @patch("routes.summary.get_llm_client")
    def test_summary_with_string_response(self, mock_get_llm_client, client):
        """Test summary with LLM returning string response using API for setup."""
        # Mock the LLM client first, before any API calls
        mock_llm_instance = Mock()
        mock_llm_instance.generate_with_long_polling.return_value = "String summary response"
        mock_get_llm_client.return_value = mock_llm_instance

        register_data = {
            "email": "string_response_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "string_response_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        mem_data = {
            "content": "Test memory content",
            "model_response": "Test model response",
            "chat_id": "test_chat",
            "mood_emoji": "😊",
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 200
        result = response.json
        assert "String summary response" in str(result["summary"])

    @patch("routes.summary.get_llm_client")
    def test_summary_with_dict_response(self, mock_get_llm_client, client):
        """Test summary with LLM returning dict response using API for setup."""
        # Mock the LLM client first, before any API calls
        mock_llm_instance = Mock()
        mock_llm_instance.generate_with_long_polling.return_value = "Dict summary response"
        mock_get_llm_client.return_value = mock_llm_instance

        # Register and login user
        register_data = {
            "email": "dict_response_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "dict_response_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memory via API
        mem_data = {
            "content": "Test memory content",
            "model_response": "Test model response",
            "chat_id": "test_chat",
            "mood_emoji": "😊",
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 200
        result = response.json
        assert "Dict summary response" in str(result["summary"])

    def test_summary_memory_decryption_failure(self, client):
        """Test summary when memory decryption fails."""
        # Register and login user
        register_data = {
            "email": "decryption_failure_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "decryption_failure_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memory with invalid encrypted data
        mem_data = {
            "content": "Test memory content",
            "model_response": "invalid_encrypted_data",
            "chat_id": "test_chat",
            "mood_emoji": "😊",
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        # The summary should still work but skip the invalid memory
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 200
        result = response.json
        assert "summary" in result

    @patch("routes.summary.get_llm_client")
    def test_summary_prompt_building(self, mock_get_llm_client, client):
        """Test that the summary prompt is built correctly."""
        # Mock the LLM client first, before any API calls
        mock_llm_instance = Mock()
        mock_llm_instance.generate_with_long_polling.return_value = "Test summary"
        mock_get_llm_client.return_value = mock_llm_instance

        # Register and login user
        register_data = {
            "email": "prompt_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123",
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "prompt_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memory via API
        mem_data = {
            "content": "Test memory content",
            "model_response": "Test model response",
            "chat_id": "test_chat",
            "mood_emoji": "😊",
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        # Call summary endpoint
        response = client.get("/api/summary/weekly", headers=auth_headers)
        assert response.status_code == 200
        # Verify LLM was called
        mock_llm_instance.generate_with_long_polling.assert_called_once()
