#!/usr/bin/env python3

"""
Test Vertex AI model names to ensure they're valid
"""

import os
import sys
sys.path.append('.')
from mcp_server import call_vertex_ai_with_retry

def test_model_names():
    """Test different model names to see which ones work."""
    
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-pro", 
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-001"
    ]
    
    test_request = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Say 'Hello world' in JSON format"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 50,
            "responseMimeType": "application/json"
        }
    }
    
    print("🧪 Testing Vertex AI Model Names")
    print("=" * 50)
    
    for model in models_to_test:
        print(f"\n🔍 Testing model: {model}")
        try:
            request_with_model = {**test_request, "model": model}
            
            response = call_vertex_ai_with_retry(request_with_model, f"model_test_{model}", process_response=False)
            
            if response and 'candidates' in response:
                print(f"✅ {model}: SUCCESS")
                candidate = response['candidates'][0] if response['candidates'] else {}
                if candidate.get('content'):
                    print(f"   Response: {candidate['content']['parts'][0]['text'][:50]}...")
            else:
                print(f"❌ {model}: FAILED - No valid response")
                
        except Exception as e:
            print(f"❌ {model}: ERROR - {str(e)[:100]}")

if __name__ == "__main__":
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    test_model_names()
