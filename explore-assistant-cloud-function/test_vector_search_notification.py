#!/usr/bin/env python3
"""
Test Vector Search Notification System
This script tests that vector search usage is properly tracked and returned to the frontend.
"""

import json
import logging
from mcp_server import generate_explore_params_from_query

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_vector_search_notification():
    """Test that vector search usage is properly tracked"""
    
    # Mock data for testing
    test_query = "Show me sales for Nike products by month"
    test_explore_key = "ecommerce:order_items"
    test_auth_header = "Bearer test_token"
    
    # Mock golden queries
    test_golden_queries = {
        "exploreGenerationExamples": {
            "ecommerce:order_items": [
                {
                    "input": "Show me total sales by brand",
                    "output": {"fields": ["products.brand", "order_items.total_sale_price"], "filters": {}}
                }
            ]
        }
    }
    
    # Mock semantic models
    test_semantic_models = {
        "ecommerce:order_items": {
            "dimensions": [
                {"name": "products.brand", "label": "Brand", "description": "Product brand name"},
                {"name": "order_items.created_month", "label": "Created Month", "description": "Month when order was created"},
            ],
            "measures": [
                {"name": "order_items.total_sale_price", "label": "Total Sales", "description": "Total sales amount"},
                {"name": "order_items.count", "label": "Order Count", "description": "Number of orders"},
            ],
            "description": "Order items explore with product and sales data"
        }
    }
    
    # Mock current explore
    test_current_explore = {
        "exploreKey": "order_items",
        "exploreId": "ecommerce:order_items",
        "modelName": "ecommerce"
    }
    
    print("🧪 Testing Vector Search Notification System")
    print(f"Query: {test_query}")
    print(f"Explore: {test_explore_key}")
    
    try:
        # This would trigger vector search function calling in a real scenario
        result = generate_explore_params_from_query(
            auth_header=test_auth_header,
            query=test_query,
            explore_key=test_explore_key,
            golden_queries=test_golden_queries,
            semantic_models=test_semantic_models,
            current_explore=test_current_explore
        )
        
        if result:
            print("✅ Test successful - got result")
            print(f"Result keys: {list(result.keys())}")
            
            # Check for vector search usage
            if 'vector_search_used' in result:
                print("🔍 Vector search was used!")
                print(f"Vector search details: {result['vector_search_used']}")
                
                if 'vector_search_summary' in result:
                    summary = result['vector_search_summary']
                    print("📊 Vector search summary:")
                    print(f"  Total searches: {summary.get('total_vector_searches', 0)}")
                    print(f"  User messages: {summary.get('user_messages', [])}")
                    
                    # This is what would be shown to the user
                    for message in summary.get('user_messages', []):
                        print(f"  👤 User notification: {message}")
                else:
                    print("⚠️ Vector search used but no summary provided")
            else:
                print("ℹ️ Vector search was not used for this query")
                print("   (This is normal for queries that don't contain specific values/codes)")
                
        else:
            print("❌ Test failed - no result returned")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        logging.error(f"Test error details: {e}", exc_info=True)

def test_notification_display():
    """Test how notifications would appear in the UI"""
    
    # Mock vector search result
    mock_vector_search_summary = {
        "total_vector_searches": 2,
        "search_semantic_fields_count": 1,
        "lookup_field_values_count": 1,
        "user_messages": [
            "Searched for specific values: nike, adidas", 
            "Verified existence of: Nike"
        ],
        "detailed_usage": [
            {
                "function": "search_semantic_fields",
                "args": {"search_terms": ["nike", "adidas"]},
                "phase": "parameter_generation"
            },
            {
                "function": "lookup_field_values", 
                "args": {"search_string": "Nike"},
                "phase": "parameter_generation"
            }
        ]
    }
    
    print("\n🎨 UI Notification Preview:")
    print("=" * 50)
    print("🔍 Smart Data Discovery Used")
    print("  🔎 Searched for specific values: nike, adidas")
    print("  🔎 Verified existence of: Nike") 
    print("  (2 smart searches performed)")
    print("=" * 50)
    
    print("\nThis notification would appear in a purple box above the explore results")

if __name__ == "__main__":
    test_vector_search_notification()
    test_notification_display()
