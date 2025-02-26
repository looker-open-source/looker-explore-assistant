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
