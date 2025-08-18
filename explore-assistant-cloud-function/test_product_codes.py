#!/usr/bin/env python3

"""
Testing function calling with product codes - these should definitely trigger vector search
since LLMs wouldn't know specific product codes like '686', '55DSL', 'BDI'.
"""

import os
import asyncio
import json
import sys
sys.path.append('.')
from mcp_server import call_vertex_ai_with_retry
from field_lookup_service import FieldValueLookupService

# Test cases with product codes that exist in data
PRODUCT_CODE_TESTS = [
    {
        "name": "Numeric code 686",
        "prompt": "Show me sales for products with code 686. 🚨 MANDATORY: You must use lookup_field_values function to find where code 686 exists in the database. Do not guess any field names.",
        "code": "686"
    },
    {
        "name": "Brand code 55DSL", 
        "prompt": "Show me sales for 55DSL products. This is a specific product code that requires vector search lookup to find the correct field location.",
        "code": "55DSL"
    },
    {
        "name": "product code 02013105F0430DE65B8B1408D52C84BE",
        "prompt": "Find sales data for 02013105F0430DE65B8B1408D52C84BE product code. This is a specific product code that requires vector search lookup to find the correct field location.",
        "code": "02013105F0430DE65B8B1408D52C84BE"
    }
]

async def test_product_code_function_calling():
    """Test if LLMs will use functions for product codes vs brand names."""
    
    print("🧪 Testing Function Calling with Product Codes")
    print("=" * 50)
    
    # Initialize field lookup service
    field_service = FieldValueLookupService()
    
    # Function declarations (same as MCP server)
    function_declarations = [
        {
            "name": "lookup_field_values",
            "description": "Find specific dimension values in indexed fields. REQUIRED for all product codes, SKUs, and specific identifiers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_string": {
                        "type": "string",
                        "description": "The code/value to search for"
                    },
                    "limit": {
                        "type": "integer", 
                        "description": "Maximum results",
                        "default": 5
                    }
                },
                "required": ["search_string"]
            }
        }
    ]
    
    for test_case in PRODUCT_CODE_TESTS:
        print(f"\n{'='*60}")
        print(f"🔍 TESTING: {test_case['name']}")
        print(f"Code: '{test_case['code']}'")
        print(f"Prompt: {test_case['prompt']}")
        
        # Verify the code exists
        print(f"\n📊 Checking if '{test_case['code']}' exists in vector database...")
        try:
            results = await field_service.field_value_lookup(test_case['code'], None, 3)
            if results:
                print(f"✅ Found {len(results)} matches:")
                for result in results:
                    print(f"  - {result['field_location']}")
                    print(f"    Value: {result['field_value'][:50]}{'...' if len(result['field_value']) > 50 else ''}")
                    print(f"    Frequency: {result['value_frequency']}")
            else:
                print(f"❌ No matches found for '{test_case['code']}' - skipping")
                continue
        except Exception as e:
            print(f"❌ Error checking code: {e}")
            continue
        
        print(f"\n🤖 Testing Vertex AI with function calling...")
        
        # Strong system prompt emphasizing function calling
        system_prompt = f"""You are a Looker query assistant. You help users find data by creating proper filters.

🚨🚨🚨 CRITICAL FUNCTION CALLING RULES 🚨🚨🚨
- For ANY product code, SKU, or identifier mentioned by the user, you MUST use lookup_field_values function
- You are ABSOLUTELY FORBIDDEN from guessing field locations  
- You CANNOT create filters without first calling lookup_field_values
- If you try to guess field names, the query will fail

Available explore: sales_demo_the_look:order_items

Response format (JSON):
{{
  "model": "sales_demo_the_look",
  "explore": "order_items",
  "fields": ["order_items.count", "inventory_items.total_sale_price"],
  "filters": {{
    "exact_field_name_from_function": "exact_value_from_function"
  }}
}}"""

        try:
            # Construct Vertex AI request with strong function requirements
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
                    "temperature": 0.0,  # Zero temperature for consistency
                    "maxOutputTokens": 1000,
                    "responseMimeType": "application/json"
                }
            }
            
            print(f"📡 Sending request to Vertex AI...")
            response = call_vertex_ai_with_retry(vertex_request, f"product_code_test_{test_case['code']}", process_response=False)
            
            if not response:
                print(f"❌ No response from Vertex AI")
                continue
                
            print(f"\n📋 RESPONSE ANALYSIS:")
            print(f"Raw response keys: {list(response.keys())}")
            
            # Check for function calls in response
            function_calls_found = []
            if 'candidates' in response and response['candidates']:
                candidate = response['candidates'][0]
                content = candidate.get('content', {})
                parts = content.get('parts', [])
                
                for part in parts:
                    if 'functionCall' in part:
                        function_calls_found.append(part['functionCall'])
                
                # Also check if there's any text content (the JSON response)
                text_content = ""
                for part in parts:
                    if 'text' in part:
                        text_content += part['text']
                
                # Results
                if function_calls_found:
                    print(f"🎉 SUCCESS! Function calls detected: {len(function_calls_found)}")
                    for i, call in enumerate(function_calls_found):
                        print(f"  📞 Function {i+1}: {call.get('name', 'Unknown')}")
                        print(f"     Args: {json.dumps(call.get('args', {}), indent=6)}")
                else:
                    print(f"❌ FAILURE! NO FUNCTION CALLS DETECTED")
                
                if text_content:
                    print(f"📝 Text Response:")
                    try:
                        json_response = json.loads(text_content)
                        print(json.dumps(json_response, indent=2))
                        
                        # Check if they guessed field names
                        if 'filters' in json_response and json_response['filters']:
                            print(f"⚠️  Generated filters without function calls: {json_response['filters']}")
                        
                    except json.JSONDecodeError:
                        print(f"Raw text: {text_content}")
                        
        except Exception as e:
            print(f"❌ Error in test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Set environment
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    
    # Run test
    asyncio.run(test_product_code_function_calling())
