#!/usr/bin/env python3
"""
Test script to specifically test if LLMs are calling vector search functions
"""

import os
import sys
import json
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_llm_function_calling_direct():
    """Test function calling directly via Vertex AI API"""
    
    # Use the Bearer token from TOKEN environment variable
    token = os.environ.get("TOKEN")
    if not token:
        print("❌ No TOKEN environment variable found")
        print("Please run: export TOKEN='your_bearer_token_here'")
        return False
    
    # Define function declarations that should trigger easily
    function_declarations = [
        {
            "name": "search_semantic_fields",
            "description": "REQUIRED: Always call this function when user mentions ANY brand name, product name, or identifier. This is MANDATORY for brands like Nike, Adidas, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Brand names or identifiers to search for"
                    }
                },
                "required": ["search_terms"]
            }
        },
        {
            "name": "lookup_field_values",
            "description": "REQUIRED: Always call this function to verify brand names exist. You MUST call this for ANY brand mentioned.",
            "parameters": {
                "type": "object", 
                "properties": {
                    "search_string": {
                        "type": "string",
                        "description": "Brand name to verify"
                    }
                },
                "required": ["search_string"]
            }
        }
    ]
    
    # Test different prompts with increasing explicitness
    test_prompts = [
        "Show me sales for Nike products",
        "Find Nike sales using vector search",
        "I need sales data for Nike brand. You MUST use the lookup_field_values function to find Nike.",
        "Call the lookup_field_values function with 'Nike' as the search_string parameter",
        "INSTRUCTION: Before generating any response, you must call lookup_field_values('Nike'). This is mandatory."
    ]
    
    project = os.environ.get("PROJECT", "ml-accelerator-dbarr")
    location = "us-central1"
    model = "gemini-2.0-flash-001"
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n🧪 Test {i}: {prompt[:50]}...")
        
        # Vertex AI request
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "tools": [{"function_declarations": function_declarations}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
                "candidateCount": 1
            }
        }
        
        try:
            # Call Vertex AI directly
            url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{model}:generateContent"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=vertex_request)
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                continue
                
            result = response.json()
            
            # Check for function calls
            function_called = False
            if 'candidates' in result:
                candidate = result['candidates'][0]
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                
                for part in parts:
                    if 'functionCall' in part:
                        function_call = part['functionCall']
                        function_name = function_call['name']
                        function_args = function_call.get('args', {})
                        print(f"✅ FUNCTION CALLED: {function_name}({function_args})")
                        function_called = True
                    elif 'text' in part:
                        print(f"📝 Text response: {part['text'][:100]}...")
            
            if not function_called:
                print(f"❌ No function calls detected")
                # Print the full response for debugging
                print(f"📋 Full response: {json.dumps(result, indent=2)}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return True

def test_via_mcp_server():
    """Test function calling via our MCP server"""
    print(f"\n🔧 Testing via MCP Server...")
    
    token = os.environ.get("TOKEN")
    if not token:
        print("❌ No TOKEN environment variable found")
        return False
    
    # Test via our MCP server
    mcp_request = {
        "tool_name": "generate_explore_params",
        "arguments": {
            "prompt": "Show me sales for Nike products - use vector search to find the Nike field",
            "restricted_explore_keys": ["sales_demo_the_look:order_items"],
            "conversation_context": ""
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:8001",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json=mcp_request
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ MCP Server Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ MCP Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ MCP Error: {e}")

def main():
    print("🚀 Testing LLM Function Calling for Vector Search")
    print("=" * 60)
    
    print("This test will check if LLMs actually call the vector search functions")
    print("when presented with brand names or specific identifiers.")
    
    # Test direct API calls
    test_llm_function_calling_direct()
    
    # Test via our MCP server
    test_via_mcp_server()
    
    print("\n" + "=" * 60)
    print("🏁 Function Calling Test Complete")

if __name__ == "__main__":
    main()
