#!/usr/bin/env python3
"""
Test script for Olympic Query Management in Looker MCP Server

Tests the integration of Olympic Query Management system with the MCP server.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from looker_mcp_server import LookerExploreAssistantMCPServer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_olympic_query_management():
    """Test Olympic Query Management functionality"""
    
    # Set environment variables for testing
    os.environ["PROJECT"] = "combined-genai-bi"
    os.environ["BQ_PROJECT_ID"] = "ml-accelerator-dbarr"
    os.environ["BQ_DATASET_ID"] = "explore_assistant"
    
    server = LookerExploreAssistantMCPServer()
    
    # Initialize server components
    await server._ensure_bigquery_client()
    await server._ensure_olympic_manager()
    
    print("=" * 80)
    print("TESTING OLYMPIC QUERY MANAGEMENT INTEGRATION")
    print("=" * 80)
    
    # Test 1: Add Bronze Query
    print("\n1. Testing Add Bronze Query...")
    bronze_args = {
        "explore_id": "ecommerce:order_items",
        "input": "Show me total sales by brand for Q2 2023",
        "output": '{"model": "ecommerce", "view": "order_items", "fields": ["order_items.brand", "order_items.total_sale_price"]}',
        "link": "https://looker.example.com/explore/ecommerce/order_items",
        "user_email": "test@example.com",
        "query_run_count": 5
    }
    
    try:
        bronze_result = await server._handle_add_bronze_query(bronze_args)
        bronze_response = json.loads(bronze_result[0].text)
        print(f"✅ Bronze query added: {bronze_response['query_id']}")
        bronze_query_id = bronze_response['query_id']
    except Exception as e:
        print(f"❌ Bronze query failed: {e}")
        return
    
    # Test 2: Add Silver Query
    print("\n2. Testing Add Silver Query...")
    silver_args = {
        "explore_id": "ecommerce:order_items",
        "input": "Show me sales trends by month this year",
        "output": '{"model": "ecommerce", "view": "order_items", "fields": ["order_items.created_month", "order_items.total_sale_price"]}',
        "link": "https://looker.example.com/explore/ecommerce/order_items",
        "user_id": "user_123",
        "feedback_type": "positive",
        "conversation_history": "User asked for trends, refined to monthly view"
    }
    
    try:
        silver_result = await server._handle_add_silver_query(silver_args)
        silver_response = json.loads(silver_result[0].text)
        print(f"✅ Silver query added: {silver_response['query_id']}")
        silver_query_id = silver_response['query_id']
    except Exception as e:
        print(f"❌ Silver query failed: {e}")
        return
    
    # Test 3: Get Query Statistics
    print("\n3. Testing Query Statistics...")
    try:
        stats_result = await server._handle_get_query_stats({})
        stats_response = json.loads(stats_result[0].text)
        print(f"✅ Query statistics retrieved:")
        print(f"   Total queries: {stats_response['total_queries']}")
        for rank, stats in stats_response['query_statistics'].items():
            print(f"   {rank.upper()}: {stats['count']} queries")
    except Exception as e:
        print(f"❌ Query statistics failed: {e}")
    
    # Test 4: Promote Bronze to Gold
    print("\n4. Testing Bronze to Gold Promotion...")
    promote_args = {
        "query_id": bronze_query_id,
        "promoted_by": "admin@example.com"
    }
    
    try:
        promote_result = await server._handle_promote_to_gold(promote_args)
        promote_response = json.loads(promote_result[0].text)
        print(f"✅ Query promotion: {promote_response['success']}")
        print(f"   Message: {promote_response['message']}")
    except Exception as e:
        print(f"❌ Query promotion failed: {e}")
    
    # Test 5: Get Gold Queries
    print("\n5. Testing Get Gold Queries...")
    gold_args = {"explore_id": "ecommerce:order_items", "limit": 10}
    
    try:
        gold_result = await server._handle_get_gold_queries(gold_args)
        gold_response = json.loads(gold_result[0].text)
        print(f"✅ Gold queries retrieved: {gold_response['results_count']} queries")
        
        if gold_response['results_count'] > 0:
            example_query = gold_response['gold_queries'][0]
            print(f"   Example Gold Query ID: {example_query['id']}")
            print(f"   Input: {example_query['input'][:50]}...")
    except Exception as e:
        print(f"❌ Get gold queries failed: {e}")
    
    # Test 6: Updated Statistics After Promotion
    print("\n6. Testing Updated Statistics...")
    try:
        stats_result = await server._handle_get_query_stats({})
        stats_response = json.loads(stats_result[0].text)
        print(f"✅ Updated statistics:")
        print(f"   Total queries: {stats_response['total_queries']}")
        for rank, stats in stats_response['query_statistics'].items():
            print(f"   {rank.upper()}: {stats['count']} queries")
    except Exception as e:
        print(f"❌ Updated statistics failed: {e}")
    
    print("\n" + "=" * 80)
    print("OLYMPIC QUERY MANAGEMENT TESTING COMPLETE")
    print("=" * 80)

def main():
    """Main test execution"""
    try:
        asyncio.run(test_olympic_query_management())
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
