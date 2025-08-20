"""
Unit tests for core.config module
"""

import pytest
from unittest.mock import patch

from core.config import (
    get_max_tokens_for_model,
    get_model_generation_defaults,
    update_token_warning_thresholds,
    MODEL_LIMITS
)


class TestGetMaxTokensForModel:
    """Test model token limit retrieval"""
    
    def test_known_model(self):
        limits = get_max_tokens_for_model("gemini-2.0-flash-001")
        
        assert limits["input"] == 1048576
        assert limits["output"] == 8192
    
    def test_partial_model_name(self):
        limits = get_max_tokens_for_model("some-prefix-gemini-2.0-flash-suffix")
        
        assert limits["input"] == 1048576
        assert limits["output"] == 8192
    
    def test_unknown_model(self):
        limits = get_max_tokens_for_model("unknown-model")
        
        assert limits["input"] == 32760  # Default fallback
        assert limits["output"] == 2048   # Default fallback
    
    def test_model_limits_completeness(self):
        """Ensure all models in MODEL_LIMITS have both input and output"""
        for model, limits in MODEL_LIMITS.items():
            assert "input" in limits
            assert "output" in limits
            assert isinstance(limits["input"], int)
            assert isinstance(limits["output"], int)


class TestGetModelGenerationDefaults:
    """Test default generation parameters"""
    
    def test_standard_model_defaults(self):
        defaults = get_model_generation_defaults("gemini-2.0-flash")
        
        assert "temperature" in defaults
        assert "topP" in defaults
        assert "topK" in defaults
        assert "maxOutputTokens" in defaults
        assert isinstance(defaults["temperature"], float)
        assert isinstance(defaults["maxOutputTokens"], int)
    
    def test_max_output_tokens_matches_model_limit(self):
        model = "gemini-2.0-flash-001"
        defaults = get_model_generation_defaults(model)
        limits = get_max_tokens_for_model(model)
        
        assert defaults["maxOutputTokens"] == limits["output"]


class TestUpdateTokenWarningThresholds:
    """Test token warning threshold calculation"""
    
    def test_thresholds_calculation(self):
        model = "gemini-2.0-flash-001"
        thresholds = update_token_warning_thresholds(model)
        limits = get_max_tokens_for_model(model)
        
        expected_warning = int(limits["input"] * 0.8)
        expected_critical = int(limits["input"] * 0.9)
        
        assert thresholds["warning_threshold"] == expected_warning
        assert thresholds["critical_threshold"] == expected_critical
    
    def test_thresholds_for_unknown_model(self):
        thresholds = update_token_warning_thresholds("unknown-model")
        
        # Should use default fallback limits
        assert thresholds["warning_threshold"] == int(32760 * 0.8)
        assert thresholds["critical_threshold"] == int(32760 * 0.9)