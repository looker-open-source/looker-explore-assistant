#!/usr/bin/env python3
"""
Test script for the Looker Explore Assistant MCP Server

This script demonstrates how to use the MCP server's field discovery capabilities
without running it as a full MCP server.
"""

import asyncio
import json
from looker_mcp_server import LookerExploreAssistantMCPServer

async def test_semantic_field_search():
    """Test the semantic field search functionality"""
    print("🧪 Testing Semantic Field Search...")
    
    server = LookerExploreAssistantMCPServer()
    
    # Test arguments for semantic field search
    test_args = {
        "search_terms": ["brand", "customer", "revenue"],
        "limit_per_term": 3,
        "similarity_threshold": 0.1
    }
    
    try:
        result = await server._handle_semantic_field_search(test_args)
        response_data = json.loads(result[0].text)
        
        print(f"✅ Found {response_data['results_count']} field matches")
        
        for i, match in enumerate(response_data['field_matches'][:5], 1):
            print(f"\n{i}. {match['field_location']} ({match['field_type']})")
            print(f"   Search term: {match['search_term']}")
            print(f"   Similarity: {match['similarity']:.3f}")
            
            if match['matching_values']:
                sample_values = [v['value'] for v in match['matching_values'][:3]]
                print(f"   Sample values: {sample_values}")
        
    except Exception as e:
        print(f"❌ Semantic field search failed: {e}")

async def test_field_value_lookup():
    """Test the field value lookup functionality"""
    print("\n🔍 Testing Field Value Lookup...")
    
    server = LookerExploreAssistantMCPServer()
    
    # Test arguments for field value lookup
    test_args = {
        "search_string": "nike",
        "limit": 5
    }
    
    try:
        result = await server._handle_field_value_lookup(test_args)
        response_data = json.loads(result[0].text)
        
        print(f"✅ Found {response_data['results_count']} matching values")
        
        for i, match in enumerate(response_data['matching_values'], 1):
            print(f"{i}. {match['field_location']}: {match['field_value']}")
            print(f"   Frequency: {match['value_frequency']}")
        
    except Exception as e:
        print(f"❌ Field value lookup failed: {e}")

async def test_generate_explore_params():
    """Test the generate explore params functionality (core Explore Assistant feature)"""
    print("\n🔧 Testing Generate Explore Params...")
    
    server = LookerExploreAssistantMCPServer()
    
    # Test arguments for generating explore parameters
    test_args = {
        "user_prompt": "Show me sales by brand for orders in the last 30 days",
        "explore_id": "sales_demo_the_look:order_items",
        "include_context": True
    }
    
    try:
        result = await server._handle_generate_explore_params(test_args)
        response_data = json.loads(result[0].text)
        
        print("✅ Generated explore parameters successfully")
        print(f"Model: {response_data.get('model', 'N/A')}")
        print(f"Explore: {response_data.get('explore', 'N/A')}")
        
        if 'dimensions' in response_data:
            print(f"Dimensions: {response_data['dimensions']}")
        if 'measures' in response_data:
            print(f"Measures: {response_data['measures']}")
        if 'filters' in response_data:
            print(f"Filters: {response_data['filters']}")
        
    except Exception as e:
        print(f"⚠️  Generate explore params test: {e}")
        print("   This is expected if Looker SDK is not fully configured")

async def test_run_looker_query():
    """Test running a Looker query"""
    print("\n� Testing Run Looker Query...")
    
    server = LookerExploreAssistantMCPServer()
    
    # Test arguments for running a Looker query - using correct API format
    # Note: Looker API uses 'view' as the legacy parameter name for 'explore'
    # and combines dimensions/measures into a single 'fields' array
    test_args = {
        "query_body": {
            "model": "sales_demo_the_look",
            "view": "order_items",  # Legacy parameter name for explore
            "fields": [
                "inventory_items.product_brand",    # Dimension
                "order_items.total_sale_price"      # Measure
            ],
            "limit": 5,
            "query_timezone": "America/Los_Angeles"
        },
        "result_format": "json"
    }
    
    try:
        result = await server._handle_run_looker_query(test_args)
        response_data = json.loads(result[0].text)
        
        if "result" in response_data and response_data["result"]:
            query_results = response_data["result"]
            print(f"✅ Query executed successfully!")
            print(f"  Returned {len(query_results)} rows")
            
            # Show first few results
            for i, row in enumerate(query_results[:3]):
                brand = row.get("products.brand", "N/A")
                count = row.get("order_items.count", "N/A")
                print(f"  {i+1}. Brand: {brand}, Count: {count}")
                
        else:
            print(f"⚠️  Query executed but no results: {response_data}")
        
    except Exception as e:
        print(f"⚠️  Run Looker query test: {e}")
        print("   This is expected if Looker SDK is not fully configured")

async def test_generate_explore_params():
    """Test the core explore parameter generation functionality"""
    print("\n🎯 Testing Generate Explore Parameters (CORE FUNCTIONALITY)...")
    
    server = LookerExploreAssistantMCPServer()
    
    # Test arguments for explore parameter generation
    test_args = {
        "prompt": "Show me sales by brand for the top 10 brands in 2023",
        "explore_key": "sales_demo_the_look:order_items",
        "conversation_context": "",
        "golden_queries": {},
        "semantic_models": {}
    }
    
    try:
        result = await server._handle_generate_explore_params(test_args)
        response_data = json.loads(result[0].text)
        
        if "explore_params" in response_data:
            params = response_data["explore_params"]
            print("✅ Explore parameters generated successfully!")
            print(f"   Model: {params.get('model')}")
            print(f"   Explore: {params.get('explore')}")
            print(f"   Dimensions: {params.get('dimensions', [])}")
            print(f"   Measures: {params.get('measures', [])}")
            print(f"   Filters: {params.get('filters', {})}")
            print(f"   Limit: {params.get('limit')}")
        else:
            print(f"❌ No explore_params in response: {response_data}")
        
    except Exception as e:
        print(f"❌ Generate explore params failed: {e}")

async def main():
    """Run all tests"""
    print("🚀 Testing Looker Explore Assistant MCP Server")
    print("=" * 50)
    
    # Test field discovery capabilities
    await test_semantic_field_search()
    await test_field_value_lookup()
    
    # Test Looker integration capabilities
    await test_run_looker_query()
    await test_generate_explore_params()
    
    # Test Vertex AI proxy (optional - requires proper auth)
    # await test_vertex_ai_query()
    
    print("\n" + "=" * 50)
    print("🎉 MCP Server Testing Complete!")
    print("\n📋 Summary of Available MCP Tools:")
    print("  • generate_explore_params - 🎯 CORE: Convert natural language to Looker queries")
    print("  • semantic_field_search - Find fields using AI similarity")
    print("  • field_value_lookup - Find specific values in fields")
    print("  • vertex_ai_query - Secure Vertex AI API access")
    print("  • get_explore_fields - Get available Looker fields")
    print("  • run_looker_query - Execute Looker queries")
    
    print("\n🔧 To use as MCP Server:")
    print("  python3 looker_mcp_server.py")
    
    print("\n💡 To use with Claude Desktop:")
    print("  Add to ~/Library/Application Support/Claude/claude_desktop_config.json")

if __name__ == "__main__":
    asyncio.run(main())
