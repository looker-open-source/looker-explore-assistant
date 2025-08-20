"""
Unit tests for vertex.response_parser module
"""

import pytest
from unittest.mock import patch, MagicMock

from core.exceptions import TokenLimitExceededException
from vertex.response_parser import (
    extract_vertex_response_text,
    parse_vertex_response,
    extract_function_calls,
    validate_vertex_response
)


class TestExtractVertexResponseText:
    """Test Vertex AI response text extraction"""
    
    def test_valid_response_with_text(self, sample_vertex_response):
        result = extract_vertex_response_text(sample_vertex_response)
        
        # Should return parsed JSON since the text contains valid JSON
        assert isinstance(result, dict)
        assert result["model"] == "test_model"
        assert result["view"] == "test_explore"
    
    def test_response_with_plain_text(self):
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [{'text': 'This is plain text response'}]
                    },
                    'finishReason': 'STOP'
                }
            ]
        }
        
        result = extract_vertex_response_text(response)
        
        assert result == "This is plain text response"
    
    def test_response_with_max_tokens_finish_reason(self):
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [{'text': 'Truncated response'}]
                    },
                    'finishReason': 'MAX_TOKENS'
                }
            ],
            'usageMetadata': {'candidatesTokenCount': 100}
        }
        
        with pytest.raises(TokenLimitExceededException):
            extract_vertex_response_text(response)
    
    def test_invalid_response_none(self):
        result = extract_vertex_response_text(None)
        
        assert result is None
    
    def test_invalid_response_empty_dict(self):
        result = extract_vertex_response_text({})
        
        assert result is None
    
    def test_response_no_candidates(self):
        response = {'candidates': []}
        
        result = extract_vertex_response_text(response)
        
        assert result is None
    
    def test_response_no_parts(self):
        response = {
            'candidates': [
                {
                    'content': {'parts': []},
                    'finishReason': 'STOP'
                }
            ]
        }
        
        result = extract_vertex_response_text(response)
        
        assert result is None
    
    def test_multiple_parts_concatenation(self):
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [
                            {'text': 'Part 1 '},
                            {'text': 'Part 2'}
                        ]
                    },
                    'finishReason': 'STOP'
                }
            ]
        }
        
        result = extract_vertex_response_text(response)
        
        assert result == "Part 1 Part 2"
    
    @patch('vertex.response_parser.parse_llm_response')
    def test_json_parsing_failure_returns_raw_text(self, mock_parse):
        mock_parse.side_effect = Exception("JSON parsing failed")
        
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [{'text': 'Invalid JSON {'}]
                    },
                    'finishReason': 'STOP'
                }
            ]
        }
        
        result = extract_vertex_response_text(response)
        
        assert result == "Invalid JSON {"


class TestValidateVertexResponse:
    """Test response validation"""
    
    def test_valid_response_structure(self, sample_vertex_response):
        is_valid = validate_vertex_response(sample_vertex_response)
        
        assert is_valid is True
    
    def test_invalid_response_not_dict(self):
        is_valid = validate_vertex_response("not a dict")
        
        assert is_valid is False
    
    def test_invalid_response_no_candidates(self):
        response = {}
        
        is_valid = validate_vertex_response(response)
        
        assert is_valid is False
    
    def test_invalid_response_empty_candidates(self):
        response = {'candidates': []}
        
        is_valid = validate_vertex_response(response)
        
        assert is_valid is False
    
    def test_invalid_response_malformed_candidate(self):
        response = {'candidates': ['not a dict']}
        
        is_valid = validate_vertex_response(response)
        
        assert is_valid is False


class TestExtractFunctionCalls:
    """Test function call extraction"""
    
    def test_response_with_function_calls(self):
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [
                            {
                                'functionCall': {
                                    'name': 'search_fields',
                                    'args': {'query': 'test'}
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        function_calls = extract_function_calls(response)
        
        assert len(function_calls) == 1
        assert function_calls[0]['name'] == 'search_fields'
        assert function_calls[0]['args']['query'] == 'test'
    
    def test_response_without_function_calls(self, sample_vertex_response):
        function_calls = extract_function_calls(sample_vertex_response)
        
        assert function_calls == []
    
    def test_response_with_mixed_parts(self):
        response = {
            'candidates': [
                {
                    'content': {
                        'parts': [
                            {'text': 'Some text'},
                            {
                                'functionCall': {
                                    'name': 'test_function',
                                    'args': {}
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        function_calls = extract_function_calls(response)
        
        assert len(function_calls) == 1
        assert function_calls[0]['name'] == 'test_function'
    
    def test_invalid_response(self):
        function_calls = extract_function_calls({})
        
        assert function_calls == []