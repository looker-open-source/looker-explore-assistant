import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# import the fastapi main code here
from async_main import app

client = TestClient(app)

@pytest.mark.parametrize(
    # Define mock data and expected outputs
    "user_id, name, email, token, expected_status, expected_message",
    [
        # Valid looker user & is new user in cloudSQL
        (
            "1", 
            "Test User", 
            "test@example.com", 
            "valid_token",
            200, 
            "User created successfully"
        ),
        # Valid looker user & is existing user in cloudSQL
        (
            "2", 
            "Test User", 
            "test@example.com", 
            "valid_token",
            200, 
            "User already exists"
        ),
        # Invalid Looker user
        (
            "invalid", 
            "Test User", 
            "test@example.com", 
            "valid_token",
            403, 
            "User is not a validated Looker user"
        ),
        # Invalid token 
        (
            "1", 
            "Test User", 
            "test@example.com", 
            "invalid_token",
            403, 
            "Invalid token"
        ),
    ]
)

def test_login_endpoint(user_id, 
                        name, 
                        email, 
                        token,
                        expected_status, 
                        expected_message
                        ):
    # Use patch to mock all the functions dependent on cloudSQL
    # convention : patch('main_module.function_called') as mock_name
    with \
        patch('async_main.validate_bearer_token') as mock_validate_bearer_token, \
        patch('async_main.verify_looker_user') as mock_verify_looker_user, \
        patch('async_main.get_user_from_db') as mock_get_user_from_db, \
        patch('async_main.create_new_user') as mock_create_new_user:

        if token == "valid_token":
            mock_validate_bearer_token.return_value = True
        else:
            mock_validate_bearer_token.return_value = False

        if user_id == "invalid":
            mock_verify_looker_user.return_value = False
        else: 
            mock_verify_looker_user.return_value = True


        if user_id == "1":
            # simulate new user created successfully
            mock_get_user_from_db.return_value = None
            mock_create_new_user.return_value = {
                "user_id": "1", "name": "Test User", "email": "test@example.com"
                }
        elif user_id == "2": 
            # simuulate user already exist
            mock_get_user_from_db.return_value = {
                "user_id": "2", "name": "Test User", "email": "test@example.com"
                }
        

        # Prepare the payload for the request
        payload = {"user_id": user_id, "name": name, "email": email}
        header =  {"Authorization": f"Bearer {token}"}

        response = client.post("/login", 
                               json=payload, 
                               headers = header
                               )

        assert response.status_code == expected_status
        if expected_status == 200:
            assert response.json()["message"] == expected_message
            assert "data" in response.json()
            assert response.json()["data"] == {"user_id": user_id, "name": name, "email": email}
        else:
            # Exceptions raise the key "detail" instead of message
            assert response.json()["detail"] == expected_message


# Chat endpoint tests
@pytest.mark.parametrize(
    "user_id, explore_key, token, expected_status, expected_message",
    [
        # Valid request
        (
            "user1",
            "explore1",
            "valid_token",
            200,
            "Chat created successfully"
        ),
        # Missing parameters
        (
            None,
            "explore1",
            "valid_token",
            400,
            "Missing required parameters"
        ),
        # Invalid token
        (
            "user1",
            "explore1",
            "invalid_token",
            403,
            "Invalid token"
        ),
        # Database error
        (
            "error_user",
            "explore1",
            "valid_token",
            500,
            "Failed to create chat thread"
        ),
    ]
)
def test_create_chat_endpoint(user_id, explore_key, token, expected_status, expected_message):
    with \
        patch('async_main.validate_bearer_token') as mock_validate_bearer_token, \
        patch('async_main.create_chat_thread') as mock_create_chat_thread:

        mock_validate_bearer_token.return_value = token == "valid_token"
        
        if user_id == "error_user":
            mock_create_chat_thread.return_value = None
        else:
            mock_create_chat_thread.return_value = 1

        payload = {}
        if user_id:
            payload["user_id"] = user_id
        if explore_key:
            payload["explore_key"] = explore_key

        response = client.post(
            "/chat",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == expected_status
        if expected_status == 200:
            assert response.json()["message"] == expected_message
            assert "data" in response.json()
        else:
            assert response.json()["detail"] == expected_message

# Chat history endpoint tests
@pytest.mark.parametrize(
    "user_id, chat_id, token, mock_return, expected_status, expected_response",
    [
        # Valid request
        (
            "user1",
            "chat1",
            "valid_token",
            {"data": [{"message_id": 1, "content": "test message"}]},
            200,
            {"data": [{"message_id": 1, "content": "test message"}]}
        ),
        # Missing user_id
        (
            None,
            "chat1",
            "valid_token",
            None,
            422,
            {"detail": [{"loc": ["query", "user_id"], 
                        "msg": "field required",
                        "type": "missing"}]}
        ),
        # Missing chat_id
        (
            "user1",
            None,
            "valid_token",
            None,
            422,
            {"detail": [{"loc": ["query", "chat_id"], 
                        "msg": "field required",
                        "type": "missing"}]}
        ),
        # Invalid token
        (
            "user1",
            "chat1",
            "invalid_token",
            None,
            403,
            {"detail": "Invalid token"}
        ),
        # Chat history not found
        (
            "user1",
            "nonexistent_chat",
            "valid_token",
            None,  # Simulating no data returned
            404,
            {"detail": "Chat history not found"}
        ),
    ]
)
def test_chat_history_endpoint(user_id, chat_id, token, mock_return, expected_status, expected_response):
    with \
        patch('async_main.validate_bearer_token') as mock_validate_bearer_token, \
        patch('async_main.retrieve_chat_history') as mock_retrieve_chat_history:

        mock_validate_bearer_token.return_value = token == "valid_token"
        mock_retrieve_chat_history.return_value = mock_return

        # Only add parameters if they are not None
        params = {}
        if user_id is not None:
            params["user_id"] = user_id
        if chat_id is not None:
            params["chat_id"] = chat_id

        response = client.get(
            "/chat/history",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == expected_status
        if expected_status == 422:
            # For 422 responses, we only check the status code as the exact error message might vary
            assert response.json()["detail"][0]["type"] == expected_response["detail"][0]["type"]
        else:
            assert response.json() == expected_response

# Prompt endpoint tests
@pytest.mark.parametrize(
    "payload, token, mock_config, expected_status, expected_response",
    [
        # Valid request - looker type
        (
            {
                "contents": "test query",
                "prompt_type": "looker",
                "current_explore_key": "explore1",
                "user_id": "user1",
                "parameters": {"param": "value"},
                "chat_id": None
            },
            "valid_token",
            {
                "chat_thread_id": 1,
                "user_message_id": 1,
                "bot_message_id": 2,
                "generated_response": "generated looker response"
            },
            200,
            {
                "message": "Prompt handled successfully",
                "data": {
                    "chat_id": 1,
                    "response": "generated looker response"
                }
            }
        ),
        # Valid request - general type
        (
            {
                "contents": "test query",
                "prompt_type": "general",
                "current_explore_key": "explore1",
                "user_id": "user1",
                "chat_id": None
            },
            "valid_token",
            {
                "chat_thread_id": 1,
                "user_message_id": 1,
                "bot_message_id": 2,
                "generated_response": "generated general response"
            },
            200,
            {
                "message": "Prompt handled successfully",
                "data": {
                    "chat_id": 1,
                    "response": "generated general response"
                }
            }
        ),
        # Valid request with existing chat_id
        (
            {
                "contents": "test query",
                "prompt_type": "general",
                "current_explore_key": "explore1",
                "user_id": "user1",
                "chat_id": 123
            },
            "valid_token",
            {
                "chat_thread_id": 123,
                "user_message_id": 1,
                "bot_message_id": 2,
                "generated_response": "generated response"
            },
            200,
            {
                "message": "Prompt handled successfully",
                "data": {
                    "chat_id": 123,
                    "response": "generated response"
                }
            }
        ),
        # Missing required fields
        (
            {
                "contents": "test query"
            },
            "valid_token",
            {},
            400,
            {
                "detail": "Missing required parameters"
            }
        ),
        # Invalid token
        (
            {
                "contents": "test query",
                "prompt_type": "looker",
                "current_explore_key": "explore1",
                "user_id": "user1"
            },
            "invalid_token",
            {},
            403,
            {
                "detail": "Invalid token"
            }
        ),
    ]
)
def test_prompt_endpoint(payload, token, mock_config, expected_status, expected_response):

    with \
        patch('async_main.validate_bearer_token') as mock_validate_bearer_token, \
        patch('async_main.generate_looker_query') as mock_generate_looker_query, \
        patch('async_main.generate_response') as mock_generate_response, \
        patch('async_main.create_chat_thread') as mock_create_chat_thread, \
        patch('async_main.add_message') as mock_add_message:

        # Configure mock responses
        mock_validate_bearer_token.return_value = token == "valid_token"
        
        # Configure chat thread creation
        mock_create_chat_thread.return_value = mock_config.get("chat_thread_id")

        # Configure message creation
        mock_add_message.side_effect = [
            mock_config.get("user_message_id"),
            mock_config.get("bot_message_id")
        ]

        # Configure response generation
        if payload.get("prompt_type") == "looker":
            mock_generate_looker_query.return_value = mock_config.get("generated_response")
        else:
            mock_generate_response.return_value = mock_config.get("generated_response")

        # Make the request
        response = client.post(
            "/prompt",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )

        # Verify response
        assert response.status_code == expected_status
        assert response.json() == expected_response

        # Verify mock calls for successful cases
        if expected_status == 200:
            if not payload.get("chat_id"):
                mock_create_chat_thread.assert_called_once()
            mock_add_message.assert_called()
            if payload.get("prompt_type") == "looker":
                mock_generate_looker_query.assert_called_once()
            else:
                mock_generate_response.assert_called_once()

# Feedback endpoint tests
@pytest.mark.parametrize(
    "payload, token, expected_status, expected_message",
    [
        # Valid request
        (
            {
                "user_id": "user1",
                "message_id": 1,
                "feedback_text": "Great response!",
                "is_positive": True
            },
            "valid_token",
            200,
            "Feedback submitted successfully"
        ),
        # Missing required fields
        (
            {
                "user_id": "user1",
                "message_id": 1
            },
            "valid_token",
            400,
            "Missing required parameters"
        ),
        # Invalid token
        (
            {
                "user_id": "user1",
                "message_id": 1,
                "feedback_text": "Great response!",
                "is_positive": True
            },
            "invalid_token",
            403,
            "Invalid token"
        ),
        # Database error
        (
            {
                "user_id": "error_user",
                "message_id": 1,
                "feedback_text": "Great response!",
                "is_positive": True
            },
            "valid_token",
            500,
            "Failed to submit feedback"
        ),
    ]
)
def test_feedback_endpoint(payload, token, expected_status, expected_message):
    with \
        patch('async_main.validate_bearer_token') as mock_validate_bearer_token, \
        patch('async_main.add_feedback') as mock_add_feedback:

        mock_validate_bearer_token.return_value = token == "valid_token"
        mock_add_feedback.return_value = payload.get("user_id") != "error_user"

        response = client.post(
            "/feedback",
            json=payload,
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == expected_status
        if expected_status == 200:
            assert response.json()["message"] == expected_message
        else:
            assert response.json()["detail"] == expected_message