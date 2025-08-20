"""
Vertex AI API client

Provides secure access to Vertex AI APIs with retry logic and proper error handling.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.auth import default
from google.auth.transport.requests import Request
from pydantic import ValidationError

from core.config import PROJECT, REGION, VERTEX_MODEL
from core.exceptions import TokenLimitExceededException
from core.models import VertexResponse
from vertex.response_parser import extract_vertex_response_text
from llm_utils import parse_llm_response, VertexAIResponse


def call_vertex_ai_api_with_service_account(request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call Vertex AI API using service account credentials"""
    try:
        if not PROJECT or not REGION:
            logging.error("Project or location not configured for Vertex AI API")
            return None
        
        # Get service account credentials
        credentials, _ = default()
        auth_req = Request()
        credentials.refresh(auth_req)
        access_token = credentials.token
        
        # Construct Vertex AI API URL
        vertex_api_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT}/locations/{REGION}/publishers/google/models/{VERTEX_MODEL}:generateContent"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Log the request for debugging
        logging.info(f"Calling Vertex AI API with service account: {vertex_api_url}")
        logging.info(f"Using model: {VERTEX_MODEL}")
        
        response = requests.post(vertex_api_url, headers=headers, json=request_body)
        
        if not response.ok:
            error_text = response.text
            logging.error(f"Vertex AI API call failed: {response.status_code} - {error_text}")
            
            # Check for token limit errors that might be retryable
            if response.status_code == 400 and any(token_error in error_text.lower() for token_error in 
                ['token limit', 'tokens exceed', 'input too long', 'context length', 'max_tokens']):
                logging.warning(f"⚠️ Token limit error detected: {error_text}")
                return {'error': 'token_limit', 'details': error_text}
            
            return None
        
        response_data = response.json()
        
        # Log token usage information
        _log_token_usage(response_data, VERTEX_MODEL)
        
        logging.info("Vertex AI API call successful")
        return response_data
        
    except Exception as e:
        logging.error(f"Error calling Vertex AI API: {e}")
        return None


def call_vertex_ai_with_retry(request_body: Dict[str, Any], context: str = "", process_response: bool = False) -> Optional[Dict[str, Any]]:
    """
    Call Vertex AI API with retry logic for token limit errors.
    
    Args:
        request_body: The Vertex AI API request
        context: Context string for logging
        process_response: Whether to process response through extract_vertex_response_text()
    
    Returns:
        If process_response=True: {'processed_response': text, 'raw_response': dict}
        If process_response=False: raw response dict
    """
    max_retries = 2
    vertex_model = request_body.get('model', VERTEX_MODEL)
    
    for attempt in range(max_retries + 1):
        try:
            logging.info(f"🔄 Vertex AI API attempt {attempt + 1}/{max_retries + 1} for {context}")
            
            response = call_vertex_ai_api_with_service_account(request_body)
            
            # Check if this was a token limit error from API
            if isinstance(response, dict) and response.get('error') == 'token_limit':
                if attempt < max_retries:
                    logging.warning(f"⚠️ Token limit exceeded, attempting retry {attempt + 1}")
                    _increase_output_tokens(request_body, vertex_model, attempt)
                    continue
                else:
                    logging.error(f"❌ All retry attempts exhausted for token limit error")
                    return None
                    
            elif response is None:
                if attempt < max_retries:
                    logging.warning(f"⚠️ API call failed, retrying {attempt + 1}/{max_retries}")
                    continue
                else:
                    logging.error(f"❌ All retry attempts exhausted for API failure")
                    return None
            else:
                # Got a response - now process it if requested
                if process_response:
                    try:
                        processed_response = extract_vertex_response_text(response)
                        if attempt > 0:
                            logging.info(f"✅ Retry successful after {attempt} attempts")
                        return {'processed_response': processed_response, 'raw_response': response}
                    except TokenLimitExceededException as tle:
                        if attempt < max_retries:
                            logging.warning(f"⚠️ Response truncated due to MAX_TOKENS, attempting retry {attempt + 1}")
                            logging.info(f"📊 Current token usage: {tle.usage_metadata}")
                            _increase_output_tokens(request_body, vertex_model, attempt)
                            continue
                        else:
                            logging.error(f"❌ All retry attempts exhausted - response still truncated")
                            return None
                else:
                    # Return raw response without processing
                    if attempt > 0:
                        logging.info(f"✅ Retry successful after {attempt} attempts")
                    return response
                
        except Exception as e:
            logging.error(f"❌ Error in retry attempt {attempt + 1}: {e}")
            if attempt >= max_retries:
                return None
            continue
    
    return None


def _increase_output_tokens(request_body: Dict[str, Any], vertex_model: str, attempt: int) -> None:
    """Increase output token limits for retry attempts"""
    from core.config import get_max_tokens_for_model
    
    current_max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
    
    if attempt == 0:
        # First retry: Double the tokens (up to 8192)
        new_max_tokens = min(current_max_tokens * 2, 8192)
        request_body.setdefault('generationConfig', {})['maxOutputTokens'] = new_max_tokens
        logging.info(f"📈 Retry {attempt + 1}: Increased maxOutputTokens from {current_max_tokens} to {new_max_tokens}")
    elif attempt == 1:
        # Second retry: Max out at model's maximum output capacity
        model_limits = get_max_tokens_for_model(vertex_model)
        max_model_output = model_limits.get("output", 8192)
        if current_max_tokens < max_model_output:
            request_body['generationConfig']['maxOutputTokens'] = max_model_output
            logging.info(f"📈 Retry {attempt + 1}: Maxed out maxOutputTokens to model limit: {max_model_output}")
        else:
            logging.error(f"❌ Already at maximum output tokens ({current_max_tokens}), cannot increase further")


def _log_token_usage(response_data: Dict[str, Any], vertex_model: str) -> None:
    """Log token usage with model-specific warnings"""
    from core.config import get_max_tokens_for_model, update_token_warning_thresholds
    
    usage_metadata = response_data.get('usageMetadata', {})
    if not usage_metadata:
        return
        
    prompt_tokens = usage_metadata.get('promptTokenCount', 0)
    total_tokens = usage_metadata.get('totalTokenCount', 0)
    cached_tokens = usage_metadata.get('cachedContentTokenCount', 0)
    
    logging.info(f"📊 Token Usage - Prompt: {prompt_tokens:,}, Total: {total_tokens:,}, Cached: {cached_tokens:,}")
    
    # Get model-specific warning thresholds
    thresholds = update_token_warning_thresholds(vertex_model)
    
    # Model-aware warnings
    if prompt_tokens > thresholds.get("critical_threshold", 30000):
        logging.error(f"🚨 CRITICAL: Prompt token usage ({prompt_tokens:,}) approaching model limit for {vertex_model}")
    elif prompt_tokens > thresholds.get("warning_threshold", 25000):
        logging.warning(f"⚠️ High prompt token usage: {prompt_tokens:,} tokens for model {vertex_model}")
    
    # Log model capacity utilization
    model_limits = get_max_tokens_for_model(vertex_model)
    prompt_utilization = (prompt_tokens / model_limits["input"]) * 100
    logging.info(f"📊 Model capacity utilization: {prompt_utilization:.1f}% of input limit")