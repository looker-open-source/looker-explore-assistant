#!/usr/bin/env python3

"""
Test script for feedback detection with deployed backend
Simulates a conversation where user gives feedback and confirms correction
"""

import requests
import json
import os
import time

# Configuration
SERVER_URL = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"
OAUTH_TOKEN = os.environ.get('OAUTH_TOKEN') or 'your-oauth-token-here'

def test_feedback_conversation():
    """Test a complete feedback conversation cycle"""
    
    print("🧪 Testing Feedback Detection with Deployed Backend")
    print("=" * 60)
    
    # Load test data
    with open('test_files/conversation_test.json', 'r') as f:
        base_data = json.load(f)
    
    # Simulate a feedback conversation cycle
    conversation_steps = [
        {
            "step": 1,
            "description": "Initial request for sales data",
            "prompt": "Show me sales data by region",
            "prompt_history": ["Show me sales data by region"],
            "thread_messages": [],
            "expected_feedback": False
        },
        {
            "step": 2, 
            "description": "User feedback - visualization is wrong",
            "prompt": "This chart is incorrect, I need a table instead",
            "prompt_history": [
                "Show me sales data by region",
                "This chart is incorrect, I need a table instead"
            ],
            "thread_messages": [
                {"message": "Here's your sales data visualization", "actor": "system", "type": "response"}
            ],
            "expected_feedback": False  # No confirmation yet
        },
        {
            "step": 3,
            "description": "User confirms correction is good",
            "prompt": "Perfect! That's exactly what I wanted, thank you",
            "prompt_history": [
                "Show me sales data by region",
                "This chart is incorrect, I need a table instead", 
                "Perfect! That's exactly what I wanted, thank you"
            ],
            "thread_messages": [
                {"message": "Here's your sales data visualization", "actor": "system", "type": "response"},
                {"message": "I've corrected it to show a table format", "actor": "system", "type": "response"}
            ],
            "expected_feedback": True  # Should detect feedback pattern
        }
    ]
    
    headers = {
        'Authorization': f'Bearer {OAUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    for step_data in conversation_steps:
        print(f"\n📍 Step {step_data['step']}: {step_data['description']}")
        
        # Prepare request data
        request_data = base_data.copy()
        request_data.update({
            'prompt': step_data['prompt'],
            'prompt_history': step_data['prompt_history'],
            'thread_messages': step_data['thread_messages'],
            'conversation_id': f'test_feedback_{int(time.time())}'
        })
        
        print(f"   Prompt: '{step_data['prompt']}'")
        print(f"   Expected feedback detection: {step_data['expected_feedback']}")
        
        try:
            # Make request to backend
            response = requests.post(SERVER_URL, 
                                   headers=headers, 
                                   json=request_data,
                                   timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # Check for feedback message
                has_feedback_message = 'feedback_message' in result
                feedback_message = result.get('feedback_message', '')
                
                print(f"   ✅ Status: {response.status_code}")
                print(f"   📝 Summary: {result.get('summary', 'No summary')}")
                print(f"   🎯 Feedback detected: {has_feedback_message}")
                
                if has_feedback_message:
                    print(f"   💬 Feedback message: '{feedback_message}'")
                    print(f"   🏆 SUCCESS: Feedback pattern detected and saved!")
                    
                    # Check if explore_params are present (should not be changed)
                    if result.get('explore_params'):
                        print(f"   ✅ Explore params preserved: {bool(result.get('explore_params').get('fields'))}")
                    
                elif step_data['expected_feedback']:
                    print(f"   ⚠️  WARNING: Expected feedback detection but none found")
                else:
                    print(f"   ✅ Correctly no feedback detected")
                    
                # Show explore_params status
                explore_params = result.get('explore_params', {})
                fields = explore_params.get('fields', [])
                print(f"   📊 Fields returned: {len(fields)} fields")
                
            else:
                print(f"   ❌ Error: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print("-" * 50)
    
    print("\n🎯 Test Summary:")
    print("- Step 1: Initial request (no feedback expected)")
    print("- Step 2: User gives feedback (no confirmation yet)")  
    print("- Step 3: User confirms correction (feedback pattern should be detected)")
    print("\nLook for the feedback message in Step 3 to confirm the feature works!")

def test_simple_feedback():
    """Test a simple feedback scenario"""
    print("\n🔍 Testing Simple Feedback Scenario")
    print("=" * 40)
    
    headers = {
        'Authorization': f'Bearer {OAUTH_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    # Load base test data
    with open('test_files/conversation_test.json', 'r') as f:
        request_data = json.load(f)
    
    # Override with feedback conversation
    request_data.update({
        'prompt': 'Great! That works perfectly, thank you',
        'prompt_history': [
            'Show me order data',
            'This is wrong, I want a table',
            'Great! That works perfectly, thank you'
        ],
        'thread_messages': [
            {'message': 'Here is your visualization', 'actor': 'system'},
            {'message': 'I need this in table format instead', 'actor': 'user'},
            {'message': 'Here is the corrected table view', 'actor': 'system'}
        ],
        'conversation_id': f'simple_feedback_{int(time.time())}'
    })
    
    try:
        response = requests.post(SERVER_URL, 
                               headers=headers, 
                               json=request_data,
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✅ Response received successfully")
            print(f"📝 Summary: {result.get('summary', 'No summary')}")
            
            if 'feedback_message' in result:
                print(f"🎉 FEEDBACK DETECTED!")
                print(f"💬 Message: {result['feedback_message']}")
                print(f"👤 This should be saved with user email from OAuth token")
            else:
                print(f"⚠️  No feedback message detected")
                
            # Show what would be saved
            explore_params = result.get('explore_params', {})
            if explore_params:
                print(f"💾 Would save explore_params with {len(explore_params.get('fields', []))} fields")
                
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    # Check if OAuth token is set
    if OAUTH_TOKEN == 'your-oauth-token-here':
        print("⚠️  Please set your OAUTH_TOKEN environment variable")
        print("   export OAUTH_TOKEN='your-actual-token'")
        exit(1)
    
    print(f"🌐 Testing against: {SERVER_URL}")
    print(f"🔑 Using OAuth token: {OAUTH_TOKEN[:20]}...")
    
    # Run tests
    test_feedback_conversation()
    test_simple_feedback()
    
    print("\n✅ Testing complete!")
