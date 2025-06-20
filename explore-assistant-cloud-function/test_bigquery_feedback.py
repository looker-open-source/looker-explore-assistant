#!/usr/bin/env python3

"""
Quick test for BigQuery feedback saving
"""

import requests
import json
import os

# Test URL
url = "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app"

# Get OAuth token
oauth_token = os.popen("gcloud auth print-access-token").read().strip()

headers = {
    "Authorization": f"Bearer {oauth_token}",
    "Content-Type": "application/json"
}

# Simple feedback test data
test_data = {
    "prompt": "Perfect! That's exactly what I wanted, thank you",
    "conversation_id": "test-feedback-123",
    "prompt_history": [
        "Show me sales data by region",
        "This chart is incorrect, I need a table instead", 
        "Perfect! That's exactly what I wanted, thank you"
    ],
    "thread_messages": [
        {"message": "This visualization is not right", "actor": "user"},
        {"message": "I've corrected it to show a table", "actor": "system"}
    ],
    "current_explore": {
        "exploreKey": "sales_demo_the_look:order_items"
    },
    "golden_queries": {},
    "semantic_models": {
        "sales_demo_the_look:order_items": {
            "dimensions": [
                {"name": "orders.created_date", "type": "date", "label": "Created Date"},
                {"name": "distribution_centers.name", "type": "string", "label": "Distribution Center"}
            ],
            "measures": [
                {"name": "order_items.total_sale_price", "type": "number", "label": "Total Sale Price"}
            ]
        }
    },
    "model_name": "sales_demo_the_look",
    "test_mode": False
}

print("🧪 Testing BigQuery Feedback Saving")
print("=" * 50)

try:
    response = requests.post(url, headers=headers, json=test_data, timeout=60)
    print(f"✅ Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"📝 Summary: {result.get('summary', 'No summary')}")
        print(f"🎯 Feedback detected: {'feedback_message' in result}")
        
        if 'feedback_message' in result:
            print(f"💬 Feedback message: '{result['feedback_message']}'")
            print("🎉 SUCCESS: Feedback system working!")
        else:
            print("❌ No feedback message detected")
            print(f"Available keys: {list(result.keys())}")
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n🔍 Checking BigQuery for new records...")
os.system('bq query --use_legacy_sql=false --format=table "SELECT * FROM `ml-accelerator-dbarr.explore_assistant.suggested_golden_queries` ORDER BY timestamp DESC LIMIT 5"')
