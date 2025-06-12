import unittest
from src.handlers.mcp_handler import MCPHandler
from src.handlers.fallback_handler import FallbackHandler

class TestMCPHandler(unittest.TestCase):

    def setUp(self):
        self.mcp_handler = MCPHandler()
        self.fallback_handler = FallbackHandler()

    def test_handle_request_with_context(self):
        request = {
            "context": {"user_id": "123"},
            "data": {"query": "some query"}
        }
        response = self.mcp_handler.handle_request(request)
        self.assertEqual(response['status'], 'success')
        self.assertIn('data', response)

    def test_handle_request_without_context(self):
        request = {
            "data": {"query": "some query"}
        }
        response = self.mcp_handler.handle_request(request)
        self.assertEqual(response['status'], 'success')
        self.assertIn('data', response)

    def test_fallback_handler(self):
        request = {
            "data": {"unknown": "data"}
        }
        response = self.fallback_handler.handle_request(request)
        self.assertEqual(response['status'], 'error')
        self.assertEqual(response['message'], 'No handler found for the request.')

if __name__ == '__main__':
    unittest.main()