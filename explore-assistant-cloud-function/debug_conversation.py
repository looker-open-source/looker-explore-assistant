#!/usr/bin/env python3

import requests
import json
import os

def debug_conversation_request():
    """Debug the conversation request to see what's happening"""
    
    # Load test data
    with open('test_files/conversation_test.json', 'r') as f:
        test_data = json.load(f)
    
    print("🔍 Debugging Conversation History Request")
    print("=" * 50)
    
    # Show what we're sending
    print("📤 Request Data:")
    print(f"  Prompt: '{test_data['prompt']}'")
    print(f"  Prompt History: {test_data['prompt_history']}")
    print(f"  Current Explore: {test_data['current_explore']['exploreKey']}")
    
    # Check semantic models to see what fields are available
    semantic_models = test_data.get('semantic_models', {})
    explore_key = test_data['current_explore']['exploreKey']
    
    if explore_key in semantic_models:
        model = semantic_models[explore_key]
        print(f"\n🏗️  Available Fields for {explore_key}:")
        
        dimensions = model.get('dimensions', [])[:5]  # First 5 dimensions
        measures = model.get('measures', [])[:5]      # First 5 measures
        
        print("  Dimensions:")
        for dim in dimensions:
            print(f"    - {dim.get('name', 'unnamed')}: {dim.get('label', 'no label')}")
        
        print("  Measures:")
        for measure in measures:
            print(f"    - {measure.get('name', 'unnamed')}: {measure.get('label', 'no label')}")
    
    # Send request
    base_url = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"
    oauth_token = os.environ.get('OAUTH_TOKEN')
    
    if not oauth_token:
        print("❌ No OAUTH_TOKEN")
        return
    
    headers = {
        "Authorization": f"Bearer {oauth_token}",
        "Content-Type": "application/json"
    }
    
    print(f"\n🌐 Sending request to: {base_url}")
    
    try:
        response = requests.post(f"{base_url}/", json=test_data, headers=headers, timeout=30)
        
        print(f"\n📋 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📥 Response Data:")
            print(json.dumps(result, indent=2))
            
            # Analyze the response
            explore_params = result.get('explore_params', {})
            if not explore_params:
                print("\n❌ Empty explore_params!")
            elif not explore_params.get('fields'):
                print("\n⚠️  No fields in explore_params!")
                print(f"explore_params keys: {list(explore_params.keys())}")
            else:
                print(f"\n✅ Got fields: {explore_params.get('fields')}")
        else:
            print(f"❌ Request failed: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_conversation_request()
