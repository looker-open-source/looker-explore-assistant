"""
Pytest configuration and fixtures for the test suite
"""

import pytest
import os
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing"""
    with patch.dict(os.environ, {
        'PROJECT': 'test-project',
        'REGION': 'us-central1',
        'VERTEX_MODEL': 'gemini-2.0-flash-001',
        'BQ_PROJECT_ID': 'test-bq-project',
        'BQ_DATASET_ID': 'test_dataset',
        'LOOKERSDK_BASE_URL': 'https://test.looker.com',
        'LOOKERSDK_CLIENT_ID': 'test-client-id',
        'LOOKERSDK_CLIENT_SECRET': 'test-client-secret'
    }):
        yield


@pytest.fixture
def sample_jwt_token():
    """Sample JWT token for testing auth functions"""
    # This is a fake JWT token with a valid structure for testing
    # Header: {"alg": "HS256", "typ": "JWT"}
    # Payload: {"email": "test@example.com", "sub": "user123", "name": "Test User"}
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJzdWIiOiJ1c2VyMTIzIiwibmFtZSI6IlRlc3QgVXNlciJ9.fake_signature"


@pytest.fixture
def sample_vertex_response():
    """Sample Vertex AI response for testing"""
    return {
        'candidates': [
            {
                'content': {
                    'parts': [
                        {
                            'text': '{"model": "test_model", "view": "test_explore", "fields": ["field1", "field2"]}'
                        }
                    ]
                },
                'finishReason': 'STOP'
            }
        ],
        'usageMetadata': {
            'promptTokenCount': 100,
            'candidatesTokenCount': 50,
            'totalTokenCount': 150
        }
    }


@pytest.fixture
def sample_explore_info():
    """Sample explore information for testing"""
    return {
        'explore_key': 'test_model:test_explore',
        'model_name': 'test_model',
        'explore_name': 'test_explore',
        'description': 'Test explore for unit testing',
        'dimensions': [
            {'name': 'dim1', 'label': 'Dimension 1', 'type': 'string'},
            {'name': 'dim2', 'label': 'Dimension 2', 'type': 'date'}
        ],
        'measures': [
            {'name': 'measure1', 'label': 'Measure 1', 'type': 'number'},
            {'name': 'measure2', 'label': 'Measure 2', 'type': 'count'}
        ]
    }


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing"""
    client = MagicMock()
    # Add common mock behaviors
    client.query.return_value.result.return_value = []
    return client


@pytest.fixture
def mock_looker_sdk():
    """Mock Looker SDK for testing"""
    sdk = MagicMock()
    # Add common mock behaviors
    sdk.me.return_value.email = "test@example.com"
    return sdk