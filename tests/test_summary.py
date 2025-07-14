from unittest.mock import Mock, patch


class TestSummaryAPI:
    """Test cases for summary API."""
    
    @patch('routes.summary.LLMService')
    def test_weekly_summary_success(self, mock_llm_service, client):
        """Test successful weekly summary generation using API for setup."""
        # 1. Register user
        register_data = {
            "email": "weekly_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
        }
        resp = client.post("/api/auth/register", json=register_data)
        print(f"Registration response status: {resp.status_code}")
        print(f"Registration response body: {resp.get_data(as_text=True)}")
        assert resp.status_code == 201
        # 2. Login
        login_data = {"email": "weekly_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200      
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # 3. Create memories via API
        for i in range(3):
            mem_data = {
                "content": f"Memory content {i}",
                "model_response": f"Model response {i}",
                "chat_id": f"chat_{i}",
                "mood_emoji": "😊"
            }
            resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
            assert resp.status_code == 201
        # 4. Mock LLM service response
        mock_llm_instance = Mock()
        mock_llm_instance.process_query.return_value = {
            'data': {
                'text': 'This is a weekly summary of your memories.'
            }
        }
        mock_llm_service.return_value = mock_llm_instance
        # 5. Call summary endpoint
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json
        assert result["summary_type"] == "weekly"
        assert "summary" in result
        assert "This is a weekly summary" in str(result["summary"])
    
    @patch('routes.summary.LLMService')
    def test_monthly_summary_success(self, mock_llm_service, client):
        """Test successful monthly summary generation using API for setup."""
        # Register user
        register_data = {
            "email": "monthly_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
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
                "mood_emoji": "😊"
            }
            resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
            assert resp.status_code == 201
        # Mock LLM service response
        mock_llm_instance = Mock()
        mock_llm_instance.process_query.return_value = {
            'data': {
                'text': 'This is a monthly summary of your memories.'
            }
        }
        mock_llm_service.return_value = mock_llm_instance
        # Call summary endpoint
        response = client.get(
            "/api/summary/monthly",
            headers=auth_headers
        )
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
            "passphrase": "testpassphrase123"
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "invalid_type_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get(
            "/api/summary/daily",
            headers=auth_headers
        )
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
            "passphrase": "testpassphrase123"
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "no_memories_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 404
        result = response.json
        assert "No memories found for summary" in result["error"]
    
    def test_summary_no_auth(self, client):
        """Test summary without authentication."""
        response = client.get("/api/summary/weekly")
        assert response.status_code == 401
    
    @patch('routes.summary.LLMService')
    def test_summary_with_string_response(self, mock_llm_service, client):
        """Test summary with LLM returning string response using API for setup."""
       
        register_data = {
            "email": "string_response_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
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
            "mood_emoji": "😊"
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        mock_llm_instance = Mock()
        mock_llm_instance.process_query.return_value = "String summary response"
        mock_llm_service.return_value = mock_llm_instance
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json
        assert "String summary response" in str(result["summary"])
    
    @patch('routes.summary.LLMService')
    def test_summary_with_dict_response(self, mock_llm_service, client):
        """Test summary with LLM returning dict response using API for setup."""
        # Register and login user
        register_data = {
            "email": "dict_response_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
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
            "mood_emoji": "😊"
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        # Mock LLM service returning dict
        mock_llm_instance = Mock()
        mock_llm_instance.process_query.return_value = {
            'text': 'Dict summary response'
        }
        mock_llm_service.return_value = mock_llm_instance
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json
        assert "Dict summary response" in str(result["summary"])
    
    def test_summary_memory_decryption_failure(self, client):
        """Test summary when memory decryption fails (simulate by corrupting encrypted data)."""
        # Register and login user
        register_data = {
            "email": "decryption_failure_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        user_id = resp.json["user"]["id"]
        login_data = {"email": "decryption_failure_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memory with model_response
        mem_data = {
            "content": "Test memory content",
            "model_response": "Test model response",
            "chat_id": "test_chat",
            "mood_emoji": "😊"
        }
        resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
        assert resp.status_code == 201
        
        # Simulate decryption failure by corrupting the encrypted data
        from models.memory import Memory
        from extensions import db
        memory = Memory.query.filter_by(user_id=user_id).first()
        memory.model_response = b'corrupted_data'
        db.session.commit()
        
        # Call summary endpoint - should handle decryption failure gracefully
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 404  # No valid memories found
        assert "No memories found for summary" in response.json["error"]

    @patch('routes.summary.LLMService')
    def test_summary_prompt_building(self, mock_llm_service, client):
        """Test that summary prompt is built correctly using API for setup."""
        # Register and login user
        register_data = {
            "email": "prompt_building_test@example.com",
            "password": "Testpassword123!",
            "first_name": "Test",
            "last_name": "User",
            "passphrase": "testpassphrase123"
        }
        resp = client.post("/api/auth/register", json=register_data)
        assert resp.status_code == 201
        login_data = {"email": "prompt_building_test@example.com", "password": "Testpassword123!"}
        resp = client.post("/api/auth/login", json=login_data)
        assert resp.status_code == 200
        access_token = resp.json["access_token"]
        auth_headers = {"Authorization": f"Bearer {access_token}"}
        # Create memories via API
        for i in range(2):
            mem_data = {
                "content": f"Memory content {i}",
                "model_response": f"Model response {i}",
                "chat_id": f"chat_{i}",
                "mood_emoji": "😊"
            }
            resp = client.post("/api/memories/", json=mem_data, headers=auth_headers)
            assert resp.status_code == 201
        # Mock LLM service to capture the prompt
        mock_llm_instance = Mock()
        mock_llm_instance.process_query.return_value = {
            'data': {'text': 'Test summary'}
        }
        mock_llm_service.return_value = mock_llm_instance
        response = client.get(
            "/api/summary/weekly",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json
        assert "Test summary" in str(result["summary"])
    
        mock_llm_instance.process_query.assert_called_once()
        call_args = mock_llm_instance.process_query.call_args[0][0]
        assert "Model response 0" in call_args
        assert "Model response 1" in call_args 