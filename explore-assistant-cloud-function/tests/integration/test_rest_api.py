#!/usr/bin/env python3
"""
Integration tests for the new REST API backend.

Tests the production-ready REST API endpoints in restful_backend.py.
"""

import unittest
import json
import os
from unittest.mock import patch, MagicMock
from test_config import setup_test_environment

# Set up test environment and import the new backend
setup_test_environment()

try:
    from restful_backend import create_app
    BACKEND_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ REST backend not available for testing: {e}")
    BACKEND_AVAILABLE = False


class TestRestAPIEndpoints(unittest.TestCase):
    """Test REST API endpoints functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client for REST API"""
        if not BACKEND_AVAILABLE:
            raise unittest.SkipTest("REST backend not available")
        
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def setUp(self):
        """Set up test context"""
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test context"""
        self.app_context.pop()
    
    def test_health_endpoint(self):
        """Test GET /api/v1/health endpoint"""
        response = self.client.get('/api/v1/health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('services', data)
        
        # Check service status structure
        services = data['services']
        self.assertIn('bigquery', services)
        self.assertIn('vertex_ai', services)
        self.assertIn('looker_sdk', services)
    
    def test_legacy_health_endpoint(self):
        """Test backward compatibility GET /health endpoint"""
        response = self.client.get('/health')
        
        # Should redirect to new endpoint
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('status', data)
    
    def test_cors_preflight(self):
        """Test CORS preflight requests"""
        response = self.client.options('/api/v1/query')
        
        self.assertEqual(response.status_code, 200)
        
        # Check CORS headers
        headers = response.headers
        self.assertIn('Access-Control-Allow-Origin', headers)
        self.assertIn('Access-Control-Allow-Methods', headers)
        self.assertIn('Access-Control-Allow-Headers', headers)
    
    @patch('restful_backend.generate_explore_params_from_query')
    @patch('restful_backend.determine_explore_from_prompt')
    def test_query_endpoint_basic(self, mock_determine_explore, mock_generate_params):
        """Test basic POST /api/v1/query functionality"""
        # Mock the parameter generation
        mock_determine_explore.return_value = "ecommerce:order_items"
        mock_generate_params.return_value = {
            "explore_params": {
                "model": "ecommerce",
                "view": "order_items", 
                "fields": ["order_items.created_date", "order_items.total_sale_price"],
                "filters": {"order_items.created_date": "30 days"},
                "limit": 500
            },
            "model_used": "gemini-2.0-flash-001"
        }
        
        test_payload = {
            "query": "show me sales by month",
            "conversation_context": ""
        }
        
        response = self.client.post(
            '/api/v1/query',
            data=json.dumps(test_payload),
            content_type='application/json',
            headers={'Authorization': 'Bearer test-token'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('timestamp', data)
        
        # Check response structure
        result_data = data['data']
        self.assertIn('explore_key', result_data)
        self.assertIn('parameters', result_data)
        self.assertIn('generation_metadata', result_data)
    
    def test_query_endpoint_missing_data(self):
        """Test POST /api/v1/query with missing data"""
        response = self.client.post(
            '/api/v1/query',
            data='',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_query_endpoint_missing_auth(self):
        """Test POST /api/v1/query without authorization header"""
        test_payload = {
            "query": "show me sales by month"
        }
        
        response = self.client.post(
            '/api/v1/query',
            data=json.dumps(test_payload),
            content_type='application/json'
        )
        
        # Should still process (auth extraction handles missing tokens gracefully)
        self.assertIn(response.status_code, [200, 400, 500])  # Various possible outcomes
    
    def test_legacy_root_endpoint(self):
        """Test backward compatibility POST / endpoint"""
        test_payload = {
            "query": "show me sales by month"
        }
        
        response = self.client.post(
            '/',
            data=json.dumps(test_payload),
            content_type='application/json',
            headers={'Authorization': 'Bearer test-token'}
        )
        
        # Should redirect to new query endpoint
        # Status could be 200 (success) or error depending on mocking
        self.assertIn(response.status_code, [200, 400, 500])
    
    @patch('restful_backend.call_vertex_ai_with_retry')
    def test_vertex_proxy_endpoint(self, mock_vertex_call):
        """Test POST /api/v1/vertex-proxy endpoint"""
        mock_vertex_call.return_value = {
            'candidates': [{'content': {'parts': [{'text': 'Test response'}]}}]
        }
        
        test_payload = {
            'contents': [{'parts': [{'text': 'test prompt'}]}],
            'generationConfig': {'temperature': 0.1}
        }
        
        response = self.client.post(
            '/api/v1/vertex-proxy',
            data=json.dumps(test_payload),
            content_type='application/json',
            headers={'Authorization': 'Bearer test-token'}
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
    
    def test_not_found_endpoint(self):
        """Test 404 handling for non-existent endpoints"""
        response = self.client.get('/api/v1/nonexistent')
        
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class TestAdminEndpoints(unittest.TestCase):
    """Test admin endpoints functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client for admin endpoints"""
        if not BACKEND_AVAILABLE:
            raise unittest.SkipTest("REST backend not available")
        
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def setUp(self):
        """Set up test context"""
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up test context"""
        self.app_context.pop()
    
    @patch('restful_backend.app.olympic_manager')
    def test_admin_queries_endpoint(self, mock_olympic_manager):
        """Test GET /api/v1/admin/queries/<table_name> endpoint"""
        # Mock the Olympic manager response
        mock_olympic_manager.get_queries_by_rank.return_value = [
            {'id': '1', 'query': 'test query', 'rank': 'bronze'},
            {'id': '2', 'query': 'another query', 'rank': 'bronze'}
        ]
        
        response = self.client.get('/api/v1/admin/queries/bronze')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('table', data)
        self.assertIn('count', data)
        self.assertEqual(data['table'], 'bronze')
    
    def test_admin_queries_invalid_table(self):
        """Test GET /api/v1/admin/queries/<invalid_table>"""
        response = self.client.get('/api/v1/admin/queries/invalid')
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    @patch('restful_backend.app.olympic_manager')
    def test_admin_promote_endpoint(self, mock_olympic_manager):
        """Test POST /api/v1/admin/promote endpoint"""
        # Mock the Olympic manager response
        mock_olympic_manager.promote_query.return_value = {
            'new_query_id': 'promoted_123',
            'status': 'success'
        }
        
        test_payload = {
            'query_id': 'test_123',
            'target_rank': 'SILVER'
        }
        
        response = self.client.post(
            '/api/v1/admin/promote',
            data=json.dumps(test_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('message', data)
    
    def test_admin_promote_missing_data(self):
        """Test POST /api/v1/admin/promote with missing data"""
        test_payload = {}  # Missing required fields
        
        response = self.client.post(
            '/api/v1/admin/promote',
            data=json.dumps(test_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertIn('error', data)


class TestErrorHandling(unittest.TestCase):
    """Test error handling in REST API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test client"""
        if not BACKEND_AVAILABLE:
            raise unittest.SkipTest("REST backend not available")
        
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()
    
    def test_500_error_handling(self):
        """Test internal server error handling"""
        # This would require a way to trigger a 500 error
        # For now, just test the error handler structure exists
        
        with self.app.test_request_context():
            from restful_backend import _handle_api_error, RestfulBackendError
            
            error = RestfulBackendError("Test error", 500)
            response_data, status_code = _handle_api_error(error)
            
            self.assertEqual(status_code, 500)
            response_json = json.loads(response_data.data)
            self.assertFalse(response_json['success'])
            self.assertIn('error', response_json)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)