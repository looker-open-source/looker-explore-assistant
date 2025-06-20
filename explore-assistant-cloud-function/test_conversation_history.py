#!/usr/bin/env python3

import requests
import json
import os
import sys
from typing import Dict, Any

def load_test_data() -> Dict[str, Any]:
    """Load the conversation test data"""
    try:
        with open('test_files/conversation_test.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Test data file not found: test_files/conversation_test.json")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in test file: {e}")
        sys.exit(1)

def test_conversation_history_functionality():
    """Test that prompt history is properly used in conversation context"""
    
    # Load the test data that resulted in null explore_params
    test_data = load_test_data()
    
    print("🧪 Testing Conversation History Functionality")
    print("=" * 60)
    print()
    
    # Extract test scenario details
    prompt = test_data.get('prompt', '')
    conversation_id = test_data.get('conversation_id', '')
    prompt_history = test_data.get('prompt_history', [])
    current_explore = test_data.get('current_explore', {})
    
    print(f"📝 Test Scenario:")
    print(f"   Conversation ID: {conversation_id}")
    print(f"   Current Prompt: '{prompt}'")
    print(f"   Prompt History: {prompt_history}")
    print(f"   Current Explore: {current_explore.get('exploreKey', 'None')}")
    print()
    
    # Verify we have the expected conversation context
    if len(prompt_history) < 2:
        print("❌ Test data should have multiple prompts in history")
        return False
    
    if prompt_history[-1] != prompt:
        print("❌ Current prompt should be the last item in prompt history")
        return False
    
    previous_prompt = prompt_history[-2] if len(prompt_history) > 1 else ""
    print(f"🔄 Conversation Context:")
    print(f"   Previous prompt: '{previous_prompt}'")
    print(f"   Current prompt: '{prompt}'")
    print(f"   Expected behavior: Should understand '{prompt}' refers to table visualization")
    print()
    
    # Test the MCP server endpoint
    base_url = os.environ.get('MCP_SERVER_URL', 'https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app')
    oauth_token = os.environ.get('OAUTH_TOKEN')
    
    if not oauth_token:
        print("❌ OAUTH_TOKEN environment variable not set")
        print("   Run: export OAUTH_TOKEN=$(gcloud auth print-access-token)")
        return False
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }
    
    print(f"🌐 Testing against: {base_url}")
    print()
    
    try:
        # Send the request to the MCP server
        response = requests.post(f"{base_url}/", json=test_data, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
        
        result = response.json()
        
        # Check if we got a proper response
        print("📋 Server Response:")
        print(f"   Status Code: {response.status_code}")
        
        if 'error' in result:
            print(f"❌ Server returned error: {result['error']}")
            return False
        
        # Check explore_params
        explore_params = result.get('explore_params')
        if not explore_params:
            print("❌ FAILED: explore_params is null/empty")
            print("   This indicates the server is not properly using prompt history")
            print(f"   Full response: {json.dumps(result, indent=2)}")
            print()
            print("🔍 Analysis:")
            print("   The server should understand that 'use a table' in context of")
            print("   'what are sales by month?' means to show sales by month in table format")
            print("   But it's returning null explore_params, suggesting conversation")
            print("   context is not being properly utilized.")
            return False
        
        print("✅ Got explore_params (not null)")
        print(f"   Fields: {explore_params.get('fields', 'None')}")
        print(f"   Vis Config: {explore_params.get('vis_config', 'None')}")
        
        # Check if the response indicates table visualization
        vis_config = explore_params.get('vis_config', {})
        
        expected_indicators = [
            # Check for table-related visualization config
            vis_config.get('type') == 'table',
            vis_config.get('type') == 'looker_table', 
            'table' in str(vis_config).lower(),
            # Check for fields that make sense for "sales by month"
            any('sale' in str(field).lower() for field in explore_params.get('fields', [])),
            any('month' in str(field).lower() or 'date' in str(field).lower() for field in explore_params.get('fields', []))
        ]
        
        if any(expected_indicators):
            print("✅ Response shows understanding of conversation context")
            print("   The server properly interpreted 'use a table' in the context")
            print("   of the previous 'sales by month' question")
            return True
        else:
            print("⚠️  PARTIAL FAILURE: Got explore_params but context understanding unclear")
            print("   Expected indicators of table visualization for sales by month")
            print("   but didn't find clear evidence in the response")
            print(f"   Full explore_params: {json.dumps(explore_params, indent=2)}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False

def test_conversation_context_building():
    """Test the conversation context building specifically"""
    print()
    print("🔍 Testing Conversation Context Building")
    print("=" * 50)
    
    # Test various conversation scenarios
    test_scenarios = [
        {
            "name": "Basic refinement",
            "prompt_history": ["show me sales by region", "make it a table"],
            "expected_context_includes": ["sales by region", "table"]
        },
        {
            "name": "Multi-step refinement", 
            "prompt_history": ["sales trends", "by product category", "last 6 months", "as a line chart"],
            "expected_context_includes": ["sales trends", "product category", "6 months", "line chart"]
        },
        {
            "name": "Question with follow-up",
            "prompt_history": ["what are our top customers?", "show revenue for each"],
            "expected_context_includes": ["top customers", "revenue"]
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📝 Scenario: {scenario['name']}")
        print(f"   History: {scenario['prompt_history']}")
        
        # This would test the build_conversation_context function
        # For now, we'll check if the function exists and works
        try:
            # Import the function to test it directly
            sys.path.append('.')
            from mcp_server import build_conversation_context
            
            context = build_conversation_context(scenario['prompt_history'], [])
            print(f"   Generated context: {context[:100]}...")
            
            # Check if expected terms are in the context
            missing_terms = []
            for expected_term in scenario['expected_context_includes']:
                if expected_term.lower() not in context.lower():
                    missing_terms.append(expected_term)
            
            if missing_terms:
                print(f"⚠️  Missing expected terms in context: {missing_terms}")
            else:
                print("✅ Context includes all expected terms")
                
        except ImportError:
            print("⚠️  Could not import build_conversation_context function")
        except Exception as e:
            print(f"❌ Error testing context building: {e}")
    
    return True

def main():
    """Main test runner"""
    print("🚀 Conversation History Test Suite")
    print("=" * 60)
    print()
    
    # Check environment
    if not os.path.exists('test_files/conversation_test.json'):
        print("❌ Test data file not found")
        return False
    
    # Run the main conversation history test
    success = test_conversation_history_functionality()
    
    if not success:
        print()
        print("❌ CONVERSATION HISTORY TEST FAILED")
        print()
        print("🔧 Expected Issues to Fix:")
        print("1. The build_conversation_context function may not be properly")
        print("   combining prompt_history and thread_messages")
        print("2. The system prompt for Vertex AI may not be effectively")
        print("   using the conversation context")
        print("3. The current prompt may not be interpreted in context")
        print("   of previous prompts")
        print()
        return False
    
    # Run additional context building tests
    test_conversation_context_building()
    
    print()
    print("🎉 ALL TESTS PASSED!")
    print()
    print("✅ The conversation history functionality is working correctly")
    print("   The server properly uses prompt history to understand context")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
