#!/usr/bin/env python3
"""
Test Vector Search Integration Against Live Backend
This script tests vector search against the actual deployed service.
"""

import requests
import json
import os
from datetime import datetime

def test_live_vector_search():
    """Test vector search against the live Cloud Run service"""
    
    # Get Cloud Run URL
    CLOUD_RUN_URL = "https://looker-explore-assistant-mcp-1031395340382.us-central1.run.app"
    
    # Test payload that should trigger vector search
    test_payload = {
        "prompt": "Show me sales for Nike products by month",
        "conversation_id": f"test_{int(datetime.now().timestamp())}",
        "prompt_history": [],
        "thread_messages": [],
        "golden_queries": {
            "exploreEntries": [
                {
                    "golden_queries.explore_id": "ecommerce:order_items"
                }
            ],
            "exploreGenerationExamples": {
                "ecommerce:order_items": [
                    {
                        "input": "Show me total sales",
                        "output": {
                            "fields": ["order_items.total_sale_price"],
                            "filters": {}
                        }
                    }
                ]
            }
        },
        "semantic_models": {
            "ecommerce:order_items": {
                "dimensions": [
                    {"name": "products.brand", "label": "Brand", "description": "Product brand name"},
                    {"name": "order_items.created_month", "label": "Created Month", "description": "Order creation month"}
                ],
                "measures": [
                    {"name": "order_items.total_sale_price", "label": "Total Sales", "description": "Total sales amount"}
                ],
                "description": "Order items with product data"
            }
        },
        "restricted_explore_keys": ["ecommerce:order_items"],
        "vertex_model": "gemini-2.0-flash-001",
        "test_mode": False
    }
    
    # Test headers - we need a valid identity token for Cloud Run
    print("🧪 Testing Vector Search Against Live Backend")
    print(f"URL: {CLOUD_RUN_URL}")
    print(f"Query: {test_payload['prompt']}")
    
    # For testing, we'll just show what the payload looks like
    print("\n📦 Test Payload Structure:")
    print(f"  Prompt: {test_payload['prompt']}")
    print(f"  Restricted Explores: {test_payload['restricted_explore_keys']}")
    print(f"  Vertex Model: {test_payload['vertex_model']}")
    print(f"  Golden Queries Keys: {list(test_payload['golden_queries'].keys())}")
    print(f"  Semantic Models Keys: {list(test_payload['semantic_models'].keys())}")
    
    print("\n⚠️  Note: This test requires a valid identity token to run against the live service.")
    print("   The frontend application handles token management for actual requests.")
    
    # Show what we expect to see in the response
    print("\n🔍 Expected Response Structure:")
    print("""
    {
        "explore_params": { ... },
        "vector_search_used": [
            {
                "function": "lookup_field_values",
                "args": {"search_string": "Nike"},
                "phase": "parameter_generation"
            }
        ],
        "vector_search_summary": {
            "total_vector_searches": 1,
            "user_messages": ["Verified existence of: Nike"],
            "detailed_usage": [ ... ]
        }
    }
    """)
    
    return test_payload

def test_debug_query():
    """Test with a query that should definitely trigger vector search"""
    
    print("\n🔬 Debug: Testing Queries That Should Trigger Vector Search")
    
    test_queries = [
        "Show me sales for Nike products",  # Brand lookup
        "Find orders with status COMPLETED", # Status lookup  
        "Products containing SKU ABC123",    # SKU search
        "Show data for region CA",           # Region code
    ]
    
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        print("    Expected: Should trigger lookup_field_values or search_semantic_fields")
        print("    Reason: Contains specific value that might need verification")
    
    print("\n❌ Queries That Should NOT Trigger Vector Search:")
    not_trigger_queries = [
        "Show me total revenue",           # General metric
        "Count of customers by month",     # Standard aggregation
        "Sales trends over time",          # Time-based analysis
    ]
    
    for query in not_trigger_queries:
        print(f"\n  Query: '{query}'")
        print("    Expected: Should NOT trigger vector search")
        print("    Reason: Uses standard fields available in explore metadata")

if __name__ == "__main__":
    test_payload = test_live_vector_search()
    test_debug_query()
    
    print("\n📝 Next Steps:")
    print("1. Check frontend console logs for vector search data in responses")
    print("2. Check backend Cloud Run logs for function call messages")
    print("3. Verify that explore metadata doesn't already contain the brand field")
    print("4. Test with more obscure values that wouldn't be in standard metadata")
