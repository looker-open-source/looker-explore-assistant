#!/usr/bin/env python3

"""
Test the integrated enhanced vector search in MCP server
"""

import requests
import json
import time
import subprocess
import signal
import os
from threading import Timer

def start_server():
    """Start the MCP server in background"""
    print("🚀 Starting MCP server...")
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        'LOOKER_BASE_URL': 'dummy',
        'LOOKER_CLIENT_ID': 'dummy', 
        'LOOKER_CLIENT_SECRET': 'dummy',
        'GOOGLE_CLOUD_PROJECT': 'ml-accelerator-dbarr'
    })
    
    # Start server
    proc = subprocess.Popen(
        ['python3', 'mcp_server.py'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid
    )
    
    # Wait for server to start
    time.sleep(5)
    return proc

def test_enhanced_vector_search():
    """Test the enhanced vector search integration"""
    
    # Start server
    server_proc = start_server()
    
    try:
        # Test queries with different entity types
        test_cases = [
            {
                "name": "Single Brand Query",
                "prompt": "Show me sales for Nike products",
                "expected_entities": ["Nike"]
            },
            {
                "name": "Multiple Brand Query", 
                "prompt": "Compare revenue for Nike vs Adidas vs 55DSL brands",
                "expected_entities": ["Nike", "Adidas", "55DSL"]
            },
            {
                "name": "Product Code Query",
                "prompt": "Find sales data for product code 686",
                "expected_entities": ["686"]
            },
            {
                "name": "Mixed Entity Query",
                "prompt": "Show BDI and Barmah Hats performance this year",
                "expected_entities": ["BDI", "Barmah Hats"]
            },
            {
                "name": "No Entity Query",
                "prompt": "What was our total revenue last quarter?",
                "expected_entities": []
            }
        ]
        
        print("🧪 TESTING ENHANCED VECTOR SEARCH INTEGRATION")
        print("=" * 60)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🔍 Test {i}: {test_case['name']}")
            print(f"Query: {test_case['prompt']}")
            print("-" * 40)
            
            # Construct request
            payload = {
                "tool_name": "generate_explore_params",
                "arguments": {
                    "prompt": test_case['prompt'],
                    "restricted_explore_keys": ["sales_demo_the_look:order_items"],
                    "conversation_context": {
                        "previous_queries": [],
                        "current_explore": None,
                        "user_intent": "test enhanced vector search"
                    }
                }
            }
            
            try:
                # Make request to server
                response = requests.post(
                    "http://localhost:8001",
                    headers={
                        "Authorization": "Bearer ya29.test_token",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    print("✅ Request successful!")
                    
                    # Check for vector search usage
                    vector_search_used = result.get('vector_search_used', [])
                    vector_search_summary = result.get('vector_search_summary', {})
                    
                    if vector_search_used:
                        print(f"🔍 Vector search executed: {len(vector_search_used)} operations")
                        for usage in vector_search_used:
                            print(f"   - {usage.get('function', 'unknown')}: {usage.get('results_summary', 'no summary')}")
                    else:
                        print("⚪ No vector search operations")
                    
                    if vector_search_summary:
                        print(f"📊 Summary: {vector_search_summary.get('total_vector_searches', 0)} searches")
                        user_messages = vector_search_summary.get('user_messages', [])
                        for msg in user_messages:
                            print(f"   - {msg}")
                    
                    # Check explore params
                    explore_params = result.get('explore_params', {})
                    filters = explore_params.get('filters', {})
                    
                    if filters:
                        print(f"🎯 Filters created: {filters}")
                    else:
                        print("⚪ No filters created")
                        
                else:
                    print(f"❌ Request failed: {response.status_code}")
                    print(f"Error: {response.text}")
                    
            except Exception as e:
                print(f"❌ Request error: {e}")
            
            print(f"{'='*40}")
        
        print(f"\n✅ All tests completed!")
        
    finally:
        # Kill server
        print("\n🛑 Stopping server...")
        os.killpg(os.getpgid(server_proc.pid), signal.SIGTERM)
        server_proc.wait()

if __name__ == "__main__":
    test_enhanced_vector_search()
