#!/usr/bin/env python3

"""
Final test of function calling behavior - bypassing MCP server authentication
to directly test the Vertex AI function calling implementation.
"""

import os
import asyncio
import json
import sys
sys.path.append('.')
from mcp_server import call_vertex_ai_with_retry
from field_lookup_service import FieldValueLookupService

# Test data
TEST_CASES = [
    {
        "name": "Nike (popular brand)",
        "prompt": "Show me sales for Nike brand products. You must use vector search to find the exact field location.",
        "brand": "Nike"
    },
    {
        "name": "Barmah Hats (extremely obscure brand)",
        "prompt": "Show me sales for Barmah Hats brand products. 🚨 CRITICAL: This is an extremely obscure Australian leather hat brand that you definitely do not know about. YOU ABSOLUTELY MUST use the lookup_field_values function to find where this brand exists in the database before creating any filters. DO NOT GUESS the field location.",
        "brand": "Barmah"
    }
]

async def test_function_calling_direct():
    """Test function calling by calling Vertex AI directly with function declarations."""
    
    print("🧪 Testing Function Calling with Direct Vertex AI API Calls")
    print("=" * 60)
    
    # Initialize field lookup service
    field_service = FieldValueLookupService()
    
    # Function declarations for Vertex AI (same as in MCP server)
    function_declarations = [
        {
            "name": "lookup_field_values",
            "description": "Find specific dimension values in indexed fields. Use this to locate where specific brand names, product codes, or other values exist in the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_string": {
                        "type": "string",
                        "description": "The value to search for (e.g., brand name, product code)"
                    },
                    "field_location": {
                        "type": "string",
                        "description": "Optional specific field to search in"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "Maximum number of results to return"
                    }
                },
                "required": ["search_string"]
            }
        }
    ]
    
    for test_case in TEST_CASES:
        print(f"\n🔍 Testing: {test_case['name']}")
        print(f"Brand: {test_case['brand']}")
        print(f"Prompt: {test_case['prompt']}")
        
        # First verify the brand exists in our data
        print(f"\n📊 Checking if {test_case['brand']} exists in vector database...")
        try:
            results = await field_service.field_value_lookup(test_case['brand'], None, 3)
            if results:
                print(f"✅ Found {len(results)} matches:")
                for result in results:
                    print(f"  - {result['field_location']}: {result['field_value']} (freq: {result['value_frequency']})")
            else:
                print(f"❌ No matches found for {test_case['brand']}")
                continue
        except Exception as e:
            print(f"❌ Error checking brand: {e}")
            continue
        
        # Now test with Vertex AI function calling
        print(f"\n🤖 Testing Vertex AI with function calling...")
        
        system_prompt = f"""You are a Looker query assistant. Your task is to help users create filters for their queries.

🚨 CRITICAL FUNCTION CALLING REQUIREMENTS:
- When a user asks about specific brand names, product codes, or other specific values, you MUST use the lookup_field_values function
- You are FORBIDDEN from guessing field locations or hardcoding field names
- Every brand name or specific value must be looked up using the provided functions

Available explore: sales_demo_the_look:order_items

Your response should be a JSON object with the following structure:
{{
  "model": "sales_demo_the_look",
  "explore": "order_items", 
  "fields": ["order_items.count", "inventory_items.total_sale_price"],
  "filters": {{
    "field_name": "value"
  }}
}}"""

        try:
            # Construct Vertex AI request body (same format as MCP server)
            vertex_request = {
                "model": "gemini-2.0-flash-exp",
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": test_case['prompt']}]
                    }
                ],
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "tools": [{"function_declarations": function_declarations}],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.5,
                    "topK": 20,
                    "maxOutputTokens": 1000,
                    "responseMimeType": "application/json",
                    "candidateCount": 1
                }
            }
            
            # Call Vertex AI with function declarations
            response = call_vertex_ai_with_retry(vertex_request, "function_calling_test", process_response=False)
            
            print(f"🤖 Raw Vertex AI Response:")
            print(json.dumps(response, indent=2))
            
            # Check if functions were called in the response
            if response and 'candidates' in response:
                candidate = response['candidates'][0] if response['candidates'] else {}
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                
                function_calls_found = []
                for part in parts:
                    if 'functionCall' in part:
                        function_calls_found.append(part['functionCall'])
                
                if function_calls_found:
                    print(f"✅ Function calls detected: {len(function_calls_found)}")
                    for i, call in enumerate(function_calls_found):
                        print(f"  Function {i+1}: {call.get('name', 'Unknown')} with args: {call.get('args', {})}")
                else:
                    print(f"❌ NO FUNCTION CALLS DETECTED")
                    
        except Exception as e:
            print(f"❌ Error in Vertex AI call: {e}")
            import traceback
            traceback.print_exc()
        
        print("-" * 40)

if __name__ == "__main__":
    # Set up environment
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    
    # Run the test
    asyncio.run(test_function_calling_direct())
