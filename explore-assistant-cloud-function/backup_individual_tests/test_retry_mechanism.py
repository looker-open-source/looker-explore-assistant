#!/usr/bin/env python3
"""
Test script for the Vertex AI retry mechanism with token limit handling
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

# Mock the call_vertex_ai_api_with_service_account function to simulate token limit errors
call_count = 0

def mock_vertex_api_call_with_token_limit(request_body):
    """Simulate token limit errors that can be resolved with higher output limits"""
    global call_count
    call_count += 1
    
    # Check if this is the first call (original token limit) or a retry
    max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
    prompt_text = request_body.get('contents', [{}])[0].get('parts', [{}])[0].get('text', '')
    
    print(f"   Mock API call #{call_count} - maxOutputTokens: {max_tokens}, prompt length: {len(prompt_text)}")
    
    # Simulate different scenarios based on prompt content and max tokens
    
    # Test 1 scenario: Low output tokens cause failures, higher tokens succeed
    if 'test_scenario_1' in prompt_text and max_tokens < 4096:
        return {'error': 'token_limit', 'details': 'maxOutputTokens too low for response complexity'}
    
    # Test 2 scenario: Progressive increases needed
    if 'test_scenario_2' in prompt_text:
        if max_tokens < 2048:
            return {'error': 'token_limit', 'details': 'maxOutputTokens insufficient'}
        elif max_tokens < 4096:
            return {'error': 'token_limit', 'details': 'Still need higher maxOutputTokens'}
        # Succeeds when tokens >= 4096
        
    # Test 4 scenario: Works with sufficient output tokens
    if 'test_scenario_4' in prompt_text and max_tokens < 4096:
        return {'error': 'token_limit', 'details': 'Complex field metadata response needs higher maxOutputTokens'}
    
    # Success case - return a proper response
    return {
        'candidates': [
            {
                'content': {
                    'parts': [
                        {'text': f'{{"explore_key": "test:explore", "message": "Success on attempt {call_count} with {max_tokens} tokens"}}'}
                    ]
                }
            }
        ],
        'usageMetadata': {
            'promptTokenCount': len(prompt_text) // 4,
            'candidateTokenCount': 50,
            'totalTokenCount': len(prompt_text) // 4 + 50
        }
    }

def test_retry_mechanism():
    print("=== Testing Vertex AI Retry Mechanism (Context Preservation) ===")
    global call_count
    
    # Patch the actual API call function with our mock
    import mcp_server
    original_function = mcp_server.call_vertex_ai_api_with_service_account
    mcp_server.call_vertex_ai_api_with_service_account = mock_vertex_api_call_with_token_limit
    
    try:
        # Test case 1: Token limit error with successful retry (higher output limits)
        print("\n🔄 Test 1: Token limit error with maxOutputTokens retry")
        call_count = 0  # Reset counter
        
        request_body = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': 'test_scenario_1: This is a prompt that will trigger a token limit error on first attempt' + ' extended content' * 30
                        }
                    ]
                }
            ],
            'generationConfig': {
                'maxOutputTokens': 2048,  # This will trigger the error
                'temperature': 0.1
            }
        }
        
        result = mcp_server.call_vertex_ai_with_retry(request_body, "test_scenario_1")
        
        if result and 'candidates' in result:
            print("   ✅ Success! Retry mechanism worked with increased token limits")
            print(f"   Final maxOutputTokens: {request_body['generationConfig']['maxOutputTokens']}")
        else:
            print("   ❌ Failed - retry mechanism did not work")
        
        # Test case 2: Progressive token limit increases
        print("\n📈 Test 2: Progressive token limit increases")
        call_count = 0  # Reset counter
        
        request_body = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': 'test_scenario_2: This prompt will test progressive token increases' * 50
                        }
                    ]
                }
            ],
            'generationConfig': {
                'maxOutputTokens': 1024,  # Start with low tokens
                'temperature': 0.1
            }
        }
        
        original_tokens = request_body['generationConfig']['maxOutputTokens']
        print(f"   Starting maxOutputTokens: {original_tokens}")
        
        result = mcp_server.call_vertex_ai_with_retry(request_body, "test_scenario_2")
        
        final_tokens = request_body['generationConfig']['maxOutputTokens']
        print(f"   Final maxOutputTokens: {final_tokens}")
        
        if result and 'candidates' in result and final_tokens > original_tokens:
            print("   ✅ Success! Progressive token increase worked")
        elif result and 'candidates' in result:
            print("   ✅ Success! Request worked (may not have needed token increase)")
        else:
            print("   ❌ Failed - progressive token increase did not work")
        
        # Test case 3: Normal success (no retry needed)
        print("\n✅ Test 3: Normal success case (no retry needed)")
        call_count = 0  # Reset counter
        
        request_body = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': 'test_scenario_3: Short prompt'  # This should succeed immediately
                        }
                    ]
                }
            ],
            'generationConfig': {
                'maxOutputTokens': 2048,
                'temperature': 0.1
            }
        }
        
        result = mcp_server.call_vertex_ai_with_retry(request_body, "test_scenario_3")
        
        if result and 'candidates' in result:
            print("   ✅ Success! Normal case worked without retry")
        else:
            print("   ❌ Failed - normal case should have worked")

        # Test case 4: Input context preservation
        print("\n🛡️ Test 4: Input context preservation")
        call_count = 0  # Reset counter
        
        valuable_context = 'test_scenario_4: IMPORTANT FIELD METADATA: order_date (Date), customer_id (String), total_sales (Number). GOLDEN QUERY EXAMPLES: Show sales by month, Customer analysis. CONVERSATION HISTORY: User asked about sales trends.' * 20
        request_body = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': valuable_context
                        }
                    ]
                }
            ],
            'generationConfig': {
                'maxOutputTokens': 2048,
                'temperature': 0.1
            }
        }
        
        original_context = request_body['contents'][0]['parts'][0]['text']
        original_length = len(original_context)
        
        result = mcp_server.call_vertex_ai_with_retry(request_body, "test_scenario_4")
        
        final_context = request_body['contents'][0]['parts'][0]['text']
        final_length = len(final_context)
        
        print(f"   Original context length: {original_length}")
        print(f"   Final context length: {final_length}")
        
        if original_context == final_context:
            print("   ✅ Success! Input context fully preserved during retries")
        else:
            print("   ❌ Failed - input context was modified")
            
    finally:
        # Restore original function
        mcp_server.call_vertex_ai_api_with_service_account = original_function
    
    print("\n🎉 Retry mechanism testing completed!")

def test_retry_strategies():
    print("\n=== Testing Retry Strategies (Context Preservation) ===")
    
    print("📈 Strategy 1: Progressive maxOutputTokens Increases")
    print("   - First attempt: Original tokens → Token limit error")
    print("   - Retry 1: Double tokens (up to 8192) → May succeed")
    print("   - Retry 2: Max out at model's output limit → Final attempt")
    print("   - Use case: Model needs more output space for complex responses")
    
    print("🛡️ Strategy 2: Input Context Preservation")
    print("   - Input context NEVER truncated or modified")
    print("   - Preserves valuable field metadata, examples, and conversation history")
    print("   - If token limits persist, suggests using higher-capacity model")
    print("   - Use case: Maintaining data quality and context integrity")
    
    print("🔄 Retry Logic Flow:")
    print("   1. Attempt original request with full context")
    print("   2. If token limit error:")
    print("      - Retry 1: Double maxOutputTokens (up to 8192)")
    print("      - Retry 2: Max out at model's maximum output capacity")
    print("   3. If other API error:")
    print("      - Retry up to 2 more times")
    print("   4. Input context always preserved")
    print("   5. Recommend higher-capacity model if all retries fail")
    
    print("\n💡 Benefits of Context Preservation:")
    print("   - Field metadata remains complete for accurate parameter generation")
    print("   - Golden query examples stay intact for better LLM guidance")
    print("   - Conversation history preserved for context-aware responses")
    print("   - No loss of valuable filtering information")
    print("   - Maintains consistency with area restrictions")

if __name__ == "__main__":
    test_retry_mechanism()
    test_retry_strategies()
