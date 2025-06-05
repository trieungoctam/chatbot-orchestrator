import pytest
import uuid
from unittest.mock import AsyncMock, patch
from fastapi import status, HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.request import PancakeMessageRequest
from app.schemas.response import PancakeMessageResponse
from app.services import get_message_handler


class TestChatAPI:
    """Test suite for Chat API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_access_verification(self):
        """Mock access verification dependency."""
        with patch("app.api.dependencies.verify_access") as mock:
            mock.return_value = True
            yield mock

    @pytest.fixture
    def mock_message_handler(self):
        """Mock MessageHandler using FastAPI dependency override."""
        mock_handler = AsyncMock()
        app.dependency_overrides[get_message_handler] = lambda: mock_handler
        yield mock_handler
        # Clean up dependency override
        if get_message_handler in app.dependency_overrides:
            del app.dependency_overrides[get_message_handler]

    @pytest.fixture
    def sample_message_request(self):
        """Sample message request data for testing."""
        return {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Hello, how are you?</USER><br><BOT>I'm doing well, thank you!</BOT><br>",
            "resources": {"user_id": "123", "session_type": "web"}
        }

    @pytest.fixture
    def sample_message_response(self):
        """Sample message response for testing."""
        return {
            "success": True,
            "status": "processed",
            "message": "Message processed successfully"
        }

    # SUCCESSFUL MESSAGE PROCESSING Tests
    def test_send_message_success(self, client, mock_access_verification, mock_message_handler,
                                 sample_message_request, sample_message_response):
        """Test successful message processing."""
        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=sample_message_request)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "processed"
        assert data["message"] == "Message processed successfully"

        # Verify handler was called with correct parameters
        mock_message_handler.handle_message_request.assert_called_once_with(
            conversation_id=sample_message_request["conversation_id"],
            history=sample_message_request["history"],
            resources=sample_message_request["resources"]
        )

    def test_send_message_without_conversation_id(self, client, mock_access_verification,
                                                 mock_message_handler, sample_message_response):
        """Test message processing with auto-generated conversation_id."""
        message_data = {
            "history": "<USER>Hello, I need help</USER><br>",
            "resources": {"platform": "web"}
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Verify handler was called and conversation_id was generated
        call_args = mock_message_handler.handle_message_request.call_args
        assert call_args[1]["conversation_id"] is not None
        assert len(call_args[1]["conversation_id"]) == 36  # UUID length
        assert call_args[1]["history"] == message_data["history"]
        assert call_args[1]["resources"] == message_data["resources"]

    def test_send_message_without_resources(self, client, mock_access_verification,
                                           mock_message_handler, sample_message_response):
        """Test message processing without optional resources."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Simple message</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

        # Verify handler was called with None resources
        call_args = mock_message_handler.handle_message_request.call_args
        assert call_args[1]["resources"] is None

    def test_send_message_minimal_data(self, client, mock_access_verification):
        """Test message processing with minimal required data - uses real handler."""
        message_data = {
            "history": "<USER>Minimal test</USER><br>"
        }

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "ai_processing_started"

    # ERROR HANDLING Tests
    def test_send_message_handler_exception(self, client, mock_access_verification, mock_message_handler):
        """Test message processing when handler throws an exception."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Test message</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(
            side_effect=Exception("Handler processing failed")
        )

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Message processing failed: Handler processing failed" in data["detail"]

    def test_send_message_handler_timeout(self, client, mock_access_verification, mock_message_handler):
        """Test message processing when handler times out."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Timeout test</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(
            side_effect=TimeoutError("Request timeout")
        )

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Message processing failed: Request timeout" in data["detail"]

    def test_send_message_handler_returns_error(self, client, mock_access_verification, mock_message_handler):
        """Test message processing when handler returns error result."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Error test</USER><br>"
        }

        error_response = {
            "success": False,
            "status": "failed",
            "message": "Processing failed",
            "error": "AI service unavailable"
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=error_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "failed"
        assert data["error"] == "AI service unavailable"

    # VALIDATION Tests
    def test_send_message_missing_history(self, client, mock_access_verification):
        """Test message processing with missing required history field."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "resources": {"test": "data"}
        }

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "history" in str(data["detail"]).lower()

    def test_send_message_empty_history(self, client, mock_access_verification):
        """Test message processing with empty history."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": ""
        }

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

    def test_send_message_invalid_json(self, client, mock_access_verification):
        """Test message processing with invalid JSON data."""
        response = client.post("/api/v1/chat/message", data="invalid json")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_send_message_wrong_content_type(self, client, mock_access_verification):
        """Test message processing with wrong content type."""
        response = client.post("/api/v1/chat/message", data="text data",
                              headers={"Content-Type": "text/plain"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # CONVERSATION ID GENERATION Tests
    def test_conversation_id_generation_format(self, client, mock_access_verification,
                                              mock_message_handler, sample_message_response):
        """Test that auto-generated conversation_id is a valid UUID."""
        message_data = {"history": "<USER>UUID test</USER><br>"}

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

        # Check that the conversation_id passed to handler is a valid UUID
        call_args = mock_message_handler.handle_message_request.call_args
        conversation_id = call_args[1]["conversation_id"]

        # This should not raise an exception if it's a valid UUID
        uuid.UUID(conversation_id)

    def test_conversation_id_preservation(self, client, mock_access_verification,
                                         mock_message_handler, sample_message_response):
        """Test that provided conversation_id is preserved."""
        original_id = str(uuid.uuid4())
        message_data = {
            "conversation_id": original_id,
            "history": "<USER>ID preservation test</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

        # Verify the original conversation_id was passed to handler
        call_args = mock_message_handler.handle_message_request.call_args
        assert call_args[1]["conversation_id"] == original_id

    # AUTHENTICATION Tests
    def test_missing_authentication(self, client):
        """Test that chat endpoint requires authentication."""
        # Since verify_access currently always returns True, we'll use FastAPI dependency override
        from app.api.dependencies import verify_access

        def unauthorized_access():
            raise HTTPException(status_code=401, detail="Unauthorized")

        app.dependency_overrides[verify_access] = unauthorized_access

        try:
            message_data = {
                "history": "<USER>Auth test</USER><br>"
            }

            response = client.post("/api/v1/chat/message", json=message_data)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
        finally:
            # Clean up dependency override
            if verify_access in app.dependency_overrides:
                del app.dependency_overrides[verify_access]

    # EDGE CASES
    def test_send_message_very_long_history(self, client, mock_access_verification,
                                           mock_message_handler, sample_message_response):
        """Test message processing with very long history."""
        long_history = "<USER>" + "A" * 10000 + "</USER><br>"
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": long_history
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

        # Verify the full history was passed
        call_args = mock_message_handler.handle_message_request.call_args
        assert call_args[1]["history"] == long_history

    def test_send_message_special_characters(self, client, mock_access_verification):
        """Test message processing with special characters in history."""
        special_history = "<USER>Hello! @#$%^&*()_+{}|:<>?[]\\;',./</USER><br><BOT>こんにちは 你好 🤖</BOT><br>"
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": special_history
        }

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

    def test_send_message_complex_resources(self, client, mock_access_verification,
                                           mock_message_handler, sample_message_response):
        """Test message processing with complex resources object."""
        complex_resources = {
            "user_info": {
                "id": "user123",
                "name": "Test User",
                "preferences": ["opt1", "opt2"]
            },
            "session_data": {
                "device": "mobile",
                "browser": "chrome",
                "location": {"lat": 40.7128, "lng": -74.0060}
            },
            "metadata": {
                "version": "1.0",
                "debug": True
            }
        }

        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Complex resources test</USER><br>",
            "resources": complex_resources
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK

        # Verify complex resources were passed correctly
        call_args = mock_message_handler.handle_message_request.call_args
        assert call_args[1]["resources"] == complex_resources

    # LOGGING AND MONITORING Tests
    def test_send_message_logging(self, client, mock_access_verification,
                                 mock_message_handler, sample_message_response):
        """Test that message processing includes proper logging."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Logging test</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=sample_message_response)

        with patch('app.api.v1.chat_api.logger') as mock_logger:
            response = client.post("/api/v1/chat/message", json=message_data)

            assert response.status_code == status.HTTP_200_OK

            # Verify info logging was called
            mock_logger.info.assert_called()

    def test_send_message_error_logging(self, client, mock_access_verification, mock_message_handler):
        """Test that errors are properly logged."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Error logging test</USER><br>"
        }

        mock_message_handler.handle_message_request = AsyncMock(
            side_effect=Exception("Test error")
        )

        with patch('app.api.v1.chat_api.logger') as mock_logger:
            response = client.post("/api/v1/chat/message", json=message_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

            # Verify error logging was called
            mock_logger.error.assert_called()

    # RESPONSE FORMAT Tests
    def test_response_format_validation(self, client, mock_access_verification,
                                       mock_message_handler):
        """Test that response format matches PancakeMessageResponse schema."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Format test</USER><br>"
        }

        handler_response = {
            "success": True,
            "status": "completed",
            "message": "Test response"
        }

        mock_message_handler.handle_message_request = AsyncMock(return_value=handler_response)

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Validate response structure
        assert "success" in data
        assert "status" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["status"], str)

        # Verify our custom message came through
        assert data["message"] == "Test response"

    # CONCURRENT PROCESSING Tests
    def test_concurrent_message_processing(self, client, mock_access_verification):
        """Test that concurrent messages are handled properly."""
        import threading
        import time

        def send_message(conversation_id):
            message_data = {
                "conversation_id": conversation_id,
                "history": f"<USER>Concurrent test {conversation_id}</USER><br>"
            }
            return client.post("/api/v1/chat/message", json=message_data)

        # Send multiple concurrent requests
        conversation_ids = [str(uuid.uuid4()) for _ in range(3)]
        threads = []
        results = []

        for conv_id in conversation_ids:
            thread = threading.Thread(target=lambda cid=conv_id: results.append(send_message(cid)))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests were successful
        assert len(results) == 3
        for response in results:
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["success"] is True

    # REAL HANDLER INTEGRATION Tests
    def test_real_handler_integration(self, client, mock_access_verification):
        """Test integration with the real message handler."""
        message_data = {
            "conversation_id": str(uuid.uuid4()),
            "history": "<USER>Real handler test</USER><br>",
            "resources": {"test": "integration"}
        }

        response = client.post("/api/v1/chat/message", json=message_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "ai_processing_started"
        assert data["message"] == "Message received and AI processing started"
        # Verify additional fields present in real handler response
        assert "ai_job_id" in data
        assert "bot_name" in data