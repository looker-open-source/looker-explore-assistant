#!/usr/bin/env python3
"""
Test Vector Search with Obscure Values
This tests vector search with values that wouldn't be obvious from field names alone.
"""

import json
import logging
from mcp_server import generate_explore_params_from_query

logging.basicConfig(level=logging.INFO)

def test_obscure_vector_search():
    """Test with values that should require vector search"""
    
    # Test queries that should require looking up actual data values
    test_cases = [
        {
            "query": "Show me sales for products from manufacturer code 'ACME123'",
            "reason": "ACME123 is not obviously mapped to any field name"
        },
        {
            "query": "Filter orders by internal status code 'PROC_COMP'", 
            "reason": "PROC_COMP is not obvious from field metadata"
        },
        {
            "query": "Show products with category identifier 'CAT_ELECTRONICS_001'",
            "reason": "Specific category code that needs lookup"
        }
    ]
    
    # Mock semantic models with minimal field info (no obvious brand field)
    test_semantic_models = {
        "ecommerce:order_items": {
            "dimensions": [
                {"name": "products.category", "label": "Category", "description": "Product category"},
                {"name": "order_items.status", "label": "Status", "description": "Order status"},
                {"name": "suppliers.code", "label": "Supplier Code", "description": "Supplier identifier"},
                {"name": "order_items.created_month", "label": "Created Month", "description": "Month created"},
            ],
            "measures": [
                {"name": "order_items.total_sale_price", "label": "Total Sales", "description": "Total sales amount"},
                {"name": "order_items.count", "label": "Order Count", "description": "Number of orders"},
            ],
            "description": "Order items explore"
        }
    }
    
    # Mock golden queries
    test_golden_queries = {
        "exploreGenerationExamples": {
            "ecommerce:order_items": [
                {
                    "input": "Show me total sales",
                    "output": {"fields": ["order_items.total_sale_price"], "filters": {}}
                }
            ]
        }
    }
    
    test_current_explore = {
        "exploreKey": "order_items",
        "exploreId": "ecommerce:order_items", 
        "modelName": "ecommerce"
    }
    
    for test_case in test_cases:
        print(f"\n🧪 Testing: {test_case['query']}")
        print(f"   Reason: {test_case['reason']}")
        
        try:
            result = generate_explore_params_from_query(
                auth_header="Bearer test_token",
                query=test_case['query'],
                explore_key="ecommerce:order_items",
                golden_queries=test_golden_queries,
                semantic_models=test_semantic_models,
                current_explore=test_current_explore
            )
            
            if result and 'vector_search_used' in result:
                print(f"   ✅ Vector search used: {len(result['vector_search_used'])} calls")
                for usage in result['vector_search_used']:
                    print(f"      📞 Function: {usage['function']}")
                    print(f"         Args: {usage['args']}")
            else:
                print(f"   ❌ Vector search NOT used")
                if result:
                    print(f"      Result keys: {list(result.keys())}")
                    
        except Exception as e:
            print(f"   💥 Error: {e}")

def test_simple_case():
    """Test with a simple case to see basic functionality"""
    
    print("\n🔍 Testing Simple Case (Nike with no brand field in metadata)")
    
    # Semantic model WITHOUT an obvious brand field
    minimal_semantic_models = {
        "ecommerce:order_items": {
            "dimensions": [
                {"name": "products.category", "label": "Category", "description": "Product category"},
                {"name": "order_items.created_month", "label": "Created Month", "description": "Month created"},
            ],
            "measures": [
                {"name": "order_items.total_sale_price", "label": "Total Sales", "description": "Total sales amount"},
            ],
            "description": "Order items explore - minimal fields"
        }
    }
    
    test_golden_queries = {
        "exploreGenerationExamples": {
            "ecommerce:order_items": [
                {"input": "Show sales", "output": {"fields": ["order_items.total_sale_price"], "filters": {}}}
            ]
        }
    }
    
    test_current_explore = {
        "exploreKey": "order_items",
        "exploreId": "ecommerce:order_items",
        "modelName": "ecommerce"
    }
    
    try:
        result = generate_explore_params_from_query(
            auth_header="Bearer test_token",
            query="Show me sales for Nike products",  # Nike not obvious from minimal field set
            explore_key="ecommerce:order_items",
            golden_queries=test_golden_queries,
            semantic_models=minimal_semantic_models,
            current_explore=test_current_explore
        )
        
        print(f"Result: {json.dumps(result, indent=2) if result else 'None'}")
        
    except Exception as e:
        print(f"Error: {e}")
        logging.error(f"Detailed error: {e}", exc_info=True)

if __name__ == "__main__":
    test_obscure_vector_search()
    test_simple_case()
