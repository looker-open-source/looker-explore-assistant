#!/usr/bin/env python3
"""
Test configuration and utilities for MCP Server tests.
This module handles imports and test setup when tests are in a separate directory.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def setup_test_environment():
    """
    Set up the test environment by adding the parent directory to sys.path
    so we can import mcp_server from the tests directory.
    """
    # Get the directory containing this file (tests/)
    tests_dir = Path(__file__).parent
    
    # Get the parent directory (explore-assistant-cloud-function/)
    project_dir = tests_dir.parent
    
    # Add the project directory to Python path
    if str(project_dir) not in sys.path:
        sys.path.insert(0, str(project_dir))
    
    # Verify we can import mcp_server
    try:
        import mcp_server
        logging.info(f"✅ Successfully imported mcp_server from {project_dir}")
        return mcp_server
    except ImportError as e:
        logging.error(f"❌ Failed to import mcp_server: {e}")
        logging.error(f"Project directory: {project_dir}")
        logging.error(f"Current sys.path: {sys.path}")
        raise

def get_test_data_path(filename):
    """Get the absolute path to a test data file."""
    tests_dir = Path(__file__).parent
    return tests_dir / "data" / filename

# Set up the environment when this module is imported
mcp_server = setup_test_environment()

# Export commonly used functions from new modular architecture
try:
    # Import from new modular structure
    from explore_selection.filters import (
        filter_golden_queries_by_explores,
        filter_semantic_models_by_explores
    )
    from vertex.client import call_vertex_ai_with_retry
    from core.config import get_max_tokens_for_model
    from parameter_generation import generate_explore_params_from_query
    logging.info("✅ Imported from new modular architecture")
except ImportError as e:
    logging.warning(f"⚠️ Falling back to legacy imports: {e}")
    # Fallback to legacy imports
    from mcp_server import (
        filter_golden_queries_by_explores,
        filter_semantic_models_by_explores,
        call_vertex_ai_with_retry,
        get_max_tokens_for_model
    )

# For backward compatibility, also try to import calculate_max_output_tokens
try:
    from mcp_server import calculate_max_output_tokens
except ImportError:
    # Create a fallback implementation
    def calculate_max_output_tokens(model_name: str, input_tokens: int) -> int:
        """Fallback implementation for calculate_max_output_tokens"""
        from core.config import get_max_tokens_for_model
        limits = get_max_tokens_for_model(model_name)
        return min(limits["output"], max(1000, limits["input"] - input_tokens))

# Test data constants
SAMPLE_GOLDEN_QUERIES = {
    'exploreGenerationExamples': {
        'ecommerce:order_items': [
            {'input': 'Show me total sales by month', 'output': 'ecommerce_params'},
            {'input': 'Customer orders analysis', 'output': 'ecommerce_params2'}
        ],
        'finance:transactions': [
            {'input': 'Monthly revenue breakdown', 'output': 'finance_params'}
        ],
        'marketing:campaigns': [
            {'input': 'Campaign performance metrics', 'output': 'marketing_params'}
        ]
    },
    'exploreRefinementExamples': {
        'ecommerce:order_items': [{'input': 'refine sales', 'output': 'refine1'}],
        'finance:transactions': [{'input': 'refine revenue', 'output': 'refine2'}]
    }
}

SAMPLE_SEMANTIC_MODELS = {
    'ecommerce:order_items': {
        'dimensions': [{'name': 'order_date'}, {'name': 'customer_id'}],
        'measures': [{'name': 'total_sales'}, {'name': 'order_count'}]
    },
    'finance:transactions': {
        'dimensions': [{'name': 'transaction_date'}],
        'measures': [{'name': 'revenue'}]
    },
    'marketing:campaigns': {
        'dimensions': [{'name': 'campaign_name'}],
        'measures': [{'name': 'impressions'}]
    }
}
