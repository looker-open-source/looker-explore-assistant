import pytest
from src.middleware.auth_middleware import auth_middleware
from src.middleware.context_middleware import context_middleware

def test_auth_middleware_valid_token():
    request = {
        'headers': {
            'Authorization': 'Bearer valid_token'
        }
    }
    response = auth_middleware(request)
    assert response['status'] == 200
    assert response['message'] == 'Authentication successful'

def test_auth_middleware_missing_token():
    request = {
        'headers': {}
    }
    response = auth_middleware(request)
    assert response['status'] == 401
    assert response['message'] == 'Authentication token is missing'

def test_context_middleware_with_context():
    request = {
        'context': {
            'user_id': '12345'
        }
    }
    response = context_middleware(request)
    assert response['status'] == 200
    assert response['message'] == 'Context is valid'

def test_context_middleware_without_context():
    request = {}
    response = context_middleware(request)
    assert response['status'] == 400
    assert response['message'] == 'Context is required'