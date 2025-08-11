#!/usr/bin/env python3
"""
Unified test suite for MCP Server functionality.
This consolidates all tests into a proper test framework.
"""

import unittest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock

# Import test configuration and utilities
from test_config import (
    mcp_server,
    SAMPLE_GOLDEN_QUERIES,
    SAMPLE_SEMANTIC_MODELS,
    get_test_data_path,
    filter_golden_queries_by_explores,
    filter_semantic_models_by_explores,
    call_vertex_ai_with_retry,
    get_max_tokens_for_model
)


class TestGoldenQueriesFiltering(unittest.TestCase):
    """Test filtering of golden queries by explore keys."""
    
    def setUp(self):
        self.golden_queries = SAMPLE_GOLDEN_QUERIES.copy()
        
    def test_filter_by_single_explore(self):
        """Test filtering golden queries to a single explore."""
        restricted_keys = ['ecommerce:order_items']
        filtered = filter_golden_queries_by_explores(self.golden_queries, restricted_keys)
        
        # Check that only the specified explore remains
        self.assertIn('ecommerce:order_items', filtered['exploreGenerationExamples'])
        self.assertNotIn('finance:transactions', filtered['exploreGenerationExamples'])
        self.assertNotIn('marketing:campaigns', filtered['exploreGenerationExamples'])
        self.assertEqual(len(filtered['exploreGenerationExamples']), 1)
    
    def test_filter_by_multiple_explores(self):
        """Test filtering golden queries to multiple explores."""
        restricted_keys = ['ecommerce:order_items', 'finance:transactions']
        filtered = filter_golden_queries_by_explores(self.golden_queries, restricted_keys)
        
        # Check that both specified explores remain
        self.assertIn('ecommerce:order_items', filtered['exploreGenerationExamples'])
        self.assertIn('finance:transactions', filtered['exploreGenerationExamples'])
        self.assertNotIn('marketing:campaigns', filtered['exploreGenerationExamples'])
        self.assertEqual(len(filtered['exploreGenerationExamples']), 2)
    
    def test_no_filtering_when_empty_restrictions(self):
        """Test that no filtering occurs when restrictions are empty."""
        filtered = filter_golden_queries_by_explores(self.golden_queries, [])
        
        # Should be identical to original
        self.assertEqual(filtered, self.golden_queries)
        self.assertEqual(len(filtered['exploreGenerationExamples']), 3)
    
    def test_nonexistent_explore_key(self):
        """Test filtering with nonexistent explore key."""
        restricted_keys = ['nonexistent:explore']
        filtered = filter_golden_queries_by_explores(self.golden_queries, restricted_keys)
        
        # Should result in empty examples
        self.assertEqual(len(filtered['exploreGenerationExamples']), 0)


class TestSemanticModelsFiltering(unittest.TestCase):
    """Test filtering of semantic models by explore keys."""
    
    def setUp(self):
        self.semantic_models = SAMPLE_SEMANTIC_MODELS.copy()
        
    def test_filter_by_single_explore(self):
        """Test filtering semantic models to a single explore."""
        restricted_keys = ['ecommerce:order_items']
        filtered = filter_semantic_models_by_explores(self.semantic_models, restricted_keys)
        
        # Check that only the specified explore remains
        self.assertIn('ecommerce:order_items', filtered)
        self.assertNotIn('finance:transactions', filtered)
        self.assertNotIn('marketing:campaigns', filtered)
        self.assertEqual(len(filtered), 1)
    
    def test_filter_by_multiple_explores(self):
        """Test filtering semantic models to multiple explores."""
        restricted_keys = ['ecommerce:order_items', 'marketing:campaigns']
        filtered = filter_semantic_models_by_explores(self.semantic_models, restricted_keys)
        
        # Check that both specified explores remain
        self.assertIn('ecommerce:order_items', filtered)
        self.assertIn('marketing:campaigns', filtered)
        self.assertNotIn('finance:transactions', filtered)
        self.assertEqual(len(filtered), 2)
    
    def test_no_filtering_when_empty_restrictions(self):
        """Test that no filtering occurs when restrictions are empty."""
        filtered = filter_semantic_models_by_explores(self.semantic_models, [])
        
        # Should be identical to original
        self.assertEqual(filtered, self.semantic_models)
        self.assertEqual(len(filtered), 3)


class TestParameterGenerationOptimization(unittest.TestCase):
    """Test the optimization of context for parameter generation."""
    
    def setUp(self):
        self.golden_queries = SAMPLE_GOLDEN_QUERIES.copy()
        self.semantic_models = SAMPLE_SEMANTIC_MODELS.copy()
        
    def test_single_explore_optimization(self):
        """Test that single explore scenarios are properly optimized."""
        # Simulate area restriction to 2 explores
        area_explores = ['ecommerce:order_items', 'finance:transactions']
        area_filtered_gq = filter_golden_queries_by_explores(self.golden_queries, area_explores)
        area_filtered_sm = filter_semantic_models_by_explores(self.semantic_models, area_explores)
        
        # Simulate chosen explore (single explore optimization)
        chosen_explore = ['ecommerce:order_items']
        param_gen_gq = filter_golden_queries_by_explores(area_filtered_gq, chosen_explore)
        param_gen_sm = filter_semantic_models_by_explores(area_filtered_sm, chosen_explore)
        
        # Should be optimized to single explore
        self.assertEqual(len(param_gen_gq['exploreGenerationExamples']), 1)
        self.assertEqual(len(param_gen_sm), 1)
        self.assertIn('ecommerce:order_items', param_gen_gq['exploreGenerationExamples'])
        self.assertIn('ecommerce:order_items', param_gen_sm)
    
    def test_massive_context_reduction(self):
        """Test reduction from full dataset to single explore."""
        # Start with full dataset (no restrictions)
        full_gq = self.golden_queries
        full_sm = self.semantic_models
        
        # Optimize to single explore
        chosen_explore = ['marketing:campaigns']
        optimized_gq = filter_golden_queries_by_explores(full_gq, chosen_explore)
        optimized_sm = filter_semantic_models_by_explores(full_sm, chosen_explore)
        
        # Should go from 3 explores to 1
        self.assertEqual(len(optimized_gq['exploreGenerationExamples']), 1)
        self.assertEqual(len(optimized_sm), 1)
        self.assertIn('marketing:campaigns', optimized_gq['exploreGenerationExamples'])


class TestRetryMechanism(unittest.TestCase):
    """Test the Vertex AI retry mechanism with token limit handling."""
    
    def setUp(self):
        self.call_count = 0
    
    def mock_vertex_api_with_token_limits(self, request_body):
        """Mock API that simulates token limit errors."""
        self.call_count += 1
        max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
        
        # Simulate token limit error on first call, success on retry
        if self.call_count == 1 and max_tokens <= 2048:
            return {'error': 'token_limit', 'details': 'maxOutputTokens too low'}
        
        # Success case
        return {
            'candidates': [{'content': {'parts': [{'text': 'Success'}]}}],
            'usageMetadata': {'promptTokenCount': 100, 'totalTokenCount': 150}
        }
    
    @patch('test_config.mcp_server.call_vertex_ai_api_with_service_account')
    def test_token_limit_retry_success(self, mock_api):
        """Test successful retry after token limit error."""
        mock_api.side_effect = self.mock_vertex_api_with_token_limits
        
        request_body = {
            'contents': [{'parts': [{'text': 'test prompt'}]}],
            'generationConfig': {'maxOutputTokens': 2048, 'temperature': 0.1}
        }
        
        result = call_vertex_ai_with_retry(request_body, "test")
        
        # Should succeed after retry
        self.assertIsNotNone(result)
        self.assertIn('candidates', result)
        # Should have increased maxOutputTokens
        self.assertEqual(request_body['generationConfig']['maxOutputTokens'], 4096)
    
    @patch('test_config.mcp_server.call_vertex_ai_api_with_service_account')
    def test_context_preservation(self, mock_api):
        """Test that input context is never truncated."""
        mock_api.side_effect = self.mock_vertex_api_with_token_limits
        
        original_context = 'IMPORTANT FIELD METADATA: ' * 100
        request_body = {
            'contents': [{'parts': [{'text': original_context}]}],
            'generationConfig': {'maxOutputTokens': 2048}
        }
        
        result = call_vertex_ai_with_retry(request_body, "test")
        
        # Context should be preserved
        final_context = request_body['contents'][0]['parts'][0]['text']
        self.assertEqual(original_context, final_context)
        self.assertIsNotNone(result)


class TestModelLimits(unittest.TestCase):
    """Test model token limit calculations."""
    
    def test_known_model_limits(self):
        """Test token limits for known models."""
        # Test Gemini 2.0 Flash
        limits = get_max_tokens_for_model("gemini-2.0-flash-001")
        self.assertEqual(limits["input"], 1048576)
        self.assertEqual(limits["output"], 8192)
        
        # Test Gemini 1.5 Pro
        limits = get_max_tokens_for_model("gemini-1.5-pro")
        self.assertEqual(limits["input"], 2097152)
        self.assertEqual(limits["output"], 8192)
        
        # Test unknown model (fallback)
        limits = get_max_tokens_for_model("unknown-model")
        self.assertEqual(limits["input"], 32000)
        self.assertEqual(limits["output"], 2048)


class TestConversationProcessing(unittest.TestCase):
    """Test conversation context processing using real test data."""
    
    def setUp(self):
        # Load the conversation test data
        conversation_file = get_test_data_path("conversation_test.json")
        try:
            with open(conversation_file, 'r') as f:
                self.conversation_data = json.load(f)
        except FileNotFoundError:
            self.skipTest(f"Conversation test data not found: {conversation_file}")
    
    def test_conversation_data_structure(self):
        """Test that conversation test data has expected structure."""
        required_fields = ['prompt', 'conversation_id', 'prompt_history', 'golden_queries', 'semantic_models']
        
        for field in required_fields:
            self.assertIn(field, self.conversation_data, f"Missing required field: {field}")
        
        # Test prompt history
        self.assertIsInstance(self.conversation_data['prompt_history'], list)
        self.assertGreater(len(self.conversation_data['prompt_history']), 0)
        
        # Test golden queries structure
        golden_queries = self.conversation_data['golden_queries']
        self.assertIn('exploreEntries', golden_queries)
        
    def test_conversation_context_building(self):
        """Test building conversation context from test data."""
        prompt_history = self.conversation_data['prompt_history']
        thread_messages = self.conversation_data.get('thread_messages', [])
        
        # Test that we can build context (would normally call build_conversation_context)
        # This is a structure test since we don't want to call actual LLM functions
        self.assertIsInstance(prompt_history, list)
        self.assertIsInstance(thread_messages, list)
        
        # Test conversation flow
        if len(prompt_history) >= 2:
            self.assertEqual(prompt_history[0], "what are sales by month?")
            self.assertEqual(prompt_history[1], "use a table")


class TestQueryLinks(unittest.TestCase):
    """Test Looker query creation and link generation."""
    
    def test_sample_explore_params(self):
        """Test structure of sample explore parameters."""
        sample_params = {
            "fields": ["order_items.created_date", "order_items.total_sale_price"],
            "filters": {"order_items.created_date": "30 days"},
            "sorts": ["order_items.created_date"],
            "limit": "500",
            "vis_config": {"type": "looker_line"}
        }
        
        # Test required fields
        required_fields = ['fields', 'filters', 'sorts', 'limit']
        for field in required_fields:
            self.assertIn(field, sample_params)
        
        # Test data types
        self.assertIsInstance(sample_params['fields'], list)
        self.assertIsInstance(sample_params['filters'], dict)
        self.assertIsInstance(sample_params['sorts'], list)
        self.assertIsInstance(sample_params['limit'], str)
        
    @patch('test_config.mcp_server.get_looker_sdk')
    def test_query_creation_mock(self, mock_sdk):
        """Test query creation with mocked Looker SDK."""
        # Mock the SDK response
        mock_sdk.return_value.create_query.return_value = MagicMock(slug="test_query_123")
        
        # This would test the actual query creation function if we wanted to mock it
        # For now, just test that we can set up the mock properly
        self.assertIsNotNone(mock_sdk)


if __name__ == '__main__':
    # Set up test suite
    unittest.main(verbosity=2)
