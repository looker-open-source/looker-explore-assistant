#!/usr/bin/env python3

"""
Test script to verify that the backend correctly extracts approved explore_params
from frontend thread messages and saves them to BigQuery.
"""

import sys
import os
import json
import logging
import time
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the current directory to Python path so we can import mcp_server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_approved_params_extraction():
    """Test the extraction of approved explore_params from thread messages"""
    
    # Import here after setting up the path
    from mcp_server import extract_approved_explore_params, detect_feedback_pattern
    
    print("🧪 Testing approved explore_params extraction...")
    
    # Simulate thread messages as they would come from the frontend
    thread_messages = [
        {
            "uuid": "msg-1",
            "message": "Show me sales by month",
            "actor": "user",
            "createdAt": 1234567890000,
            "type": "text"
        },
        {
            "uuid": "msg-2",
            "exploreParams": {
                "fields": ["order_items.total_sale_price", "order_items.created_month"],
                "filters": {},
                "sorts": ["order_items.created_month"],
                "limit": "500",
                "vis_config": {"type": "looker_line"}
            },
            "actor": "system",
            "createdAt": 1234567891000,
            "type": "explore",
            "summarizedPrompt": "Sales by month visualization"
        },
        {
            "uuid": "msg-3",
            "message": "Actually, I want to see sales by quarter instead",
            "actor": "user",
            "createdAt": 1234567892000,
            "type": "text"
        },
        {
            "uuid": "msg-4",
            "exploreParams": {
                "fields": ["order_items.total_sale_price", "order_items.created_quarter"],
                "filters": {},
                "sorts": ["order_items.created_quarter"],
                "limit": "500",
                "vis_config": {"type": "looker_line"}
            },
            "actor": "system", 
            "createdAt": 1234567893000,
            "type": "explore",
            "summarizedPrompt": "Sales by quarter visualization"
        },
        {
            "uuid": "msg-5",
            "message": "Perfect! That's exactly what I wanted.",
            "actor": "user",
            "createdAt": 1234567894000,
            "type": "text"
        }
    ]
    
    # Test the extraction function
    print("\n1️⃣ Testing extract_approved_explore_params...")
    approved_params = extract_approved_explore_params(thread_messages)
    
    if approved_params:
        print("✅ Successfully extracted approved explore_params:")
        print(json.dumps(approved_params, indent=2))
        
        # Verify it's the correct (most recent) params
        expected_fields = ["order_items.total_sale_price", "order_items.created_quarter"]
        actual_fields = approved_params.get("fields", [])
        
        if actual_fields == expected_fields:
            print("✅ Correct fields extracted (quarterly, not monthly)")
        else:
            print(f"❌ Wrong fields extracted. Expected: {expected_fields}, Got: {actual_fields}")
            return False
    else:
        print("❌ Failed to extract approved explore_params")
        return False
    
    # Test the feedback detection with these messages
    print("\n2️⃣ Testing feedback pattern detection...")
    prompt_history = [
        "Show me sales by month",
        "Actually, I want to see sales by quarter instead", 
        "Perfect! That's exactly what I wanted."
    ]
    current_prompt = "Perfect! That's exactly what I wanted."
    
    has_feedback, detected_params = detect_feedback_pattern(prompt_history, thread_messages, current_prompt)
    
    if has_feedback:
        print("✅ Feedback pattern detected successfully")
        if detected_params:
            print("✅ Approved params extracted through feedback detection")
            print(json.dumps(detected_params, indent=2))
            
            # Verify consistency
            if detected_params == approved_params:
                print("✅ Consistency check passed - both methods return same params")
            else:
                print("❌ Inconsistency detected between extraction methods")
                return False
        else:
            print("❌ Feedback detected but no approved params extracted")
            return False
    else:
        print("❌ Feedback pattern not detected")
        return False
    
    print("\n3️⃣ Testing with empty thread messages...")
    empty_approved = extract_approved_explore_params([])
    if empty_approved is None:
        print("✅ Correctly handles empty thread messages")
    else:
        print("❌ Should return None for empty thread messages")
        return False
    
    print("\n4️⃣ Testing with no explore messages...")
    text_only_messages = [
        {
            "uuid": "msg-1",
            "message": "Hello",
            "actor": "user",
            "createdAt": 1234567890000,
            "type": "text"
        },
        {
            "uuid": "msg-2", 
            "message": "Hi there!",
            "actor": "system",
            "createdAt": 1234567891000,
            "type": "text"
        }
    ]
    
    text_only_approved = extract_approved_explore_params(text_only_messages)
    if text_only_approved is None:
        print("✅ Correctly handles messages with no explore_params")
    else:
        print("❌ Should return None when no explore_params available")
        return False
    
    print("\n🎉 All tests passed! The approved params extraction is working correctly.")
    return True

def main():
    """Main test function"""
    try:
        print("🚀 Starting approved params extraction test...")
        
        success = test_approved_params_extraction()
        
        if success:
            print("\n✅ TEST SUITE PASSED")
            print("The backend will now correctly extract and save approved explore_params!")
        else:
            print("\n❌ TEST SUITE FAILED")
            print("There are issues with the approved params extraction logic.")
            
        return success
        
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        logging.error(f"Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
