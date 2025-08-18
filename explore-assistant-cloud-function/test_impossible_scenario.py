#!/usr/bin/env python3

"""
Ultimate test: Create a scenario where the LLM absolutely cannot know the answer
and must use function calling. Test with completely made-up product codes.
"""

import os
import asyncio
import json
import sys
sys.path.append('.')
from mcp_server import call_vertex_ai_with_retry

async def test_impossible_scenario():
    """Test with completely fictional scenario that forces function calling."""
    
    print("🧪 ULTIMATE FUNCTION CALLING TEST")
    print("Testing with impossible-to-know scenario")
    print("=" * 60)
    
    # Function declarations 
    function_declarations = [
        {
            "name": "lookup_field_values",
            "description": "REQUIRED function to find product codes in database. No query can be completed without calling this function first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_string": {"type": "string", "description": "Product code to find"},
                    "limit": {"type": "integer", "description": "Max results", "default": 5}
                },
                "required": ["search_string"]
            }
        }
    ]
    
    # Test with completely unknown scenario
    impossible_prompt = """I need to find sales data for the mystery product code "XYZABC123". 

❗ CRITICAL SYSTEM CONSTRAINT ❗
- You are connecting to a custom proprietary database
- Product codes in this database use non-standard naming conventions
- You have ZERO knowledge of the field names or structure
- The ONLY way to find data is using the lookup_field_values function
- If you attempt to create filters without calling the function, the query will fail with ERROR_INVALID_FIELD

MANDATORY WORKFLOW:
1. Call lookup_field_values("XYZABC123") to discover field location
2. Only then create filters using the exact field names returned by the function

Failure to follow this workflow will result in query failure."""

    system_prompt = """You are a database query assistant for a PROPRIETARY SYSTEM with unknown schema.

⚠️ CRITICAL SYSTEM LIMITATIONS ⚠️
- You have NO KNOWLEDGE of field names in this database  
- All field names are CUSTOM and PROPRIETARY
- You CANNOT guess field names like "products.id" or "product_code"
- The database will REJECT any query with incorrect field names

🔧 REQUIRED WORKFLOW 🔧
1. ALWAYS call lookup_field_values function for any product code mentioned
2. Use EXACT field names returned by the function
3. NO EXCEPTIONS - guessing field names causes system errors

Response format:
{
  "function_calls_made": ["list of functions you called"],
  "model": "proprietary_system",
  "explore": "sales_data", 
  "fields": ["count", "total_revenue"],
  "filters": {"exact_field_from_function": "exact_value"}
}"""

    try:
        vertex_request = {
            "model": "gemini-2.0-flash-exp",
            "contents": [{"role": "user", "parts": [{"text": impossible_prompt}]}],
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "tools": [{"function_declarations": function_declarations}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json"
            }
        }
        
        print("📡 Sending impossible scenario to Vertex AI...")
        response = call_vertex_ai_with_retry(vertex_request, "impossible_scenario_test", process_response=False)
        
        if not response:
            print("❌ No response")
            return
            
        print("\n📋 ANALYZING RESPONSE...")
        
        # Check for function calls
        function_calls_found = []
        text_content = ""
        
        if 'candidates' in response and response['candidates']:
            candidate = response['candidates'][0]
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            for part in parts:
                if 'functionCall' in part:
                    function_calls_found.append(part['functionCall'])
                if 'text' in part:
                    text_content += part['text']
        
        # Results
        if function_calls_found:
            print("🎉🎉🎉 BREAKTHROUGH! Function calls detected!")
            for i, call in enumerate(function_calls_found):
                print(f"  📞 Function {i+1}: {call.get('name', 'Unknown')}")
                print(f"     Args: {json.dumps(call.get('args', {}), indent=6)}")
        else:
            print("💀💀💀 STILL NO FUNCTION CALLS!")
            print("Even impossible scenarios don't trigger function calls")
        
        if text_content:
            print(f"\n📄 TEXT RESPONSE:")
            try:
                json_response = json.loads(text_content)
                print(json.dumps(json_response, indent=2))
                
                # Check what they did
                if 'filters' in json_response:
                    if json_response['filters']:
                        print(f"\n🔍 FILTER ANALYSIS:")
                        print(f"They created filters: {json_response['filters']}")
                        print(f"This proves they're still guessing field names!")
                    else:
                        print(f"\n🤔 They returned empty filters - maybe they realized they can't guess?")
                        
            except json.JSONDecodeError:
                print(f"Raw response: {text_content}")
        
        print(f"\n🏁 FINAL VERDICT:")
        if function_calls_found:
            print(f"✅ SUCCESS - LLM used function calling!")
        else:
            print(f"❌ CONFIRMED - Modern LLMs will NOT use function calling even in impossible scenarios")
            print(f"📋 SOLUTION REQUIRED: Architectural changes needed, not better prompting")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    asyncio.run(test_impossible_scenario())
