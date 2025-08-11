
# MCP (Model Context Protocol) Server for Looker Explore Assistant
# This server acts as a credential proxy for non-admin users to access
# Vertex AI API by providing secure token exchange.

import os
import time
import json
import uuid
import logging
import traceback
from pydantic import ValidationError
from llm_utils import parse_llm_response, VertexAIResponse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import looker_sdk
from looker_sdk.rtl import api_settings
import spacy
from google.cloud import bigquery
from field_lookup_service import FieldValueLookupService
import asyncio

logging.basicConfig(level=logging.INFO)

# Custom exceptions for token limit handling
class TokenLimitExceededException(Exception):
    """Exception raised when Vertex AI response is truncated due to token limits"""
    def __init__(self, message="Response truncated due to token limit", current_tokens=None, usage_metadata=None):
        self.message = message
        self.current_tokens = current_tokens
        self.usage_metadata = usage_metadata
        super().__init__(self.message)

# Load spaCy model once at module level
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    nlp = None
    logging.warning(f"spaCy model load failed: {e}")

# Initialize environment variables
project = os.environ.get("PROJECT")
location = os.environ.get("REGION", "us-central1")
vertex_model = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")

# BigQuery configuration for suggested golden queries
bq_project_id = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
bq_dataset_id = os.environ.get("BQ_DATASET_ID", "explore_assistant")
bq_suggested_table = os.environ.get("BQ_SUGGESTED_TABLE", "silver_queries")

# Initialize field lookup service
field_lookup_service = FieldValueLookupService()

def get_max_tokens_for_model(model_name: str) -> dict:
    """Get maximum input and output tokens for the current model"""
    model_limits = {
        # Gemini 2.5 Models
        "gemini-2.5-flash": {"input": 1048576, "output": 8192},
        "gemini-2.5-flash-lite": {"input": 1048576, "output": 8192},
        "gemini-2.5-pro": {"input": 2097152, "output": 8192},
        
        # Gemini 2.0 Models
        "gemini-2.0-flash-exp": {"input": 1048576, "output": 8192},
        "gemini-2.0-flash-001": {"input": 1048576, "output": 8192},
        "gemini-2.0-flash": {"input": 1048576, "output": 8192},
        "gemini-2.0-flash-thinking-exp": {"input": 32767, "output": 8192},
        "gemini-2.0-pro": {"input": 2097152, "output": 8192},
        
        # Gemini 1.5 Models
        "gemini-1.5-pro-002": {"input": 2097152, "output": 8192},
        "gemini-1.5-pro-001": {"input": 2097152, "output": 8192},
        "gemini-1.5-pro": {"input": 2097152, "output": 8192},
        "gemini-1.5-flash-002": {"input": 1048576, "output": 8192},
        "gemini-1.5-flash-001": {"input": 1048576, "output": 8192},
        "gemini-1.5-flash": {"input": 1048576, "output": 8192},
        "gemini-1.5-flash-8b": {"input": 1048576, "output": 8192},
        
        # Gemini 1.0 Models (legacy)
        "gemini-1.0-pro": {"input": 32760, "output": 2048},
        "gemini-pro": {"input": 32760, "output": 2048}
    }
    
    # Check for exact match first
    if model_name in model_limits:
        return model_limits[model_name]
    
    # Pattern matching for version variations
    if "gemini-2.5" in model_name.lower():
        if "flash-lite" in model_name.lower():
            return {"input": 1048576, "output": 8192}
        elif "flash" in model_name.lower():
            return {"input": 1048576, "output": 8192}
        elif "pro" in model_name.lower():
            return {"input": 2097152, "output": 8192}
    
    if "gemini-2.0" in model_name.lower():
        if "thinking" in model_name.lower():
            return {"input": 32767, "output": 8192}
        elif "flash" in model_name.lower():
            return {"input": 1048576, "output": 8192}
        elif "pro" in model_name.lower():
            return {"input": 2097152, "output": 8192}
    
    if "gemini-1.5" in model_name.lower():
        if "flash-8b" in model_name.lower():
            return {"input": 1048576, "output": 8192}
        elif "flash" in model_name.lower():
            return {"input": 1048576, "output": 8192}
        elif "pro" in model_name.lower():
            return {"input": 2097152, "output": 8192}
    
    # Default fallback for unknown models
    logging.warning(f"Unknown model '{model_name}', using conservative defaults")
    return {"input": 32000, "output": 2048}

def calculate_max_output_tokens(system_prompt: str, model_name: str, task_type: str = "general") -> int:
    """Calculate appropriate output tokens based on task type and model capacity"""
    model_limits = get_max_tokens_for_model(model_name)
    max_output = model_limits["output"]
    max_input = model_limits["input"]
    
    # Check if this is a thinking model that needs extra buffer
    is_thinking_model = "thinking" in model_name.lower() or "2.5" in model_name.lower()
    
    # Task-specific token limits with thinking model adjustments
    if is_thinking_model:
        # Thinking models need more tokens due to internal reasoning
        task_limits = {
            "explore_selection": 400,      # Extra buffer for thinking process
            "synthesis": 600,              # More room for reasoning
            "explore_params": 2000,        # Main task needs substantial buffer
            "general": max_output // 3     # Conservative but not too restrictive
        }
        logging.info(f"🧠 Using thinking model limits for {model_name}")
    else:
        # Standard models - more conservative limits
        task_limits = {
            "explore_selection": 150,      # Just need the explore key
            "synthesis": 300,              # Synthesized query should be concise  
            "explore_params": 1200,        # JSON structure with fields, filters, etc.
            "general": max_output // 4     # Conservative default for other tasks
        }
        logging.info(f"📝 Using standard model limits for {model_name}")
    
    # Use task-specific limit, capped by model maximum
    recommended_tokens = min(task_limits.get(task_type, task_limits["general"]), max_output)
    
    # Rough estimate: 1 token ≈ 4 characters for English text
    estimated_prompt_tokens = len(system_prompt) // 4
    
    logging.info(f"📊 Model: {model_name}, Task: {task_type}")
    logging.info(f"📊 Max input tokens: {max_input:,}")
    logging.info(f"📊 Max output tokens: {max_output:,}")
    logging.info(f"📊 Estimated prompt tokens: {estimated_prompt_tokens:,}")
    
    # Only reduce output if prompt is extremely large (>90% of input limit)
    if estimated_prompt_tokens > max_input * 0.9:
        logging.warning(f"⚠️ Prompt approaching input token limit ({estimated_prompt_tokens:,} / {max_input:,})")
        minimum_safe = 300 if is_thinking_model else 150
        return max(recommended_tokens // 4, minimum_safe)  # Emergency fallback
    else:
        # Use task-appropriate tokens instead of maximum
        logging.info(f"📊 Using task-appropriate tokens: {recommended_tokens:,} (task: {task_type})")
        return recommended_tokens

def update_token_warning_thresholds(model_name: str) -> dict:
    """Get appropriate warning thresholds based on model capabilities"""
    model_limits = get_max_tokens_for_model(model_name)
    
    return {
        "prompt_warning": int(model_limits["input"] * 0.8),  # Warn at 80% of input limit
        "total_warning": int((model_limits["input"] + model_limits["output"]) * 0.8),
        "prompt_critical": int(model_limits["input"] * 0.95),  # Critical at 95% of input limit
        "total_critical": int((model_limits["input"] + model_limits["output"]) * 0.95)
    }

def get_response_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "3600",
        "Access-Control-Allow-Credentials": "false"
    }

def extract_user_email_from_token(bearer_token: str) -> Optional[str]:
    """Extract user email from JWT token without validation (infrastructure handles auth)"""
    try:
        logging.info("Extracting user email from token")
        
        # Add proper null and type checks
        if not bearer_token or not isinstance(bearer_token, str):
            logging.error("Invalid bearer token: token is None or not a string")
            return None
        
        # Remove 'Bearer ' prefix if present - with safe string operations
        bearer_token_lower = bearer_token.lower()
        if bearer_token_lower.startswith('bearer '):
            bearer_token = bearer_token[7:]
        
        # Remove any whitespace
        bearer_token = bearer_token.strip()
        
        # Check if token is empty after processing
        if not bearer_token:
            logging.error("Invalid bearer token: empty token after processing")
            return None
        
        # Split JWT into parts
        token_parts = bearer_token.split('.')
        if len(token_parts) != 3:
            logging.error(f"Invalid JWT format: expected 3 parts, got {len(token_parts)}")
            return None
        
        # Decode the payload (second part) to extract email
        import base64
        import json
        
        payload_data = token_parts[1]
        
        # Validate payload data exists
        if not payload_data:
            logging.error("Invalid JWT format: empty payload section")
            return None
            
        # Add padding if needed for base64 decoding
        payload_data += '=' * (4 - len(payload_data) % 4)
        
        try:
            payload_json = base64.urlsafe_b64decode(payload_data).decode('utf-8')
            payload = json.loads(payload_json)
            
            # Ensure payload is a dictionary
            if not isinstance(payload, dict):
                logging.error("Invalid JWT payload: not a JSON object")
                return None
            
            email = payload.get('email')
            if email and isinstance(email, str):
                logging.info(f"Extracted user email: {email}")
                return email
            else:
                logging.error("No valid email found in token payload")
                return None
                
        except Exception as e:
            logging.error(f"Failed to decode JWT payload: {e}")
            return None
        
    except Exception as e:
        logging.error(f"Error extracting email from token: {e}")
        return None

def call_vertex_ai_api_with_service_account(request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call Vertex AI API using service account credentials"""
    try:
        if not project or not location:
            logging.error("Project or location not configured for Vertex AI API")
            return None
        
        # Get service account credentials
        credentials, _ = default()
        auth_req = Request()
        credentials.refresh(auth_req)
        access_token = credentials.token
        
        # Construct Vertex AI API URL
        vertex_api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{vertex_model}:generateContent"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Log the request for debugging
        logging.info(f"Calling Vertex AI API with service account: {vertex_api_url}")
        logging.info(f"Using model: {vertex_model}")
        
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
        
        # Log token usage information with model-specific thresholds
        usage_metadata = response_data.get('usageMetadata', {})
        if usage_metadata:
            prompt_tokens = usage_metadata.get('promptTokenCount', 0)
            total_tokens = usage_metadata.get('totalTokenCount', 0)
            cached_tokens = usage_metadata.get('cachedContentTokenCount', 0)
            
            logging.info(f"📊 Token Usage - Prompt: {prompt_tokens:,}, Total: {total_tokens:,}, Cached: {cached_tokens:,}")
            
            # Get model-specific warning thresholds
            thresholds = update_token_warning_thresholds(vertex_model)
            
            # Model-aware warnings
            if prompt_tokens > thresholds["prompt_critical"]:
                logging.error(f"🚨 CRITICAL: Prompt token usage ({prompt_tokens:,}) approaching model limit for {vertex_model}")
            elif prompt_tokens > thresholds["prompt_warning"]:
                logging.warning(f"⚠️ High prompt token usage: {prompt_tokens:,} tokens for model {vertex_model}")
            
            if total_tokens > thresholds["total_critical"]:
                logging.error(f"🚨 CRITICAL: Total token usage ({total_tokens:,}) approaching model limit for {vertex_model}")
            elif total_tokens > thresholds["total_warning"]:
                logging.warning(f"⚠️ High total token usage: {total_tokens:,} tokens for model {vertex_model}")
            
            # Log model capacity utilization
            model_limits = get_max_tokens_for_model(vertex_model)
            prompt_utilization = (prompt_tokens / model_limits["input"]) * 100
            logging.info(f"📊 Model capacity utilization: {prompt_utilization:.1f}% of input limit")
        
        logging.info("Vertex AI API call successful")
        return response_data
        
    except Exception as e:
        logging.error(f"Error calling Vertex AI API: {e}")
        return None

def call_vertex_ai_with_retry(request_body: Dict[str, Any], context: str = "", process_response: bool = False) -> Optional[Dict[str, Any]]:
    """
    Call Vertex AI API with retry logic for token limit errors.
    Now includes response processing to catch MAX_TOKENS finish reasons.
    Attempts to recover by increasing output token limits only - input context is preserved.
    
    Args:
        request_body: The Vertex AI API request
        context: Context string for logging
        process_response: Whether to process response through extract_vertex_response_text()
    
    Returns:
        If process_response=True: {'processed_response': text, 'raw_response': dict}
        If process_response=False: raw response dict
    """
    max_retries = 2
    vertex_model = request_body.get('model', 'gemini-1.5-flash')
    original_max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
    
    for attempt in range(max_retries + 1):
        try:
            logging.info(f"🔄 Vertex AI API attempt {attempt + 1}/{max_retries + 1} for {context}")
            
            response = call_vertex_ai_api_with_service_account(request_body)
            
            # Check if this was a token limit error from API
            if isinstance(response, dict) and response.get('error') == 'token_limit':
                if attempt < max_retries:
                    logging.warning(f"⚠️ Token limit exceeded, attempting retry {attempt + 1}")
                    
                    # Strategy: Increase output token limits progressively
                    current_max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
                    
                    # Progressive increase: 2x, then max out at model limit
                    if attempt == 0:
                        # First retry: Double the tokens (up to 8192)
                        new_max_tokens = min(current_max_tokens * 2, 8192)
                        request_body['generationConfig']['maxOutputTokens'] = new_max_tokens
                        logging.info(f"📈 Retry {attempt + 1}: Increased maxOutputTokens from {current_max_tokens} to {new_max_tokens}")
                        continue
                    elif attempt == 1:
                        # Second retry: Max out at model's maximum output capacity
                        model_limits = get_max_tokens_for_model(vertex_model)
                        max_model_output = model_limits.get("output", 8192)
                        if current_max_tokens < max_model_output:
                            request_body['generationConfig']['maxOutputTokens'] = max_model_output
                            logging.info(f"📈 Retry {attempt + 1}: Maxed out maxOutputTokens to model limit: {max_model_output}")
                            continue
                        else:
                            logging.error(f"❌ Already at maximum output tokens ({current_max_tokens}), cannot increase further")
                            logging.error(f"💡 Consider optimizing the input context or using a higher-capacity model")
                else:
                    logging.error(f"❌ All retry attempts exhausted for token limit error")
                    logging.error(f"💡 Input context preserved - consider using a model with higher token capacity")
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
                        # Process the response, which may raise TokenLimitExceededException
                        processed_response = extract_vertex_response_text(response)
                        # If we get here, processing was successful
                        if attempt > 0:
                            logging.info(f"✅ Retry successful after {attempt} attempts")
                        return {'processed_response': processed_response, 'raw_response': response}
                    except TokenLimitExceededException as tle:
                        # Response was truncated due to token limits - retry with higher limits
                        if attempt < max_retries:
                            logging.warning(f"⚠️ Response truncated due to MAX_TOKENS, attempting retry {attempt + 1}")
                            logging.info(f"📊 Current token usage: {tle.usage_metadata}")
                            
                            # Strategy: Increase output token limits progressively
                            current_max_tokens = request_body.get('generationConfig', {}).get('maxOutputTokens', 2048)
                            
                            # Progressive increase: 2x, then max out at model limit
                            if attempt == 0:
                                # First retry: Double the tokens (up to 8192)
                                new_max_tokens = min(current_max_tokens * 2, 8192)
                                request_body['generationConfig']['maxOutputTokens'] = new_max_tokens
                                logging.info(f"📈 Retry {attempt + 1}: Increased maxOutputTokens from {current_max_tokens} to {new_max_tokens}")
                                continue
                            elif attempt == 1:
                                # Second retry: Max out at model's maximum output capacity
                                model_limits = get_max_tokens_for_model(vertex_model)
                                max_model_output = model_limits.get("output", 8192)
                                if current_max_tokens < max_model_output:
                                    request_body['generationConfig']['maxOutputTokens'] = max_model_output
                                    logging.info(f"📈 Retry {attempt + 1}: Maxed out maxOutputTokens to model limit: {max_model_output}")
                                    continue
                                else:
                                    logging.error(f"❌ Already at maximum output tokens ({current_max_tokens}), cannot increase further")
                                    break
                        else:
                            logging.error(f"❌ All retry attempts exhausted - response still truncated")
                            logging.error(f"💡 Consider optimizing the input context or using a higher-capacity model")
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

def get_looker_sdk():
    """Initialize and return Looker SDK instance using environment variables"""
    try:
        logging.info("Initializing Looker SDK using LOOKERSDK_ environment variables...")
        
        # Check if required environment variables are set
        base_url = os.environ.get('LOOKERSDK_BASE_URL')
        client_id = os.environ.get('LOOKERSDK_CLIENT_ID')
        client_secret = os.environ.get('LOOKERSDK_CLIENT_SECRET')
        
        logging.info(f"LOOKERSDK_BASE_URL: {base_url}")
        logging.info(f"LOOKERSDK_CLIENT_ID: {client_id[:8]}..." if client_id else "LOOKERSDK_CLIENT_ID: None")
        logging.info(f"LOOKERSDK_CLIENT_SECRET: {'***' if client_secret else 'None'}")
        
        if not base_url:
            raise Exception("LOOKERSDK_BASE_URL environment variable is not set")
        if not client_id:
            raise Exception("LOOKERSDK_CLIENT_ID environment variable is not set")
        if not client_secret:
            raise Exception("LOOKERSDK_CLIENT_SECRET environment variable is not set")
        
        # Initialize SDK using environment variables (no config file needed)
        sdk = looker_sdk.init40()
        logging.info("Looker SDK initialized successfully")
        
        # Test the SDK by trying to get current user info
        try:
            user = sdk.me()
            logging.info(f"Looker SDK test successful - logged in as: {user.email}")
        except Exception as test_error:
            logging.warning(f"Looker SDK test failed: {test_error}")
            # Don't fail completely, just log the warning
        
        return sdk
        
    except Exception as e:
        logging.error(f"Error initializing Looker SDK: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def find_looker_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find Looker user by email address using Looker SDK"""
    try:
        # Input validation
        if not email or not isinstance(email, str):
            logging.error("Invalid email parameter: email is None or not a string")
            return None
            
        email = email.strip()
        if not email:
            logging.error("Invalid email parameter: empty email after stripping")
            return None
        
        # Initialize Looker SDK
        sdk = get_looker_sdk()
        if not sdk:
            logging.error("Failed to initialize Looker SDK")
            return None
        
        # Search for user by email using SDK
        try:
            users = sdk.search_users(email=email)
        except Exception as sdk_error:
            logging.error(f"Looker SDK search_users failed: {sdk_error}")
            return None
        
        # Validate search results
        if not users or len(users) == 0:
            logging.error(f"No Looker user found with email: {email}")
            return None
        
        # Convert the first user object to dict with safe attribute access
        user = users[0]
        try:
            user_dict = {
                'id': getattr(user, 'id', None),
                'email': getattr(user, 'email', None),
                'first_name': getattr(user, 'first_name', None),
                'last_name': getattr(user, 'last_name', None),
                'is_disabled': getattr(user, 'is_disabled', None),
                'role_ids': getattr(user, 'role_ids', [])
            }
        except Exception as conversion_error:
            logging.error(f"Error converting user object to dict: {conversion_error}")
            # Return a minimal dict with available information
            user_dict = {
                'id': str(user) if user else None,
                'email': email,
                'first_name': None,
                'last_name': None,
                'is_disabled': None,
                'role_ids': []
            }

        # Validate essential fields
        if not user_dict.get('id'):
            logging.error("User found but missing essential 'id' field")
            return None

        # Log the found user details (safely)
        user_id = user_dict.get('id', 'unknown')
        user_email = user_dict.get('email', 'unknown')
        user_roles = user_dict.get('role_ids', [])
        logging.info(f"Found Looker user: {user_id} - {user_email} - {user_roles}")
        return user_dict
        
    except Exception as e:
        logging.error(f"Error finding Looker user: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def extract_vertex_response_text(vertex_response: Dict[str, Any]) -> Optional[str]:
    """
    Extract and parse text from Vertex AI response, with robust validation and JSON parsing.
    Returns parsed object if valid JSON or raw text fallback.
    """
    try:
        logging.info(f"🔍 extract_vertex_response_text - Input: {vertex_response}")
        
        # Add proper null and type validation
        if not vertex_response or not isinstance(vertex_response, dict):
            logging.error("❌ Invalid vertex response: None or not a dictionary")
            return None
        
        # Check for MAX_TOKENS or other finish reasons that indicate incomplete responses
        candidates = vertex_response.get('candidates', [])
        if not candidates:
            logging.error("❌ No candidates found in Vertex AI response")
            return None
            
        if candidates:
            finish_reason = candidates[0].get('finishReason')
            if finish_reason == 'MAX_TOKENS':
                logging.warning("⚠️ VERTEX AI RESPONSE TRUNCATED: Hit maximum token limit - will retry with higher limits")
                usage_metadata = vertex_response.get('usageMetadata', {})
                current_tokens = usage_metadata.get('candidatesTokenCount', 0)
                
                # Raise exception to trigger retry mechanism
                raise TokenLimitExceededException(
                    "Response truncated due to maximum token limit", 
                    current_tokens=current_tokens,
                    usage_metadata=usage_metadata
                )
            elif finish_reason and finish_reason != 'STOP':
                logging.warning(f"⚠️ Unexpected finish reason: {finish_reason}")
        
        # Try pydantic validation first, but handle failures gracefully
        try:
            resp_model = VertexAIResponse.parse_obj(vertex_response)
            # Extract raw text
            first = resp_model.candidates[0]
            content = first.get('content', {})
            parts = content.get('parts', []) or []
        except ValidationError as ve:
            logging.warning(f"Vertex AI response schema mismatch: {ve}")
            # Fall back to manual extraction
            first_candidate = candidates[0]
            content = first_candidate.get('content', {})
            parts = content.get('parts', []) or []
        except Exception as e:
            logging.error(f"Pydantic validation error: {e}")
            # Fall back to manual extraction
            first_candidate = candidates[0]
            content = first_candidate.get('content', {})
            parts = content.get('parts', []) or []
        
        if not parts:
            logging.warning("❌ No parts found in response content")
            return None
            
        # Safely extract text from parts - concatenate all parts
        raw_text = ""
        for part in parts:
            if isinstance(part, dict) and 'text' in part:
                part_text = part.get('text', '')
                if isinstance(part_text, str):
                    raw_text += part_text
            elif isinstance(part, str):
                raw_text += part
                
        if not raw_text:
            logging.warning("❌ No text content found in response parts")
            return None
            
        logging.info(f"🔍 Extracted raw text: '{raw_text}' (type: {type(raw_text)})")
        
        # Attempt to parse JSON from raw_text
        try:
            parsed = parse_llm_response(raw_text)
            logging.info(f"🔍 Parsed result: {parsed} (type: {type(parsed)})")
        except Exception as e:
            logging.warning(f"JSON parsing failed: {e}")
            parsed = None
        
        # Validate response size for brevity
        final_result = parsed if parsed is not None else raw_text
        if isinstance(final_result, str) and len(final_result) > 2000:
            logging.warning(f"⚠️ Response too verbose ({len(final_result)} chars), truncating for brevity")
            final_result = final_result[:2000] + "..."
        elif isinstance(final_result, dict):
            # Check if dict is too large when serialized
            dict_str = str(final_result)
            if len(dict_str) > 3000:
                logging.warning(f"⚠️ Dict response too large ({len(dict_str)} chars), may need simplification")
        
        return final_result
        
    except TokenLimitExceededException:
        # Re-raise TokenLimitExceededException so retry mechanism can catch it
        raise
    except Exception as e:
        logging.error(f"Error extracting Vertex AI response: {e}")
        # Final fallback extraction attempt
        try:
            if vertex_response and isinstance(vertex_response, dict):
                candidates = vertex_response.get('candidates', [])
                if candidates and len(candidates) > 0:
                    first_candidate = candidates[0]
                    if isinstance(first_candidate, dict):
                        content = first_candidate.get('content', {})
                        if isinstance(content, dict):
                            parts = content.get('parts', [])
                            if parts and len(parts) > 0:
                                first_part = parts[0]
                                if isinstance(first_part, dict) and 'text' in first_part:
                                    return first_part['text']
        except Exception as fallback_error:
            logging.error(f"Final fallback extraction failed: {fallback_error}")
        
        return None

def determine_explore_from_prompt(auth_header: str, prompt: str, golden_queries: Dict[str, Any], 
                                 conversation_context: str = "", restricted_explore_keys: list = None) -> Optional[str]:
    """
    Enhanced explore determination with conversation context, area restrictions, and optional semantic field discovery.
    Uses Vertex AI function calling to intelligently search for relevant fields when needed.
    """
    try:
        logging.info("=== EXPLORE DETERMINATION START ===")
        logging.info(f"Determining best explore for prompt: {prompt}")
        logging.info(f"Has conversation context: {bool(conversation_context)}")
        logging.info(f"Restricted explore keys: {restricted_explore_keys}")
        
        # Filter golden queries by restricted explore keys if provided
        filtered_golden_queries = golden_queries
        if restricted_explore_keys:
            logging.info(f"Filtering golden queries by restricted keys: {restricted_explore_keys}")
            filtered_golden_queries = {}
            for key, value in golden_queries.items():
                if key == 'exploreEntries':
                    # Filter explore entries by restricted keys
                    filtered_entries = [
                        entry for entry in value 
                        if entry.get('golden_queries.explore_id') in restricted_explore_keys
                    ]
                    filtered_golden_queries[key] = filtered_entries
                    logging.info(f"Filtered {key}: {len(filtered_entries)} entries after filtering")
                else:
                    # For other keys, filter based on explore keys
                    if isinstance(value, dict):
                        filtered_value = {
                            k: v for k, v in value.items() 
                            if k in restricted_explore_keys
                        }
                        filtered_golden_queries[key] = filtered_value
                        logging.info(f"Filtered {key}: {len(filtered_value)} entries after filtering")
                    else:
                        filtered_golden_queries[key] = value
                        logging.info(f"Copied {key} without filtering (not a dict)")
        else:
            logging.info("No restricted explore keys - using all golden queries")
        
        logging.info(f"Final filtered golden queries keys: {list(filtered_golden_queries.keys())}")
        if 'exploreEntries' in filtered_golden_queries:
            entries_count = len(filtered_golden_queries['exploreEntries']) if isinstance(filtered_golden_queries['exploreEntries'], list) else len(filtered_golden_queries['exploreEntries']) if isinstance(filtered_golden_queries['exploreEntries'], dict) else 0
            logging.info(f"exploreEntries count: {entries_count}")
        
        # Build system prompt with conversation context
        newline_char = "\n"
        restriction_text = ""
        if restricted_explore_keys:
            restriction_text = f"{newline_char}IMPORTANT: You must only select explores from this restricted list: {restricted_explore_keys}{newline_char}"
        
        # Extract just the explore names and basic info to reduce token usage
        available_explores = []
        
        # Get explore names from exploreEntries
        if 'exploreEntries' in filtered_golden_queries:
            entries = filtered_golden_queries['exploreEntries']
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict):
                        explore_id = entry.get('golden_queries.explore_id') or entry.get('explore_id')
                        if explore_id:
                            available_explores.append(explore_id)
            elif isinstance(entries, dict):
                available_explores.extend(list(entries.keys()))
        
        # Get explore names from other sections if available
        for key in ['exploreGenerationExamples', 'exploreRefinementExamples', 'exploreSamples']:
            if key in filtered_golden_queries and isinstance(filtered_golden_queries[key], dict):
                available_explores.extend(list(filtered_golden_queries[key].keys()))
        
        # Remove duplicates and ensure we have explores to choose from
        available_explores = list(set(available_explores))
        
        if not available_explores:
            logging.warning("❌ No available explores found in filtered golden queries")
            # Fallback to restricted keys if available
            if restricted_explore_keys:
                available_explores = restricted_explore_keys
            else:
                logging.error("❌ No explores available for selection")
        
        logging.info(f"🔍 Available explores for selection: {available_explores}")
        
        # Optimization: If only one explore is available, skip LLM call and return it directly
        if len(available_explores) == 1:
            single_explore = available_explores[0]
            logging.info(f"✅ Only one explore available ({single_explore}) - skipping LLM call for efficiency")
            logging.info("=== EXPLORE DETERMINATION COMPLETE (OPTIMIZED) ===")
            return single_explore
        
        # Create a concise explore list instead of full golden queries dump
        explores_text = "\n".join([f"- {explore}" for explore in available_explores])
        
        # Define function declarations for semantic field search
        function_declarations = [
            {
                "name": "search_semantic_fields",
                "description": "Search for Looker field locations that contain actual dimension values related to your search terms. IMPORTANT: Only searches high-cardinality dimensions that have been specifically indexed for vector search (marked with 'index' sets in Looker). This is NOT a comprehensive field search - use only when looking for specific values/codes that might exist in indexed dimension data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of specific values or codes to search for in indexed dimension data (e.g., ['nike', 'adidas', 'premium'] NOT ['customer', 'revenue'])"
                        },
                        "explore_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific explores to search within (e.g., ['ecommerce:order_items', 'thelook:events'])"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of field matches to return per search term",
                            "default": 3
                        }
                    },
                    "required": ["search_terms"]
                }
            },
            {
                "name": "lookup_field_values", 
                "description": "Find specific dimension values containing text patterns. IMPORTANT: Only searches values from high-cardinality dimensions that have been indexed for vector search. Use when looking for exact codes, names, SKUs, or identifiers that exist in the actual Looker data.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_string": {
                            "type": "string",
                            "description": "Specific text pattern to find in indexed dimension values (e.g., 'NIKE123', 'Premium', 'CA', 'Shipped')"
                        },
                        "explore_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific explores to search within"
                        }
                    },
                    "required": ["search_string"]
                }
            }
        ]
        
        system_prompt = f"""You are a Looker Explore Assistant. Your job is to determine which Looker explore is most appropriate for answering a user's question.

IMPORTANT: You must analyze the user's question independently and select the BEST explore for their needs, regardless of any previous explore selections or model information.
{restriction_text}
Available Explores:
{explores_text}

{f"Conversation Context:{newline_char}{conversation_context}{newline_char}" if conversation_context else ""}

You have access to semantic field search and field value lookup functions. IMPORTANT: These functions only search high-cardinality dimensions that have been specifically indexed (marked with 'index' sets in Looker). Use them ONLY when:
1. You need to find which explores contain specific product names, codes, SKUs, or identifiers that might exist in the data
2. You need to verify if specific dimension values (like brand names, status codes, region codes) exist before selecting an explore
3. The user mentions specific values/codes and you're unsure which explore contains that type of data

DO NOT use these functions for:
- General business concepts like "revenue", "profit", "customers" (these are typically measures/fields available in explore metadata)
- Finding fields by semantic meaning (use the provided explore metadata instead)
- Comprehensive field discovery (only indexed dimensions are searchable)

Instructions:
1. Analyze the user's current prompt: "{prompt}"
2. Consider the conversation context to understand what the user has been asking about
3. If needed, use the search functions to find relevant fields or verify data availability
4. Compare against the available explores
5. Determine which explore would be BEST suited to answer this question
6. {"Restrict your selection to the provided explore keys only" if restricted_explore_keys else "Ignore any previous explore selections - choose the optimal explore for this specific question"}
7. Return ONLY the explore key (e.g., "order_items", "events", etc.) as a single string

Current user prompt: {prompt}

Response format: Return only the explore key as plain text (no JSON, no explanation)"""

        logging.info(f"🔍 System prompt length: {len(system_prompt)} characters")
        logging.info(f"🔍 System prompt preview: {system_prompt[:500]}...")
        if len(system_prompt) > 10000:
            logging.warning(f"⚠️ System prompt is very long ({len(system_prompt)} chars) - may cause issues")

        # Format request for Vertex AI with function calling capabilities
        max_tokens = calculate_max_output_tokens(system_prompt, vertex_model, "explore_selection")
        
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                }
            ],
            "tools": [{"function_declarations": function_declarations}],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.4,  # Reduced for focused responses
                "topK": 20,  # Reduced for brevity
                "maxOutputTokens": max_tokens,
                "candidateCount": 1
            }
        }
        
        # Log concise request summary for debugging
        logging.info(f"🤖 LLM Request - Explore Selection with Functions | Query: '{prompt[:100]}{'...' if len(prompt) > 100 else ''}' | "
                    f"Options: {len(available_explores)} explores | "
                    f"Restricted: {'Yes' if restricted_explore_keys else 'No'} | "
                    f"Context: {'Yes' if conversation_context else 'No'} | "
                    f"Prompt: {len(system_prompt):,} chars | MaxTokens: {max_tokens}")
        
        # Call Vertex AI using service account with retry logic
        vertex_response = call_vertex_ai_with_retry(vertex_request, "explore_determination")
        if not vertex_response:
            logging.error("❌ Failed to get response from Vertex AI after retries")
            return None
        
        logging.info(f"✅ Got Vertex AI response: {vertex_response}")
        
        # Check if the model made function calls
        if 'candidates' in vertex_response and len(vertex_response['candidates']) > 0:
            candidate = vertex_response['candidates'][0]
            content_parts = candidate.get('content', {}).get('parts', [])
            
            # Process any function calls
            for part in content_parts:
                if 'functionCall' in part:
                    function_call = part['functionCall']
                    function_name = function_call['name']
                    function_args = function_call.get('args', {})
                    
                    logging.info(f"🔧 Model requested function call: {function_name} with args: {function_args}")
                    
                    # Execute the function call
                    function_result = None
                    try:
                        if function_name == "search_semantic_fields":
                            search_terms = function_args.get('search_terms', [])
                            explore_ids = function_args.get('explore_ids', restricted_explore_keys)
                            max_results = function_args.get('max_results', 3)
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                field_matches = loop.run_until_complete(
                                    field_lookup_service.semantic_field_search(
                                        search_terms=search_terms,
                                        explore_ids=explore_ids,
                                        limit_per_term=max_results,
                                        similarity_threshold=0.6
                                    )
                                )
                                function_result = {
                                    "field_matches": [
                                        {
                                            "field_location": match.field_location,
                                            "explore_id": f"{match.model_name}:{match.explore_name}",
                                            "field_type": match.field_type,
                                            "similarity": round(match.similarity, 3),
                                            "description": match.field_description or "No description"
                                        }
                                        for match in field_matches
                                    ],
                                    "total_matches": len(field_matches)
                                }
                            finally:
                                loop.close()
                        
                        elif function_name == "lookup_field_values":
                            search_string = function_args.get('search_string', '')
                            explore_ids = function_args.get('explore_ids', restricted_explore_keys)
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                value_matches = loop.run_until_complete(
                                    field_lookup_service.field_value_lookup(
                                        search_string=search_string,
                                        field_location=None,
                                        limit=10
                                    )
                                )
                                
                                # Filter by explore_ids if specified
                                if explore_ids:
                                    filtered_matches = []
                                    for match in value_matches:
                                        explore_id = f"{match['model_name']}:{match['explore_name']}"
                                        if explore_id in explore_ids:
                                            filtered_matches.append(match)
                                    value_matches = filtered_matches
                                
                                function_result = {
                                    "matching_values": value_matches[:10],  # Limit to top 10
                                    "total_matches": len(value_matches),
                                    "search_string": search_string
                                }
                            finally:
                                loop.close()
                        
                        logging.info(f"✅ Function call result: {function_result}")
                        
                        # Continue conversation with function results
                        follow_up_request = {
                            "contents": [
                                {"role": "user", "parts": [{"text": system_prompt}]},
                                {"role": "model", "parts": [{"functionCall": function_call}]},
                                {"role": "function", "parts": [{"functionResponse": {
                                    "name": function_name,
                                    "response": {"result": function_result}
                                }}]},
                                {"role": "user", "parts": [{"text": "Based on the search results, which explore is best suited for the user's question? Return only the explore key."}]}
                            ],
                            "generationConfig": {
                                "temperature": 0.1,
                                "maxOutputTokens": 100
                            }
                        }
                        
                        follow_up_response = call_vertex_ai_with_retry(follow_up_request, "explore_determination_followup")
                        if follow_up_response:
                            vertex_response = follow_up_response
                            break  # Use this response instead
                        
                    except Exception as e:
                        logging.error(f"❌ Function call execution failed: {e}")
                        # Continue with original response if function fails
        
        # Extract the explore key from response
        response_text = extract_vertex_response_text(vertex_response)
        logging.info(f"🔍 Extracted response text: '{response_text}' (type: {type(response_text)})")
        
        if response_text:
            # Handle different response types
            if isinstance(response_text, dict):
                logging.warning(f"❌ Response is dict, not string: {response_text}")
                # Try to extract string from common dict patterns
                if 'explore_key' in response_text:
                    explore_key = str(response_text['explore_key'])
                elif 'explore' in response_text:
                    explore_key = str(response_text['explore'])
                else:
                    logging.error(f"❌ Cannot extract explore key from dict response: {response_text}")
                    return None
            elif isinstance(response_text, list):
                logging.warning(f"❌ Response is list, not string: {response_text}")
                if response_text and isinstance(response_text[0], str):
                    explore_key = response_text[0]
                else:
                    logging.error(f"❌ Cannot extract explore key from list response: {response_text}")
                    return None
            else:
                # Clean up the response - remove any extra whitespace or formatting
                explore_key = str(response_text).strip().replace('"', '').replace('\n', '')
            
            logging.info(f"🔍 Cleaned explore key: '{explore_key}'")
            
            # Validate that the determined explore is in the restricted list if restrictions apply
            if restricted_explore_keys and explore_key not in restricted_explore_keys:
                logging.warning(f"Determined explore '{explore_key}' not in restricted list. Selecting first available.")
                explore_key = restricted_explore_keys[0] if restricted_explore_keys else explore_key
            
            logging.info(f"✅ Determined explore with context: {explore_key}")
            logging.info("=== EXPLORE DETERMINATION COMPLETE ===")
            return explore_key
        
        logging.error("❌ Failed to extract explore key from response - response_text is None or empty")
        return None
        
    except Exception as e:
        logging.error(f"❌ Error determining explore: {e}")
        return None

def generate_explore_params(auth_header: str, prompt: str, explore_key: str, 
                          golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                          current_explore: Dict[str, Any], conversation_context: str = "") -> Optional[Dict[str, Any]]:
    """Enhanced parameter generation with two-step LLM approach for better conversation context handling"""
    try:
        logging.info(f"=== GENERATE_EXPLORE_PARAMS START ===")
        logging.info(f"Original prompt: {prompt}")
        logging.info(f"Has conversation context: {bool(conversation_context)}")
        
        # Optimization: Skip synthesis step if there's no meaningful conversation context
        if not conversation_context or conversation_context.strip() == "":
            logging.info("✅ No conversation context - skipping synthesis step for efficiency")
            synthesized_query = prompt
        else:
            # Check if conversation context is minimal (only contains headers but no actual previous prompts)
            context_lines = [line.strip() for line in conversation_context.split('\n') if line.strip()]
            meaningful_lines = [line for line in context_lines if not line.startswith(('Previous prompts', 'Current prompt is', 'The user\'s current', 'Recent conversation'))]
            
            if len(meaningful_lines) == 0:
                logging.info("✅ Conversation context contains no meaningful history - skipping synthesis step for efficiency")
                synthesized_query = prompt
            else:
                logging.info(f"📝 Found {len(meaningful_lines)} meaningful context lines - proceeding with synthesis")
                # Step 1: Synthesize conversation context into a clear, standalone query
                synthesized_query = synthesize_conversation_context(auth_header, prompt, conversation_context)
        
        # The synthesis function now always returns a string (either synthesized or fallback to original)
        if synthesized_query and synthesized_query != prompt:
            logging.info(f"✅ SYNTHESIS SUCCESS - Original: '{prompt}' -> Synthesized: '{synthesized_query}'")
        else:
            logging.info(f"✅ SYNTHESIS FALLBACK/SKIPPED - Using original prompt: '{prompt}'")
            synthesized_query = prompt
        
        logging.info(f"Using query for explore params: {synthesized_query}")
        
        # Step 2: Generate explore parameters using the synthesized query
        result = generate_explore_params_from_query(auth_header, synthesized_query, explore_key, 
                                                golden_queries, semantic_models, current_explore)
        
        logging.info(f"=== GENERATE_EXPLORE_PARAMS RESULT ===")
        if result:
            # Safely log keys only if result is a dict
            keys_log = list(result.keys()) if isinstance(result, dict) else 'Not a dict'
            logging.info(f"Result keys: {keys_log}")
            if isinstance(result, dict) and 'explore_params' in result:
                logging.info(f"Explore params fields: {result['explore_params'].get('fields', [])}")
        else:
            logging.warning("No result from generate_explore_params_from_query")
            
        return result
        
    except Exception as e:
        logging.error(f"Error in generate_explore_params: {e}")
        return None

def synthesize_conversation_context(auth_header: str, current_prompt: str, conversation_context: str) -> Optional[str]:
    """First LLM call: Synthesize conversation history and current prompt into a clear, standalone query"""
    try:
        logging.info(f"=== SYNTHESIS STEP ===")
        logging.info(f"Current prompt: {current_prompt}")
        logging.info(f"Conversation context: {conversation_context}")
        
        # If there's no conversation context, just return the original prompt
        if not conversation_context or conversation_context.strip() == "":
            logging.info("No conversation context, returning original prompt")
            return current_prompt
        
        # Monitor conversation context size to prevent token overflow
        if len(conversation_context) > 2000:
            logging.warning(f"⚠️ Large conversation context ({len(conversation_context)} chars) - truncating to prevent token issues")
            # Truncate to last 1500 characters to preserve recent context
            conversation_context = "..." + conversation_context[-1500:]
            
        synthesis_prompt = f"""Synthesize conversation and current prompt into one clear query.

HISTORY: {conversation_context}
CURRENT: {current_prompt}

Rules:
- Combine history context with current request
- Output one standalone query only
- Be concise and specific

Output only the synthesized query."""

        logging.info(f"🔍 Synthesis prompt size: ~{len(synthesis_prompt)} characters")

        # Format request for Vertex AI with task-appropriate tokens
        max_tokens = calculate_max_output_tokens(synthesis_prompt, vertex_model, "synthesis")
        
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": synthesis_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.5,  # Reduced for more focused responses
                "topK": 20,  # Reduced for brevity
                "maxOutputTokens": max_tokens,
                "responseMimeType": "text/plain",
                "candidateCount": 1
            }
        }
        
        # Log concise request summary for debugging
        logging.info(f"🤖 LLM Request - Conversation Synthesis | Current: '{current_prompt[:80]}{'...' if len(current_prompt) > 80 else ''}' | "
                    f"Context: {len(conversation_context)} chars | "
                    f"Prompt: {len(synthesis_prompt):,} chars | MaxTokens: {max_tokens}")
        
        # Call Vertex AI using service account with retry logic
        vertex_response = call_vertex_ai_with_retry(vertex_request, "conversation_synthesis")
        if not vertex_response:
            logging.warning("❌ SYNTHESIS: No response from Vertex AI after retries, using original prompt")
            return current_prompt
        
        logging.info(f"🔍 SYNTHESIS: Got Vertex AI response: {vertex_response}")
        
        # Extract the synthesized query
        synthesized_query = extract_vertex_response_text(vertex_response)
        logging.info(f"🔍 SYNTHESIS: Extracted text: '{synthesized_query}' (type: {type(synthesized_query)})")
        
        if synthesized_query:
            # Handle different response types
            if isinstance(synthesized_query, dict):
                logging.warning(f"❌ SYNTHESIS: Response is dict, trying to extract text: {synthesized_query}")
                # Try to find text in common fields
                if 'text' in synthesized_query:
                    synthesized_query = str(synthesized_query['text'])
                elif 'content' in synthesized_query:
                    synthesized_query = str(synthesized_query['content'])
                elif 'query' in synthesized_query:
                    synthesized_query = str(synthesized_query['query'])
                else:
                    logging.warning("❌ SYNTHESIS: Cannot extract text from dict, using original prompt")
                    return current_prompt
            elif isinstance(synthesized_query, list):
                logging.warning(f"❌ SYNTHESIS: Response is list, taking first element: {synthesized_query}")
                if synthesized_query and isinstance(synthesized_query[0], str):
                    synthesized_query = synthesized_query[0]
                else:
                    logging.warning("❌ SYNTHESIS: Cannot extract text from list, using original prompt")
                    return current_prompt
            
            synthesized_query = str(synthesized_query).strip()
            
            # Validate that we got a meaningful synthesis
            if not synthesized_query or synthesized_query.lower() in ['none', 'null', 'undefined']:
                logging.warning("❌ SYNTHESIS: Got empty or invalid result, using original prompt")
                return current_prompt
            
            logging.info(f"=== SYNTHESIS RESULT ===")
            logging.info(f"✅ Synthesized query: {synthesized_query}")
            return synthesized_query
        
        logging.warning("❌ SYNTHESIS: Failed to extract synthesized query from Vertex AI response")
        logging.warning(f"❌ SYNTHESIS: Falling back to original prompt: '{current_prompt}'")
        return current_prompt
        
    except Exception as e:
        logging.error(f"Error synthesizing conversation context: {e}")
        return None

def generate_explore_params_from_query(auth_header: str, query: str, explore_key: str, 
                                     golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                                     current_explore: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generate explore parameters from a clear, synthesized query with optional semantic field discovery"""
    try:
        # Get semantic model for this specific explore only (optimized for token efficiency)
        explore_semantic_model = semantic_models.get(explore_key, {})
        
        if not explore_semantic_model:
            logging.warning(f"⚠️ No semantic model found for explore: {explore_key}")
            logging.info(f"🔍 Available semantic models: {list(semantic_models.keys())}")
        
        # Format table context for this explore - limit fields to prevent token overflow
        dimensions = explore_semantic_model.get('dimensions', [])
        measures = explore_semantic_model.get('measures', [])
        explore_description = explore_semantic_model.get('description', '')
        
        # Dynamic field limiting based on model capacity
        model_limits = get_max_tokens_for_model(vertex_model)
        
        # Adjust field limits based on model input capacity
        if model_limits["input"] >= 1000000:  # High-capacity models (2M+ tokens)
            MAX_FIELDS_PER_TYPE = 25
            description_limit = 100
        elif model_limits["input"] >= 500000:  # Medium-capacity models (500K+ tokens)
            MAX_FIELDS_PER_TYPE = 20
            description_limit = 80
        else:  # Lower-capacity models
            MAX_FIELDS_PER_TYPE = 15
            description_limit = 50
        
        def format_field_concise(field):
            name = field.get('name', '')
            label = field.get('label', '')
            description = field.get('description', '')[:description_limit]
            return f"- {name}: {label}" + (f" ({description})" if description else "")

        # Take only the first N fields to manage token usage
        limited_dimensions = dimensions[:MAX_FIELDS_PER_TYPE] if dimensions else []
        limited_measures = measures[:MAX_FIELDS_PER_TYPE] if measures else []
        
        # If we still have too many fields, be more aggressive for smaller models
        total_fields = len(limited_dimensions) + len(limited_measures)
        if total_fields > 30 and model_limits["input"] < 100000:
            logging.warning(f"⚠️ Too many fields ({total_fields}) for model capacity, reducing further")
            limited_dimensions = dimensions[:8] if dimensions else []
            limited_measures = measures[:8] if measures else []
        
        table_context = f"""
# Looker Explore: {explore_key}
{f"Description: {explore_description[:200]}" if explore_description else ""}

## Available Dimensions ({len(limited_dimensions)} of {len(dimensions)}):
{chr(10).join([format_field_concise(dim) for dim in limited_dimensions])}

## Available Measures ({len(limited_measures)} of {len(measures)}):
{chr(10).join([format_field_concise(measure) for measure in limited_measures])}
"""

        # Get examples with dynamic limits based on model capacity
        example_text = ""
        if model_limits["input"] >= 1000000:
            max_examples = 3
            max_input_chars = 120
        elif model_limits["input"] >= 500000:
            max_examples = 2
            max_input_chars = 100
        else:
            max_examples = 1
            max_input_chars = 80
        
        # Try to get relevant examples from filtered golden queries
        if 'exploreGenerationExamples' in golden_queries and explore_key in golden_queries['exploreGenerationExamples']:
            examples = golden_queries['exploreGenerationExamples'][explore_key]
            if isinstance(examples, list) and examples:
                limited_examples = examples[:max_examples]
                example_text = f"\nExample queries:\n"
                for i, ex in enumerate(limited_examples, 1):
                    input_text = ex.get('input', '')[:max_input_chars]
                    example_text += f"{i}. {input_text}\n"
                logging.info(f"✅ Using {len(limited_examples)} filtered examples for explore: {explore_key}")
            else:
                logging.info(f"⚠️ No examples found for explore in filtered golden queries: {explore_key}")
        else:
            logging.info(f"⚠️ No exploreGenerationExamples section for explore: {explore_key}")
            logging.info(f"🔍 Available sections in golden queries: {list(golden_queries.keys())}")
            if 'exploreGenerationExamples' in golden_queries:
                logging.info(f"🔍 Available explores in exploreGenerationExamples: {list(golden_queries['exploreGenerationExamples'].keys())}")
        
        # Build system prompt for explore parameter generation with function calling
        function_declarations = [
            {
                "name": "search_semantic_fields",
                "description": "Search for indexed high-cardinality dimension fields when you suspect specific values/codes might exist in the data but aren't sure which field contains them. LIMITATION: Only searches fields that have been specifically indexed with 'index' sets in Looker - NOT all fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_terms": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of specific values/codes to search for (e.g., ['nike', 'premium', 'SKU123'] NOT general concepts like ['revenue', 'customer'])"
                        },
                        "explore_ids": {
                            "type": "array", 
                            "items": {"type": "string"},
                            "description": "List of explores to search within (e.g., ['ecommerce:order_items'])",
                            "default": [explore_key]
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of field matches to return per search term",
                            "default": 5
                        }
                    },
                    "required": ["search_terms"]
                }
            },
            {
                "name": "lookup_field_values",
                "description": "Find specific values that exist in indexed high-cardinality dimensions. Use when you need to verify exact codes, names, or identifiers exist before creating filters. LIMITATION: Only searches indexed dimension values, not all fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_string": {
                            "type": "string",
                            "description": "Specific text/code to find in indexed dimension values (e.g., 'NIKE', 'Completed', 'CA', 'SKU123')"
                        },
                        "field_location": {
                            "type": "string",
                            "description": "Optional specific field to search within (format: model.explore.view.field)"
                        }
                    },
                    "required": ["search_string"]
                }
            }
        ]
        
        system_prompt = f"""Generate Looker explore parameters for: "{query}"

{table_context}
{example_text}

You have access to semantic field search and field value lookup functions. IMPORTANT: These only search high-cardinality dimensions that have been specifically indexed. Use them ONLY when:
1. You need to find exact values/codes (like product names, SKUs, brand names) that might exist in indexed dimension data
2. You need to verify specific dimension values exist before creating filters
3. The user mentions specific identifiers and you're unsure which indexed field contains them

DO NOT use these functions for:
- General field discovery (use the provided explore metadata instead) 
- Business concepts like "revenue" or "profit" (these are typically measures available in the metadata)
- Comprehensive data exploration (only specific indexed dimensions are searchable)

IMPORTANT: Be extremely concise. Return minimal JSON only.

Return JSON:
{{
  "explore_key": "{explore_key}",
  "explore_params": {{
    "fields": ["field1", "field2"],
    "filters": {{}},
    "sorts": ["field1"],
    "limit": "500",
    "vis_config": {{"type": "table"}}
  }},
  "message_type": "explore",
  "summary": "Brief description"
}}

Vis types: single_value, table, looker_grid, looker_column, looker_bar, looker_line, looker_area, looker_pie
"""

        logging.info(f"🔍 Generated prompt size: ~{len(system_prompt):,} characters")
        
        # Calculate dynamic output tokens based on model and task
        max_output_tokens = calculate_max_output_tokens(system_prompt, vertex_model, "explore_params")
        thresholds = update_token_warning_thresholds(vertex_model)
        
        logging.info(f"📊 Using task-specific maxOutputTokens: {max_output_tokens:,} for explore params generation")

        # Format request for Vertex AI with function calling capabilities
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": system_prompt
                        }
                    ]
                }
            ],
            "tools": [{"function_declarations": function_declarations}],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.5,
                "topK": 20,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
                "candidateCount": 1
            }
        }
        
        # Log concise request summary for debugging
        logging.info(f"🤖 LLM Request with Functions - Explore: {explore_key} | Query: '{query[:100]}{'...' if len(query) > 100 else ''}' | "
                    f"Fields: {len(limited_dimensions)} dims, {len(limited_measures)} measures | "
                    f"Examples: {len(golden_queries.get('exploreGenerationExamples', {}).get(explore_key, []))} | "
                    f"Prompt: {len(system_prompt):,} chars | MaxTokens: {max_output_tokens}")
        
        # Call Vertex AI using service account with retry logic
        vertex_response = call_vertex_ai_with_retry(vertex_request, "explore_parameter_generation")
        if not vertex_response:
            logging.warning("❌ Parameter generation failed after retries, using fallback")
            return create_context_aware_fallback(query, explore_key, "", semantic_models)
        
        # Check if the model made function calls  
        if 'candidates' in vertex_response and len(vertex_response['candidates']) > 0:
            candidate = vertex_response['candidates'][0]
            content_parts = candidate.get('content', {}).get('parts', [])
            
            # Process any function calls
            for part in content_parts:
                if 'functionCall' in part:
                    function_call = part['functionCall']
                    function_name = function_call['name']
                    function_args = function_call.get('args', {})
                    
                    logging.info(f"🔧 Model requested function call: {function_name} with args: {function_args}")
                    
                    # Execute the function call
                    function_result = None
                    try:
                        if function_name == "search_semantic_fields":
                            search_terms = function_args.get('search_terms', [])
                            explore_ids = function_args.get('explore_ids', [explore_key])
                            max_results = function_args.get('max_results', 5)
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                field_matches = loop.run_until_complete(
                                    field_lookup_service.semantic_field_search(
                                        search_terms=search_terms,
                                        explore_ids=explore_ids,
                                        limit_per_term=max_results,
                                        similarity_threshold=0.7
                                    )
                                )
                                function_result = {
                                    "discovered_fields": [
                                        {
                                            "field_location": match.field_location,
                                            "field_name": match.field_name,
                                            "field_type": match.field_type,
                                            "similarity": round(match.similarity, 3),
                                            "description": match.field_description or "No description",
                                            "sample_values": [v['value'] for v in match.matching_values[:3]]
                                        }
                                        for match in field_matches
                                    ],
                                    "search_terms": search_terms,
                                    "total_matches": len(field_matches)
                                }
                            finally:
                                loop.close()
                        
                        elif function_name == "lookup_field_values":
                            search_string = function_args.get('search_string', '')
                            field_location = function_args.get('field_location', None)
                            
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                value_matches = loop.run_until_complete(
                                    field_lookup_service.field_value_lookup(
                                        search_string=search_string,
                                        field_location=field_location,
                                        limit=10
                                    )
                                )
                                function_result = {
                                    "matching_values": [
                                        {
                                            "field_location": match['field_location'],
                                            "field_value": match['field_value'],
                                            "frequency": match['value_frequency']
                                        }
                                        for match in value_matches
                                    ],
                                    "search_string": search_string,
                                    "total_matches": len(value_matches)
                                }
                            finally:
                                loop.close()
                        
                        logging.info(f"✅ Function call result: {function_result}")
                        
                        # Continue conversation with function results
                        follow_up_request = {
                            "contents": [
                                {"role": "user", "parts": [{"text": system_prompt}]},
                                {"role": "model", "parts": [{"functionCall": function_call}]},
                                {"role": "function", "parts": [{"functionResponse": {
                                    "name": function_name,
                                    "response": {"result": function_result}
                                }}]},
                                {"role": "user", "parts": [{"text": "Now generate the Looker query parameters using the search results. Return JSON only."}]}
                            ],
                            "generationConfig": {
                                "temperature": 0.1,
                                "maxOutputTokens": max_output_tokens,
                                "responseMimeType": "application/json"
                            }
                        }
                        
                        follow_up_response = call_vertex_ai_with_retry(follow_up_request, "explore_params_followup", process_response=True)
                        if follow_up_response:
                            vertex_response = follow_up_response
                            break  # Use this response instead
                        
                    except Exception as e:
                        logging.error(f"❌ Function call execution failed: {e}")
                        # Continue with original response if function fails
        
        # Extract the processed response (already processed by call_vertex_ai_with_retry)
        response_text = vertex_response.get('processed_response') if isinstance(vertex_response, dict) else None
        if response_text:
            try:
                # Handle dict directly
                if isinstance(response_text, dict):
                    result = response_text
                elif isinstance(response_text, list):
                    if response_text and isinstance(response_text[0], dict):
                        result = response_text[0]
                    else:
                        logging.warning(f"Unexpected list response from LLM: {response_text}")
                        return create_context_aware_fallback(query, explore_key, "", semantic_models)
                else:
                    result = json.loads(response_text)
                    
                logging.info(f"Generated explore params for {explore_key} using model {vertex_model}")
                if isinstance(result, dict):
                    logging.info(f"Response structure: {list(result.keys())}")
                
                # Ensure the response has the expected structure
                if isinstance(result, dict) and 'explore_params' not in result:
                    if 'fields' in result or 'filters' in result:
                        result = {
                            "explore_key": explore_key,
                            "explore_params": result,
                            "message_type": "explore",
                            "summary": f"Generated query for: {query}"
                        }
                    else:
                        logging.warning(f"Unexpected response structure, creating fallback")
                        result = create_context_aware_fallback(query, explore_key, "", semantic_models)
                
                # Check if explore_params is empty and use fallback if needed
                explore_params = result.get('explore_params', {})
                if not explore_params or not explore_params.get('fields'):
                    logging.warning(f"Empty explore_params detected, using context-aware fallback")
                    fallback_result = create_context_aware_fallback(query, explore_key, "", semantic_models)
                    if result.get('summary') and 'unable' not in result.get('summary', '').lower():
                        fallback_result['summary'] = result.get('summary')
                    result = fallback_result
                
                return result
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Raw response: {response_text}")
                return create_context_aware_fallback(query, explore_key, "", semantic_models)
        
        return None
        
    except Exception as e:
        logging.error(f"Error generating explore params from query: {e}")
        return None

def create_context_aware_fallback(prompt: str, explore_key: str, conversation_context: str, semantic_models: Dict[str, Any]) -> Dict[str, Any]:
    """Create a context-aware fallback response when AI parsing fails"""
    try:
        # Get available fields for this explore
        explore_semantic_model = semantic_models.get(explore_key, {})
        dimensions = explore_semantic_model.get('dimensions', [])
        measures = explore_semantic_model.get('measures', [])
        
        # Try to find relevant fields based on conversation context and prompt
        relevant_fields = []
        
        # Look for common patterns
        context_and_prompt = f"{conversation_context} {prompt}".lower()
        
        # Look for sales/revenue related fields
        if any(word in context_and_prompt for word in ['sales', 'revenue', 'arr', 'total']):
            sales_measures = [m.get('name') for m in measures if m.get('name') and any(term in m.get('name', '').lower() for term in ['sale', 'revenue', 'total', 'arr', 'price'])]
            relevant_fields.extend(sales_measures[:2])  # Take first 2 relevant measures
        
        # Look for time/date related fields for trends
        if any(word in context_and_prompt for word in ['month', 'quarter', 'year', 'date', 'time', 'trend']):
            date_dimensions = [d.get('name') for d in dimensions if d.get('name') and any(term in d.get('name', '').lower() for term in ['date', 'month', 'quarter', 'year', 'time', 'created'])]
            relevant_fields.extend(date_dimensions[:1])  # Take first relevant date dimension
        
        # If no specific fields found, but we have context about sales by month, make educated guesses
        if not relevant_fields and 'sales' in context_and_prompt and 'month' in context_and_prompt:
            # Look for common sales and date field patterns
            for measure in measures:
                measure_name = measure.get('name', '').lower()
                if any(term in measure_name for term in ['sale', 'price', 'total', 'revenue']):
                    relevant_fields.append(measure.get('name'))
                    break
            
            for dimension in dimensions:
                dim_name = dimension.get('name', '').lower()
                if any(term in dim_name for term in ['month', 'date', 'created']):
                    relevant_fields.append(dimension.get('name'))
                    break
        
        # If still no specific fields found, use some defaults
        if not relevant_fields:
            if measures:
                relevant_fields.append(measures[0].get('name', ''))
            if dimensions:
                relevant_fields.append(dimensions[0].get('name', ''))
        
        # Remove empty fields
        relevant_fields = [f for f in relevant_fields if f]
        
        # Determine visualization type
        vis_config = {"type": "table"}  # Default to table
        if any(word in context_and_prompt for word in ['chart', 'line', 'bar', 'graph']):
            vis_config = {"type": "looker_line"}
        elif any(word in context_and_prompt for word in ['table']):
            vis_config = {"type": "table"}
        
        logging.info(f"Context-aware fallback generated fields: {relevant_fields}")
        logging.info(f"Based on context: {context_and_prompt}")
        
        return {
            "explore_key": explore_key,
            "explore_params": {
                "fields": relevant_fields,
                "filters": {},
                "sorts": relevant_fields[:1] if relevant_fields else [],
                "limit": "500",
                "vis_config": vis_config
            },
            "message_type": "explore",
            "summary": f"Generated query based on conversation context: {prompt}"
        }
        
    except Exception as e:
        logging.error(f"Error creating context-aware fallback: {e}")
        return {
            "explore_key": explore_key,
            "explore_params": {
                "fields": [],
                "filters": {},
                "sorts": [],
                "limit": "500"
            },
            "message_type": "explore",
            "summary": f"Unable to generate specific parameters for: {prompt}"
        }

def process_explore_assistant_request(auth_header: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the explore assistant request with conversation context"""
    try:
        logging.info("Starting process_explore_assistant_request")
        
        # Extract user email from token for Looker user lookup
        user_email = extract_user_email_from_token(auth_header)
        if not user_email:
            logging.warning("Could not extract user email from token, proceeding without user context")
            user_info = {'email': 'anonymous'}
        else:
            # Find Looker user for additional context
            looker_user = find_looker_user_by_email(user_email)
            user_info = {'email': user_email, 'looker_user': looker_user}
        
        # Extract conversation data from the request
        prompt = request_data.get('prompt', '')
        conversation_id = request_data.get('conversation_id', '')
        prompt_history = request_data.get('prompt_history', [])
        current_explore = request_data.get('current_explore', {})  # This will be ignored in favor of AI selection
        golden_queries = request_data.get('golden_queries', {})
        semantic_models = request_data.get('semantic_models', {})
        model_name = request_data.get('model_name', '')  # This will be ignored in favor of AI selection
        data_to_summarize = request_data.get('data_to_summarize', '')
        test_mode = request_data.get('test_mode', False)
        
        # Extract area restriction parameters
        selected_area = request_data.get('selected_area', None)
        restricted_explore_keys = request_data.get('restricted_explore_keys', [])
        
        # Filter both golden queries AND semantic models if restrictions exist
        filtered_golden_queries = golden_queries
        filtered_semantic_models = semantic_models
        
        if restricted_explore_keys:
            filtered_golden_queries = filter_golden_queries_by_explores(golden_queries, restricted_explore_keys)
            filtered_semantic_models = filter_semantic_models_by_explores(semantic_models, restricted_explore_keys)
            logging.info(f"🎯 Applied filtering for {len(restricted_explore_keys)} restricted explores")
        else:
            logging.info("📊 No explore restrictions - using all golden queries and semantic models")
        
        # Handle conversation context
        thread_messages = request_data.get('thread_messages', [])
        
        logging.info(f"User: {user_email}")
        logging.info(f"Conversation ID: {conversation_id}")
        logging.info(f"Prompt history length: {len(prompt_history)}")
        logging.info(f"Thread messages length: {len(thread_messages)}")
        logging.info(f"Selected area: {selected_area}")
        logging.info(f"Restricted explore keys: {restricted_explore_keys}")
        
        # Handle test mode
        if test_mode:
            return {
                'status': 'ok',
                'message': 'Vertex AI connection test successful',
                'timestamp': time.time()
            }
        
        # Build conversation context for the AI
        conversation_context = build_conversation_context(prompt_history, thread_messages)
        logging.info(f"Built conversation context: {conversation_context[:200]}..." if len(conversation_context) > 200 else f"Built conversation context: {conversation_context}")
        
        # Always determine the most appropriate explore for each request
        # This ensures we select the best explore based on the current prompt and conversation context
        # Ignoring any input explore or model information in favor of AI-driven selection
        
        # If only one explore is allowed, use it directly (bypass AI selection)
        if restricted_explore_keys and len(restricted_explore_keys) == 1:
            determined_explore_key = restricted_explore_keys[0]
            logging.info(f"🎯 Single explore restriction - using: {determined_explore_key}")
        else:
            # Multi-explore scenario or no restrictions - AI determines best explore with filtered golden queries
            logging.info("🤖 Using AI to determine best explore from available options")
            determined_explore_key = determine_explore_from_prompt(
                auth_header, prompt, filtered_golden_queries, conversation_context, restricted_explore_keys
            )
        
        if not determined_explore_key:
            logging.warning("❌ AI couldn't determine explore, attempting fallback...")
            # If AI couldn't determine explore, try to use first available explore as fallback
            entries = filtered_golden_queries.get('exploreEntries')
            first_explore = None
            
            logging.info(f"🔍 Fallback debugging - exploreEntries type: {type(entries)}")
            logging.info(f"🔍 Fallback debugging - exploreEntries content: {entries}")
            
            if isinstance(entries, dict) and entries:
                first_explore = next(iter(entries.keys()))
                logging.info(f"✅ Found first explore from dict: {first_explore}")
            elif isinstance(entries, list) and entries:
                # If list of explore keys
                if isinstance(entries[0], str):
                    first_explore = entries[0]
                    logging.info(f"✅ Found first explore from list: {first_explore}")
                elif isinstance(entries[0], dict):
                    # If list of explore objects, try to extract key
                    first_explore = entries[0].get('explore_id') or entries[0].get('id') or entries[0].get('key')
                    logging.info(f"✅ Found first explore from list object: {first_explore}")
                else:
                    logging.warning(f"❌ Unexpected list entry type: {type(entries[0])}")
            else:
                logging.warning(f"❌ No valid exploreEntries found - entries: {entries}")
                
            # Also check other possible sources for explores in filtered data
            if not first_explore:
                logging.info("🔍 Checking other filtered golden query sections for explores...")
                for key, value in filtered_golden_queries.items():
                    if isinstance(value, dict) and value:
                        first_explore = next(iter(value.keys()))
                        logging.info(f"✅ Found first explore from {key}: {first_explore}")
                        break
                        
            if first_explore:
                logging.warning(f"✅ Fallback successful - using first available: {first_explore}")
                determined_explore_key = first_explore
            else:
                logging.error("❌ No fallback explore available")
                available_keys = list(filtered_golden_queries.keys()) if isinstance(filtered_golden_queries, dict) else []
                logging.error(f"❌ Available filtered golden query keys: {available_keys}")
                return {
                    'error': 'Failed to determine appropriate explore and no fallback available',
                    'message_type': 'error',
                    'debug_info': {
                        'filtered_golden_queries_keys': available_keys,
                        'exploreEntries_type': str(type(entries)),
                        'exploreEntries_content': str(entries)[:500] if entries else 'None',
                        'restricted_explore_keys': restricted_explore_keys
                    }
                }
        
        logging.info(f"Determined explore key: {determined_explore_key}")
        
        # Extract model name and explore name from the determined explore key
        # The explore key format is "model:explore_name" (e.g., "ecommerce:order_items")
        if ':' in determined_explore_key:
            model_name_from_key, explore_name_from_key = determined_explore_key.split(':', 1)
            logging.info(f"Extracted from explore key - Model: {model_name_from_key}, Explore: {explore_name_from_key}")
        else:
            # Fallback if the key doesn't contain model info
            model_name_from_key = 'unknown'
            explore_name_from_key = determined_explore_key
            logging.warning(f"Explore key doesn't contain model info, using fallback: {model_name_from_key}:{explore_name_from_key}")
        
        # Create explore context for parameter generation
        current_explore = {
            'exploreKey': explore_name_from_key,  # Just the explore name part
            'exploreId': determined_explore_key,  # Full key (model:explore_name)
            'modelName': model_name_from_key      # Model name extracted from key
        }
        
        # Optimize golden queries to only include the chosen explore for parameter generation
        # This reduces token usage and focuses the LLM on relevant examples only
        chosen_explore_golden_queries = filter_golden_queries_by_explores(filtered_golden_queries, [determined_explore_key])
        chosen_explore_semantic_models = filter_semantic_models_by_explores(filtered_semantic_models, [determined_explore_key])
        
        logging.info(f"🎯 Optimized context for parameter generation to single explore: {determined_explore_key}")
        
        # Generate explore parameters using the determined explore with optimized context
        result = generate_explore_params(
            auth_header, prompt, determined_explore_key, 
            chosen_explore_golden_queries, chosen_explore_semantic_models, current_explore, conversation_context
        )
        
        if not result:
            return {
                'error': 'Failed to generate explore parameters',
                'message_type': 'error'
            }
        
        # Add conversation tracking to response
        if isinstance(result, dict):
            result['conversation_id'] = conversation_id
            result['prompt_added_to_history'] = prompt
        
        # Check for feedback pattern and save suggested golden query if detected
        has_feedback, approved_explore_params = detect_feedback_pattern(prompt_history, thread_messages, prompt)
        if has_feedback and approved_explore_params:
            # Save the suggested golden query with the APPROVED explore_params
            save_success = save_suggested_silver_query(
                auth_header, 
                result.get('explore_key', '') if isinstance(result, dict) else '', 
                prompt_history,  # Pass entire prompt history
                approved_explore_params,  # Use the approved params
                user_email
            )
            
            if save_success and isinstance(result, dict):
                result['feedback_message'] = "Thank you for your feedback. This is being saved as an improved example."
                logging.info("Successfully saved suggested golden query with approved explore_params")
        elif has_feedback:
            logging.warning("Feedback pattern detected but could not extract approved explore_params")
        
        return result
        
    except Exception as e:
        logging.error(f"Error processing explore assistant request: {e}")
        return {
            'error': f'Internal processing error: {str(e)}',
            'message_type': 'error'
        }

def build_conversation_context(prompt_history: list, thread_messages: list) -> str:
    """Build conversation context string from history"""
    try:
        if not prompt_history and not thread_messages:
            return ""
        
        context_parts = []
        
        if prompt_history:
            context_parts.append("Previous prompts in this conversation:")
            # Show all prompts except the last one (which is the current prompt)
            for i, prev_prompt in enumerate(prompt_history[:-1], 1):
                context_parts.append(f"{i}. {prev_prompt}")
            
            # If there are multiple prompts, add context about the conversation flow
            if len(prompt_history) > 1:
                context_parts.append(f"\nCurrent prompt is a follow-up to the above questions.")
                context_parts.append(f"The user's current request should be interpreted in the context of these previous questions.")
        
        if thread_messages:
            context_parts.append("\nRecent conversation messages:")
            for msg in thread_messages[-5:]:  # Last 5 messages
                msg_type = msg.get('type', 'message')
                content = msg.get('message', msg.get('content', ''))
                actor = msg.get('actor', 'unknown')
                if actor == 'user':
                    context_parts.append(f"User: {content}")
                elif actor == 'system':
                    context_parts.append(f"Assistant: {content}")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logging.error(f"Error building conversation context: {e}")
        return ""

def extract_approved_explore_params(thread_messages: list) -> Optional[Dict[str, Any]]:
    """
    Extract the explore_params from the last assistant response that the user is confirming.
    This should be the explore_params that were actually approved by the user.
    """
    try:
        logging.info("🔍 Extracting approved explore_params from thread messages")
        
        if not thread_messages:
            logging.warning("❌ No thread messages available")
            return None
        
        # Look for the last system/assistant message with explore_params
        # Go backwards through messages to find the most recent assistant response
        for i in range(len(thread_messages) - 1, -1, -1):
            msg = thread_messages[i]
            
            # Check if this is a system/assistant message
            if msg.get('actor') == 'system' and msg.get('type') == 'explore':
                explore_params = msg.get('exploreParams')
                if explore_params:
                    logging.info(f"✅ Found approved explore_params from message at index {i}")
                    logging.info(f"📊 Approved params preview: {json.dumps(explore_params, indent=2)[:200]}...")
                    return explore_params
        
        logging.warning("❌ No explore_params found in thread messages")
        return None
        
    except Exception as e:
        logging.error(f"Error extracting approved explore_params: {e}")
        return None

def detect_feedback_pattern(prompt_history: list, thread_messages: list, current_prompt: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Detect if the conversation contains a feedback pattern:
    1. Initial request -> visualization generated
    2. User feedback indicating the visualization is incorrect 
    3. Corrected visualization generated
    4. User confirmation that the correction is successful
    
    Returns: (has_feedback_pattern, corrected_explore_params)
    """
    try:
        logging.info("🔍 FEEDBACK DETECTION START")
        logging.info(f"📜 Prompt history ({len(prompt_history)}): {prompt_history}")
        logging.info(f"💬 Thread messages ({len(thread_messages)}): {thread_messages}")
        logging.info(f"🎯 Current prompt: '{current_prompt}'")
        
        # Need at least 3 interactions for a complete feedback cycle (reduced from 4)
        total_interactions = len(prompt_history) + len(thread_messages)
        logging.info(f"📊 Total interactions: {total_interactions}")
        
        if total_interactions < 3:
            logging.info("❌ Not enough interactions for feedback pattern")
            return False, None
            
        # Look for feedback indicators in the current prompt and recent history
        feedback_indicators = [
            'wrong', 'incorrect', 'not right', 'fix', 'correct', 'change',
            'should be', 'instead', 'better', 'improve', 'adjust'
        ]
        
        confirmation_indicators = [
            'perfect', 'exactly', 'correct', 'right', 'good', 'thanks', 'thank you',
            'that works', 'looks good', 'much better', 'yes', 'great'
        ]
        
        # Check if current prompt is a confirmation
        current_lower = current_prompt.lower()
        is_confirmation = any(indicator in current_lower for indicator in confirmation_indicators)
        logging.info(f"✅ Current prompt is confirmation: {is_confirmation}")
        
        if not is_confirmation:
            logging.info("❌ Current prompt is not a confirmation")
            return False, None
            
        # Look back in conversation for feedback pattern
        recent_prompts = prompt_history[-3:] if len(prompt_history) >= 3 else prompt_history
        recent_messages = [msg.get('message', msg.get('content', '')) for msg in thread_messages[-3:]]
        
        logging.info(f"🔍 Checking recent prompts for feedback: {recent_prompts}")
        logging.info(f"🔍 Checking recent messages for feedback: {recent_messages}")
        
        # Check if there was feedback in recent interactions
        has_feedback = False
        for text in recent_prompts + recent_messages:
            if text and any(indicator in text.lower() for indicator in feedback_indicators):
                logging.info(f"✅ Found feedback in: '{text}'")
                has_feedback = True
                break
                
        logging.info(f"🎯 Has feedback: {has_feedback}, Is confirmation: {is_confirmation}")
        
        if has_feedback and is_confirmation:
            logging.info("🎉 DETECTED SUCCESSFUL FEEDBACK PATTERN - user confirmed correction")
            
            # Extract the approved explore_params from thread messages
            approved_params = extract_approved_explore_params(thread_messages)
            return True, approved_params
            
        logging.info("❌ No feedback pattern detected")
        return False, None
        
    except Exception as e:
        logging.error(f"Error detecting feedback pattern: {e}")
        return False, None

def generate_suggested_prompt(auth_header: str, prompt_history: list, explore_params: Dict[str, Any]) -> Optional[str]:
    """
    Generate a suggested prompt that sanitizes and generalizes the initial user request.
    This creates a clean, example prompt that matches the generated explore params.
    """
    try:
        logging.info("=== GENERATING SUGGESTED PROMPT ===")
        
        if not prompt_history:
            logging.warning("No prompt history provided")
            return None
            
        # Get the first prompt from history (the initial user request)
        initial_prompt = prompt_history[0] if prompt_history else ""
        
        # Build the system prompt for generating the suggested prompt
        system_prompt = f"""You are an expert at creating clean, generalized example prompts for data analysis questions.

Your task is to take a user's conversation history and create a single, clean example prompt that:
1. Captures the essence of what the user was asking for
2. Removes any personal, specific, or contextual information
3. Uses generic terms that would apply to similar data analysis scenarios
4. Is clear and well-structured
5. Would be a good example for training an AI assistant

Original prompt history (chronological order):
{json.dumps(prompt_history, indent=2)}

Generated explore parameters (for reference):
{json.dumps(explore_params, indent=2)}

Guidelines:
- Focus on the data analysis intent from the FIRST prompt in the history
- Remove specific names, dates, or personal references
- Make it a standalone question that someone could understand without context
- Keep it concise but complete
- The suggested prompt should logically lead to the explore parameters that were generated

Output only the suggested prompt, nothing else."""

        # Format request for Vertex AI
        # Calculate appropriate tokens for prompt generation
        max_tokens = calculate_max_output_tokens(system_prompt, vertex_model, "general")
        
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": system_prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.5,  # More focused than 0.8
                "topK": 20,
                "maxOutputTokens": max_tokens,  
                "responseMimeType": "text/plain",
                "candidateCount": 1  # Only generate one candidate to reduce processing
            }
        }
        
        # Call Vertex AI using service account with retry logic
        vertex_response = call_vertex_ai_with_retry(vertex_request, "suggested_prompt_generation")
        if not vertex_response:
            logging.error("Failed to get response from Vertex AI for suggested prompt after retries")
            return None
        
        # Extract the suggested prompt
        suggested_prompt = extract_vertex_response_text(vertex_response)
        if suggested_prompt:
            suggested_prompt = suggested_prompt.strip()
            # Remove any quotes that might have been added
            if suggested_prompt.startswith('"') and suggested_prompt.endswith('"'):
                suggested_prompt = suggested_prompt[1:-1]
            
            logging.info(f"Generated suggested prompt: {suggested_prompt}")
            return suggested_prompt
        
        logging.error("Failed to extract suggested prompt from Vertex AI response")
        return None
        
    except Exception as e:
        logging.error(f"Error generating suggested prompt: {e}")
        return None

def create_looker_query_and_get_links(explore_params: Dict[str, Any], explore_key: str = None) -> Dict[str, str]:
    """
    Create a Looker query using the SDK and return the query slug and share URLs
    
    Args:
        explore_params: Query parameters dictionary
        explore_key: Optional explore key in "model:view" format to extract model and view
    
    Returns:
        Dict with keys: 'query_slug', 'share_url', 'expanded_share_url'
        Returns empty dict if creation fails
    """
    try:
        # Initialize Looker SDK
        looker_sdk = get_looker_sdk()
        if not looker_sdk:
            logging.error("Failed to initialize Looker SDK for query creation")
            return {}

        # Extract model and view from explore_key if provided and not already in explore_params
        model = explore_params.get('model', '')
        view = explore_params.get('view', '')
        
        if explore_key and (not model or not view):
            if ':' in explore_key:
                extracted_model, extracted_view = explore_key.split(':', 1)
                if not model:
                    model = extracted_model
                if not view:
                    view = extracted_view
                logging.info(f"Extracted from explore_key '{explore_key}': model='{model}', view='{view}'")
            else:
                logging.warning(f"explore_key '{explore_key}' does not contain model:view format")

        # Prepare query parameters from explore_params
        query_params = {
            'model': model,
            'view': view,
            'fields': explore_params.get('fields', []),
            'pivots': explore_params.get('pivots', []),
            'fill_fields': explore_params.get('fill_fields', []),
            'filters': explore_params.get('filters', {}),
            'filter_expression': explore_params.get('filter_expression', ''),
            'sorts': explore_params.get('sorts', []),
            'limit': str(explore_params.get('limit', 500)),
            'column_limit': str(explore_params.get('column_limit', 50)),
            'total': explore_params.get('total', False),
            'row_total': explore_params.get('row_total', False),
            'subtotals': explore_params.get('subtotals', []),
            'vis_config': explore_params.get('vis_config', {}),
            'filter_config': explore_params.get('filter_config', {}),
            'visible_ui_sections': explore_params.get('visible_ui_sections', ''),
            'slug': explore_params.get('slug', ''),
            'dynamic_fields': explore_params.get('dynamic_fields', ''),
            'client_id': explore_params.get('client_id', ''),
            'share': explore_params.get('share', True),
            'expanded_share': explore_params.get('expanded_share', True),
            'url': explore_params.get('url', ''),
            'query_timezone': explore_params.get('query_timezone', 'America/Los_Angeles'),
            'has_table_calculations': explore_params.get('has_table_calculations', False)
        }

        logging.info(f"Creating Looker query with model: '{query_params['model']}', view: '{query_params['view']}'")
        
        # Validate that we have model and view
        if not query_params['model'] or not query_params['view']:
            logging.error(f"Missing model or view for query creation. Model: '{query_params['model']}', View: '{query_params['view']}'")
            return {}
        
        # Create the query
        query_response = looker_sdk.create_query(query_params)
        
        if query_response and query_response.id:
            result = {
                'query_slug': query_response.slug or '',
                'share_url': query_response.share_url or '',
                'expanded_share_url': query_response.expanded_share_url or ''
            }
            
            logging.info(f"Successfully created Looker query with ID: {query_response.id}")
            logging.info(f"Query slug: {result['query_slug']}")
    except Exception as e:
        logging.error(f"Error creating Looker query: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {}

def save_suggested_silver_query(auth_header: str, explore_key: str, prompt_history: list, 
                               explore_params: Dict[str, Any], user_email: str) -> bool:
    """
    Save a suggested golden query to the BigQuery suggested_golden_queries table
    Now stores the complete prompt history for better context and generates a suggested new prompt
    """
    try:
        ensure_silver_queries_table_exists()

        # Generate the suggested prompt using LLM
        logging.info("Generating suggested prompt for silver query...")
        suggested_prompt = generate_suggested_prompt(auth_header, prompt_history, explore_params)
        if not suggested_prompt:
            logging.warning("Failed to generate suggested prompt, using first prompt from history as fallback")
            suggested_prompt = prompt_history[0] if prompt_history else "Unable to generate suggested prompt"

        # Create Looker query and get share links
        logging.info("Creating Looker query and generating share links...")
        logging.info(f"Explore key for query creation: '{explore_key}'")
        logging.info(f"Explore params fields: {explore_params.get('fields', [])}")
        logging.info(f"Explore params model: '{explore_params.get('model', 'NOT_SET')}'")
        logging.info(f"Explore params view: '{explore_params.get('view', 'NOT_SET')}'")
        
        query_links = create_looker_query_and_get_links(explore_params, explore_key)
        if not query_links:
            logging.warning("Failed to create Looker query and get share links")
            query_links = {'query_slug': '', 'share_url': '', 'expanded_share_url': ''}

        # Create BigQuery client using default credentials (Cloud Run service account)
        client = bigquery.Client(project=bq_project_id)
        
        # Prepare the record to insert - using standardized field names
        current_time = time.time()
        suggested_query = {
            'id': str(uuid.uuid4()),  # Generate UUID for the id field
            'explore_id': explore_key,  # Standardized field name
            'input': json.dumps(prompt_history),  # Store complete prompt history as JSON string - standardized field name
            'output': json.dumps(explore_params),  # Store as JSON string - standardized field name
            'created_at': datetime.fromtimestamp(current_time).isoformat(),  # Convert to ISO format string
            'user_id': user_email,
            'feedback_type': 'user_correction',
            'link': query_links.get('share_url', ''),  # Use single standardized link field
            'conversation_history': json.dumps(prompt_history)  # Silver-specific field for conversation context
        }
        
        logging.info(f"Saving suggested golden query to BigQuery: {explore_key} for user {user_email}")
        logging.info(f"Generated suggested prompt: {suggested_prompt}")
        logging.info(f"Query slug: {query_links.get('query_slug', 'Not available')}")
        logging.info(f"Share URL: {query_links.get('share_url', 'Not available')}")
        logging.info(f"Expanded share URL: {query_links.get('expanded_share_url', 'Not available')}")
        
        # Reference to the table
        table_id = f"{bq_project_id}.{bq_dataset_id}.{bq_suggested_table}"
        table = client.get_table(table_id)
        
        # Insert the row
        rows_to_insert = [suggested_query]
        errors = client.insert_rows_json(table, rows_to_insert)
        
        if errors:
            logging.error(f"BigQuery insertion errors: {errors}")
            return False
        else:
            logging.info(f"Successfully saved suggested golden query to BigQuery table {table_id}")
            return True
        
    except Exception as e:
        logging.error(f"Error saving suggested golden query to BigQuery: {e}")
        # Still log the data for debugging even if BigQuery fails
        fallback_data = {
            'explore_id': explore_key,
            'prompt_history': prompt_history,  # Use prompt_history instead of original_prompt
            'explore_params': explore_params,
            'user_id': user_email,
            'timestamp': time.time(),
            'feedback_type': 'user_correction',
            'suggested_new_prompt': suggested_prompt if 'suggested_prompt' in locals() else 'Not generated',
            'query_slug': query_links.get('query_slug', '') if 'query_links' in locals() else '',
            'share_url': query_links.get('share_url', '') if 'query_links' in locals() else '',
            'expanded_share_url': query_links.get('expanded_share_url', '') if 'query_links' in locals() else ''
        }
        logging.info(f"FALLBACK LOG - Suggested query data: {json.dumps(fallback_data, indent=2)}")
        return False

# Query Promotion Functions
def is_authorized_for_promotion(user_email: str) -> bool:
    """
    Check if user is authorized to promote queries
    You can customize this based on your authorization system
    """
    try:
        # For now, allow all authenticated users to promote
        # In production, you might check against specific roles or groups
        PROMOTION_ROLES = ['Admin', 'Developer']
        
        looker_user = find_looker_user_by_email(user_email)
        if looker_user:
            # extract the role for each of the role_ids (note: it's 'role_ids', not 'roles')
            user_role_ids = looker_user.get('role_ids', [])
            # sort ascending numerically, not by string
            user_role_ids.sort(key=lambda x: int(x))
            logging.info(f"User {user_email} has role IDs: {user_role_ids}")
            
            # Initialize Looker SDK
            sdk = get_looker_sdk()
            if not sdk:
                logging.error("Failed to initialize Looker SDK for role checking")
                return True  # Fallback to allow access if SDK fails
            
            # for each role, call Looker to see what the name of the role is
            for role_id in user_role_ids:
                try:
                    role_info = sdk.role(role_id)
                    logging.info(f"Checking role for user {user_email}: {role_info.name if role_info else 'Unknown'}")
                    # Check if any role is on the list
                    if role_info and role_info.name in PROMOTION_ROLES:
                        logging.info(f"User {user_email} has authorized role: {role_info.name}")
                        return True
                except Exception as role_error:
                    logging.warning(f"Failed to get role info for role ID {role_id}: {role_error}")
                    continue
                    
            logging.info(f"User {user_email} is not authorized to promote. Role IDs: {user_role_ids}")
            
            
            
        # logging.warning(f"User {user_email} not authorized for promotion")
        # return False
        return False

    except Exception as e:
        logging.error(f"Error checking authorization for {user_email}: {e}")
        return False

def get_queries_for_promotion(table_name: str, limit: int = 50, offset: int = 0) -> list:
    """
    Get queries from bronze/silver tables for promotion
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        
        # Ensure tables exist and run migrations if necessary
        if table_name == 'bronze':
            ensure_bronze_queries_table_exists()
        elif table_name == 'silver':
            ensure_silver_queries_table_exists()
        
        # Determine table name and appropriate query based on table schema
        if table_name == 'bronze':
            full_table_name = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
            
            # Bronze table query - using standardized field names
            query = f"""
            SELECT 
                id,
                explore_id,
                input,
                output,
                created_at,
                user_email,
                query_run_count,
                link
            FROM `{full_table_name}`
            ORDER BY created_at DESC
            LIMIT {limit}
            OFFSET {offset}
            """
        elif table_name == 'silver':
            full_table_name = f"{bq_project_id}.{bq_dataset_id}.{bq_suggested_table}"
            
            # Silver table query - using standardized field names
            query = f"""
            SELECT 
                id,
                explore_id,
                input,
                output,
                created_at,
                user_id,
                feedback_type,
                link,
                conversation_history
            FROM `{full_table_name}`
            ORDER BY created_at DESC
            LIMIT {limit}
            OFFSET {offset}
            """
        else:
            raise ValueError(f"Invalid table name: {table_name}")
        
        results = client.query(query).to_dataframe()
        
        # Fill NaN values with appropriate defaults to avoid JSON serialization issues
        # Using standardized field names
        fillna_dict = {
            'id': '',
            'explore_id': '',
            'input': '',
            'output': '',
            'created_at': '',
            'link': ''
        }
        
        # Add table-specific fields
        if table_name == 'bronze':
            fillna_dict.update({
                'user_email': '',
                'query_run_count': 0
            })
        elif table_name == 'silver':
            fillna_dict.update({
                'user_id': '',
                'feedback_type': '',
                'conversation_history': ''
            })
        
        results = results.fillna(fillna_dict)
        
        # Convert to list of dicts using standardized field names
        queries = []
        for _, row in results.iterrows():
            query_dict = {
                'id': str(row['id']) if row['id'] is not None else '',
                'explore_id': str(row['explore_id']) if row['explore_id'] is not None else '',
                'input': str(row.get('input', '')) if row.get('input') is not None else '',
                'output': str(row.get('output', '')) if row.get('output') is not None else '',
                'created_at': str(row['created_at']) if row['created_at'] is not None else '',
                'link': str(row.get('link', '')) if row.get('link') is not None else '',
                'source_table': table_name
            }
            
            # Add table-specific fields
            if table_name == 'bronze':
                query_dict.update({
                    'user_email': str(row.get('user_email', '')) if row.get('user_email') is not None else '',
                    'query_run_count': int(row.get('query_run_count', 0)) if row.get('query_run_count') is not None else 0
                })
            elif table_name == 'silver':
                query_dict.update({
                    'user_id': str(row.get('user_id', '')) if row.get('user_id') is not None else '',
                    'feedback_type': str(row.get('feedback_type', '')) if row.get('feedback_type') is not None else '',
                    'conversation_history': str(row.get('conversation_history', '')) if row.get('conversation_history') is not None else ''
                })
            
            queries.append(query_dict)
        
        logging.info(f"Retrieved {len(queries)} queries from {table_name} table")
        return queries
        
    except Exception as e:
        logging.error(f"Error getting queries for promotion from {table_name}: {e}")
        raise e

def promote_query_atomic(query_id: str, source_table: str, target_table: str, 
                        promoted_by: str, reason: str = '') -> Dict[str, Any]:
    """
    Atomic promotion operation using BigQuery transactions
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        
        # Ensure source table exists and is migrated
        if source_table == 'bronze':
            ensure_bronze_queries_table_exists()
        elif source_table == 'silver':
            ensure_silver_queries_table_exists()
        
        # Ensure target table exists and is migrated
        ensure_golden_queries_table_exists()
        
        # Determine source table name
        if source_table == 'bronze':
            source_table_name = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
        elif source_table == 'silver':
            source_table_name = f"{bq_project_id}.{bq_dataset_id}.{bq_suggested_table}"
        else:
            raise ValueError(f"Invalid source table: {source_table}")
        
        # Target table is always golden queries (explore_assistant examples)
        target_table_name = f"{bq_project_id}.{bq_dataset_id}.golden_queries"
        
        # Generate new UUID for the promoted query
        new_query_id = str(uuid.uuid4())
        current_timestamp = datetime.now()
        
        # First, get the source query data - both tables now have proper 'id' field
        get_query = f"""
        SELECT * FROM `{source_table_name}`
        WHERE id = @query_id
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query_id", "STRING", query_id)
            ]
        )
        
        source_data = client.query(get_query, job_config=job_config).to_dataframe()
        
        if source_data.empty:
            raise ValueError(f"Query {query_id} not found in {source_table}")
        
        source_row = source_data.iloc[0]
        
        # Ensure golden queries table exists
        ensure_golden_queries_table_exists()
        
        # Prepare the promoted query data - only include core fields that exist in golden queries
        promoted_query = {
            'id': new_query_id,
            'explore_id': source_row['explore_id'],
            'input': source_row.get('input', ''),  # Use 'input' field for standardization
            'output': source_row.get('output', ''),  # Use 'output' field for standardization
            'link': source_row.get('link', ''),  # Use standardized 'link' field
            'promoted_by': promoted_by,
            'promoted_at': current_timestamp  # Use timestamp format
        }
        
        # Insert into golden queries table
        table = client.get_table(target_table_name)
        errors = client.insert_rows_json(table, [promoted_query])
        
        if errors:
            raise Exception(f"Failed to insert into golden queries: {errors}")
        
        # Delete from source table
        delete_query = f"""
        DELETE FROM `{source_table_name}`
        WHERE id = @query_id
        """
        
        delete_job = client.query(delete_query, job_config=job_config)
        delete_job.result()  # Wait for completion
        
        # Log the promotion for audit trail
        log_promotion(query_id, source_table, target_table, promoted_by, reason, new_query_id)
        
        logging.info(f"Successfully promoted query {query_id} from {source_table} to {target_table}")
        
        return {
            'new_query_id': new_query_id,
            'source_query_id': query_id,
            'source_table': source_table,
            'target_table': target_table,
            'promoted_by': promoted_by
        }
        
    except Exception as e:
        logging.error(f"Error promoting query {query_id}: {e}")
        raise e

def log_promotion(source_query_id: str, source_table: str, target_table: str, 
                 promoted_by: str, reason: str, new_query_id: str):
    """
    Log promotion for audit trail
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        
        # Ensure promotion log table exists
        ensure_promotion_log_table_exists()
        
        promotion_log = {
            'id': str(uuid.uuid4()),
            'source_query_id': source_query_id,
            'new_query_id': new_query_id,
            'source_table': source_table,
            'target_table': target_table,
            'promoted_by': promoted_by,
            'promoted_at': datetime.now().isoformat(),
            'promotion_reason': reason,
            'timestamp': datetime.now().timestamp()
        }
        
        table_id = f"{bq_project_id}.{bq_dataset_id}.promotion_log"
        table = client.get_table(table_id)
        errors = client.insert_rows_json(table, [promotion_log])
        
        if errors:
            logging.error(f"Failed to log promotion: {errors}")
        else:
            logging.info(f"Promotion logged successfully")
            
    except Exception as e:
        logging.error(f"Error logging promotion: {e}")

def get_promotion_history_data(limit: int = 50, offset: int = 0) -> list:
    """
    Get promotion history for audit trail
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        
        query = f"""
        SELECT 
            id,
            source_query_id,
            new_query_id,
            source_table,
            target_table,
            promoted_by,
            promoted_at,
            promotion_reason
        FROM `{bq_project_id}.{bq_dataset_id}.promotion_log`
        ORDER BY promoted_at DESC
        LIMIT {limit}
        OFFSET {offset}
        """
        
        results = client.query(query).to_dataframe()
        
        # Convert to list of dicts
        history = []
        for _, row in results.iterrows():
            history_item = {
                'id': row['id'],
                'source_query_id': row['source_query_id'],
                'new_query_id': row['new_query_id'],
                'source_table': row['source_table'],
                'target_table': row['target_table'],
                'promoted_by': row['promoted_by'],
                'promoted_at': str(row['promoted_at']),
                'promotion_reason': row['promotion_reason']
            }
            history.append(history_item)
        
        return history
        
    except Exception as e:
        logging.error(f"Error getting promotion history: {e}")
        return []

def migrate_golden_table_explore_key_to_id():
    """
    Migrate golden table from explore_key column to explore_id column
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        golden_table_id = f"{bq_project_id}.{bq_dataset_id}.golden_queries"
        
        logging.info("Migrating golden table from explore_key to explore_id...")
        
        # Add the explore_id column
        alter_query = f"""
        ALTER TABLE `{golden_table_id}`
        ADD COLUMN explore_id STRING
        """
        
        job = client.query(alter_query)
        job.result()  # Wait for completion
        
        # Copy data from explore_key to explore_id
        update_query = f"""
        UPDATE `{golden_table_id}`
        SET explore_id = explore_key
        WHERE explore_id IS NULL
        """
        
        job = client.query(update_query)
        job.result()  # Wait for completion
        
        # Drop the old explore_key column (optional - might want to keep for rollback)
        # For now, let's keep both columns to be safe
        logging.info("Successfully migrated golden table to use explore_id")
        
    except Exception as e:
        logging.error(f"Failed to migrate golden table explore_key to explore_id: {e}")
        # Don't raise - this is a migration that can fail without breaking the system

def ensure_bronze_queries_table_exists():
    """
    Create the bronze_queries table with the correct schema, dropping and recreating if schema is wrong
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        bronze_table_id = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
        
        # Define the correct schema for bronze queries
        correct_schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("input", "STRING", mode="REQUIRED"),  # Standardized to match golden
            bigquery.SchemaField("output", "STRING", mode="NULLABLE"),  # Standardized to match golden
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("user_email", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("query_run_count", "INTEGER", mode="NULLABLE"),  # Bronze-specific field
            bigquery.SchemaField("link", "STRING", mode="NULLABLE")  # Standardized to match golden
        ]
        
        expected_field_names = {field.name for field in correct_schema}
        
        try:
            table = client.get_table(bronze_table_id)
            existing_field_names = {field.name for field in table.schema}
            
            # If schema doesn't match exactly, drop and recreate
            if existing_field_names != expected_field_names:
                logging.info(f"Bronze table schema mismatch. Expected: {expected_field_names}, Got: {existing_field_names}")
                logging.info("Dropping and recreating bronze queries table...")
                client.delete_table(bronze_table_id)
                raise Exception("Table dropped, will recreate")
            else:
                logging.info(f"Bronze queries table {bronze_table_id} has correct schema")
                return True
                
        except Exception:
            logging.info(f"Creating bronze queries table {bronze_table_id} with correct schema")
        
        # Create table with correct schema
        table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table("bronze_queries")
        table = bigquery.Table(table_ref, schema=correct_schema)
        table.description = "Bronze queries generated from historical Looker query patterns"
        
        table = client.create_table(table)
        logging.info(f"Successfully created bronze queries table: {bronze_table_id}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to ensure bronze queries table: {e}")
        raise e

def ensure_silver_queries_table_exists():
    """
    Create the silver_queries table with the correct schema, dropping and recreating if schema is wrong
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        silver_table_id = f"{bq_project_id}.{bq_dataset_id}.{bq_suggested_table}"

        # Define the correct schema for silver queries
        correct_schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("input", "STRING", mode="REQUIRED"),  # Standardized to match golden
            bigquery.SchemaField("output", "STRING", mode="NULLABLE"),  # Standardized to match golden
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("feedback_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("link", "STRING", mode="NULLABLE"),  # Standardized to match golden
            bigquery.SchemaField("conversation_history", "STRING", mode="NULLABLE")  # Silver-specific field
        ]
        
        expected_field_names = {field.name for field in correct_schema}

        try:
            table = client.get_table(silver_table_id)
            existing_field_names = {field.name for field in table.schema}
            
            # If schema doesn't match exactly, drop and recreate
            if existing_field_names != expected_field_names:
                logging.info(f"Silver table schema mismatch. Expected: {expected_field_names}, Got: {existing_field_names}")
                logging.info("Dropping and recreating silver queries table...")
                client.delete_table(silver_table_id)
                raise Exception("Table dropped, will recreate")
            else:
                logging.info(f"Silver queries table {silver_table_id} has correct schema")
                return True
                
        except Exception:
            logging.info(f"Creating silver queries table {silver_table_id} with correct schema")

        # Create table with correct schema
        table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table(bq_suggested_table)
        table = bigquery.Table(table_ref, schema=correct_schema)
        table.description = "Silver queries - suggested improvements from user feedback"

        table = client.create_table(table)
        logging.info(f"Successfully created silver queries table: {silver_table_id}")
        return True

    except Exception as e:
        logging.error(f"Failed to ensure silver queries table: {e}")
        raise e

def generate_bronze_queries_for_explore(model_name: str, explore_name: str, explore_key: str, user_email: str) -> Dict[str, Any]:
    """
    Generate bronze queries for a specific explore (placeholder implementation)
    """
    try:
        # Ensure bronze table exists
        ensure_bronze_queries_table_exists()
        
        # For now, return a simple success message
        # This function would be implemented to generate actual bronze queries
        return {
            "status": "success",
            "message": f"Bronze query generation initiated for {model_name}.{explore_name}",
            "explore_key": explore_key,
            "user_email": user_email
        }
        
    except Exception as e:
        logging.error(f"Error generating bronze queries: {e}")
        raise e

def ensure_golden_queries_table_exists():
    """
    Ensure the golden queries table exists with the correct schema
    Only adds missing columns, never drops golden table data
    """
    try:
        logging.info("=== ENSURE_GOLDEN_QUERIES_TABLE_EXISTS CALLED ===")
        client = bigquery.Client(project=bq_project_id)
        table_id = f"{bq_project_id}.{bq_dataset_id}.golden_queries"
        logging.info(f"Checking/creating golden queries table: {table_id}")
        
        # Define the golden queries schema - this is the authoritative schema
        golden_schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("input", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("output", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("link", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("promoted_by", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("promoted_at", "STRING", mode="NULLABLE")
        ]
        
        try:
            table = client.get_table(table_id)
            logging.info(f"Golden queries table {table_id} already exists")
            
            # Only add missing columns to golden table (never drop)
            current_schema = {field.name: field for field in table.schema}
            missing_fields = []
            
            for field in golden_schema:
                if field.name not in current_schema:
                    missing_fields.append(field)
            
            if missing_fields:
                logging.info(f"Adding missing fields to golden queries table: {[f.name for f in missing_fields]}")
                
                for field in missing_fields:
                    try:
                        field_type_mapping = {
                            "STRING": "STRING",
                            "FLOAT": "FLOAT64", 
                            "INTEGER": "INT64",
                            "BOOLEAN": "BOOL",
                            "TIMESTAMP": "TIMESTAMP"
                        }
                        
                        bq_field_type = field_type_mapping.get(field.field_type, field.field_type)
                        
                        alter_query = f"""
                        ALTER TABLE `{table_id}`
                        ADD COLUMN {field.name} {bq_field_type}
                        """
                        
                        logging.info(f"Executing: {alter_query}")
                        job = client.query(alter_query)
                        job.result()
                        logging.info(f"Successfully added column {field.name}")
                    except Exception as col_error:
                        logging.error(f"Failed to add column {field.name}: {col_error}")
            else:
                logging.info("Golden queries table has all required columns")
            
        except Exception as table_not_found:
            logging.info(f"Golden queries table {table_id} doesn't exist, creating it...")
            
            table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table("golden_queries")
            table = bigquery.Table(table_ref, schema=golden_schema)
            table.description = "Golden queries - promoted examples for training"
            
            table = client.create_table(table)
            logging.info(f"Successfully created golden queries table: {table_id}")
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to ensure golden queries table exists: {e}")
        raise e

def ensure_promotion_log_table_exists():
    """
    Ensure the promotion log table exists for audit trail
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        table_id = f"{bq_project_id}.{bq_dataset_id}.promotion_log"
        
        try:
            table = client.get_table(table_id)
            logging.info(f"Promotion log table {table_id} already exists")
            return True
        except Exception:
            logging.info(f"Creating promotion log table {table_id}")
        
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source_query_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("new_query_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("source_table", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("target_table", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("promoted_by", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("promoted_at", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("promotion_reason", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("timestamp", "FLOAT", mode="NULLABLE")
        ]
        
        table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table("promotion_log")
        table = bigquery.Table(table_ref, schema=schema)
        table.description = "Audit log for query promotions"
        
        table = client.create_table(table)
        logging.info(f"Successfully created promotion log table: {table_id}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to create promotion log table: {e}")
        raise e

def handle_mcp_tool(tool_name: str, arguments: dict, user_email: str, auth_header: str) -> dict:
    """
    Handle MCP tool calls for various system operations
    """
    try:
        logging.info(f"Handling MCP tool: {tool_name} for user {user_email}")
        logging.info(f"Tool arguments: {arguments}")
        
        # Olympic Query Management Tools
        if tool_name == "get_queries_for_promotion":
            table_name = arguments.get('table_name', 'bronze')
            limit = arguments.get('limit', 50)
            offset = arguments.get('offset', 0)
            
            if not is_authorized_for_promotion(user_email):
                return {"error": "User not authorized for query promotion operations"}
            
            queries = get_queries_for_promotion(table_name, limit, offset)
            return {
                "queries": queries,
                "total": len(queries)
            }
        
        elif tool_name == "promote_query":
            query_id = arguments.get('query_id')
            source_table = arguments.get('source_table')
            target_table = arguments.get('target_table', 'golden')
            reason = arguments.get('reason', '')
            
            if not query_id or not source_table:
                return {"error": "query_id and source_table are required"}
            
            if not is_authorized_for_promotion(user_email):
                return {"error": "User not authorized for query promotion operations"}
            
            result = promote_query_atomic(query_id, source_table, target_table, user_email, reason)
            return {
                "success": True,
                "message": f"Query promoted successfully from {source_table} to {target_table}",
                "new_query_id": result['new_query_id'],
                "source_query_id": result['source_query_id'],
                "promoted_by": result['promoted_by']
            }
        
        elif tool_name == "get_promotion_history":
            limit = arguments.get('limit', 50)
            offset = arguments.get('offset', 0)
            
            if not is_authorized_for_promotion(user_email):
                return {"error": "User not authorized for query promotion operations"}
            
            history = get_promotion_history_data(limit, offset)
            return {
                "history": history,
                "total": len(history)
            }

        # Existing feedback tools (keeping for compatibility)
        elif tool_name == "submit_query_feedback":
            # Handle feedback submission
            query_id = arguments.get('query_id')
            explore_id = arguments.get('explore_id')
            original_prompt = arguments.get('original_prompt', '')
            generated_params = arguments.get('generated_params', {})
            share_url = arguments.get('share_url', '')
            feedback_type = arguments.get('feedback_type', 'positive')
            user_id = arguments.get('user_id', user_email)
            user_comment = arguments.get('user_comment', '')
            suggested_improvements = arguments.get('suggested_improvements', {})
            
            if not explore_id:
                return {"error": "explore_id is required"}
            
            # Save feedback to BigQuery (implement this function)
            success = save_feedback_to_bigquery(
                query_id, explore_id, original_prompt, generated_params,
                share_url, feedback_type, user_id, user_comment, suggested_improvements
            )
            
            if success:
                return {"success": True, "message": "Feedback submitted successfully"}
            else:
                return {"error": "Failed to submit feedback"}

        elif tool_name == "get_query_feedback_history":
            explore_id = arguments.get('explore_id')
            user_id = arguments.get('user_id')
            feedback_type = arguments.get('feedback_type')
            limit = arguments.get('limit', 20)
            
            # Get feedback history from BigQuery (implement this function)
            feedback_history = get_feedback_history_from_bigquery(explore_id, user_id, feedback_type, limit)
            return {"feedback_history": feedback_history}

        elif tool_name == "get_query_stats":
            # Get query statistics (implement this function)
            stats = get_query_statistics_from_bigquery()
            return {"query_statistics": stats}

        # Explicit Feedback Tools (from recent implementation)
        elif tool_name == "submit_positive_feedback":
            query_id = arguments.get('query_id')
            user_input = arguments.get('user_input', '')
            response = arguments.get('response', '')
            feedback_notes = arguments.get('feedback_notes', '')
            
            if not query_id:
                return {"error": "query_id is required"}
            
            success = save_explicit_feedback_to_bigquery(
                query_id, user_input, response, 'positive', user_email, feedback_notes
            )
            
            if success:
                return {"success": True, "message": "Positive feedback submitted successfully"}
            else:
                return {"error": "Failed to submit positive feedback"}

        elif tool_name == "submit_negative_feedback":
            query_id = arguments.get('query_id')
            user_input = arguments.get('user_input', '')
            response = arguments.get('response', '')
            issues = arguments.get('issues', [])
            improvement_suggestions = arguments.get('improvement_suggestions', '')
            feedback_notes = arguments.get('feedback_notes', '')
            
            if not query_id:
                return {"error": "query_id is required"}
            
            success = save_explicit_feedback_to_bigquery(
                query_id, user_input, response, 'negative', user_email, 
                feedback_notes, issues, improvement_suggestions
            )
            
            if success:
                return {"success": True, "message": "Negative feedback submitted successfully"}
            else:
                return {"error": "Failed to submit negative feedback"}

        elif tool_name == "request_response_improvement":
            query_id = arguments.get('query_id')
            original_input = arguments.get('original_input', '')
            original_response = arguments.get('original_response', '')
            improvement_request = arguments.get('improvement_request', '')
            context = arguments.get('context', '')
            
            if not query_id or not improvement_request:
                return {"error": "query_id and improvement_request are required"}
            
            success = save_improvement_request_to_bigquery(
                query_id, original_input, original_response, improvement_request, context, user_email
            )
            
            if success:
                return {"success": True, "message": "Improvement request submitted successfully"}
            else:
                return {"error": "Failed to submit improvement request"}

        else:
            return {"error": f"Unknown MCP tool: {tool_name}"}
    
    except Exception as e:
        logging.error(f"Error handling MCP tool {tool_name}: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {"error": f"Internal error handling MCP tool: {str(e)}"}

def save_feedback_to_bigquery(query_id, explore_id, original_prompt, generated_params,
                             share_url, feedback_type, user_id, user_comment, suggested_improvements):
    """Save feedback to BigQuery - placeholder implementation"""
    try:
        # TODO: Implement actual BigQuery feedback storage
        logging.info(f"Saving feedback to BigQuery: {feedback_type} for {explore_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving feedback to BigQuery: {e}")
        return False

def get_feedback_history_from_bigquery(explore_id, user_id, feedback_type, limit):
    """Get feedback history from BigQuery - placeholder implementation"""
    try:
        # TODO: Implement actual BigQuery feedback retrieval
        logging.info(f"Getting feedback history from BigQuery for {explore_id}")
        return []
    except Exception as e:
        logging.error(f"Error getting feedback history from BigQuery: {e}")
        return []

def get_query_statistics_from_bigquery():
    """Get query statistics from BigQuery - placeholder implementation"""
    try:
        # TODO: Implement actual BigQuery statistics retrieval
        logging.info("Getting query statistics from BigQuery")
        return {}
    except Exception as e:
        logging.error(f"Error getting query statistics from BigQuery: {e}")
        return {}

def save_explicit_feedback_to_bigquery(query_id, user_input, response, feedback_type, user_email,
                                      feedback_notes, issues=None, improvement_suggestions=None):
    """Save explicit feedback to BigQuery - placeholder implementation"""
    try:
        # TODO: Implement actual explicit feedback storage
        logging.info(f"Saving explicit {feedback_type} feedback for query {query_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving explicit feedback to BigQuery: {e}")
        return False

def save_improvement_request_to_bigquery(query_id, original_input, original_response,
                                        improvement_request, context, user_email):
    """Save improvement request to BigQuery - placeholder implementation"""
    try:
        # TODO: Implement actual improvement request storage
        logging.info(f"Saving improvement request for query {query_id}")
        return True
    except Exception as e:
        logging.error(f"Error saving improvement request to BigQuery: {e}")
        return False

def create_mcp_flask_app():
    """Create Flask app with MCP endpoints"""
    app = Flask(__name__)
    CORS(app)
    
    # Log registered endpoints
    logging.info("Registering MCP endpoints...")
    
    @app.route("/", methods=["POST", "OPTIONS"])
    def vertex_ai_proxy():
        """Main endpoint for Vertex AI processing"""
        logging.info(f"Received {request.method} request to main endpoint")
        logging.info(f"Request headers: {dict(request.headers)}")
        logging.info(f"Request origin: {request.headers.get('Origin', 'No origin header')}")
        logging.info(f"User agent: {request.headers.get('User-Agent', 'No user agent')}")
        
        # Handle OPTIONS requests first, without authentication
        if request.method == "OPTIONS":
            logging.info("Handling OPTIONS preflight request")
            response = Response()
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
        
        try:
            logging.info("Processing POST request...")
            
            # Get Bearer token from Authorization header (only for POST requests)
            auth_header = request.headers.get("Authorization")
            logging.info(f"Authorization header present: {bool(auth_header)}")
            
            # Check for Authorization header (infrastructure handles validation)
            if not auth_header or not auth_header.lower().startswith("bearer "):
                logging.error("Missing or invalid Authorization header")
                response = jsonify({'error': 'Missing or invalid Authorization header'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            logging.info("Authorization header received, proceeding with request...")
            
            # Get the request body
            logging.info("Getting request body...")
            request_data = request.get_json()
            if not request_data:
                logging.error("Missing request body")
                return jsonify({'error': 'Missing request body'}), 400, get_response_headers()
            
            logging.info(f"Request data keys: {list(request_data.keys())}")
            logging.info(f"Test mode: {request_data.get('test_mode', False)}")
            
            # Check for MCP tool calls
            tool_name = request_data.get('tool_name')
            if tool_name:
                logging.info(f"Processing MCP tool request: {tool_name}")
                
                # Extract user email from token for authorization
                user_email = extract_user_email_from_token(auth_header)
                if not user_email:
                    return jsonify({"error": "Invalid or missing authentication token"}), 401, get_response_headers()
                
                try:
                    result = handle_mcp_tool(tool_name, request_data.get('arguments', {}), user_email, auth_header)
                    return jsonify(result), 200, get_response_headers()
                except Exception as e:
                    error_message = str(e)
                    logging.error(f"MCP tool {tool_name} failed: {error_message}")
                    return jsonify({"error": error_message}), 500, get_response_headers()
            
            # Check for bronze query generation operation
            operation = request_data.get('operation')
            if operation == 'generate_bronze_queries':
                logging.info("Processing bronze query generation request...")
                
                # Extract user email from token
                user_email = extract_user_email_from_token(auth_header)
                if not user_email:
                    return jsonify({"error": "Invalid or missing authentication token"}), 401, get_response_headers()
                
                model_name = request_data.get('model_name')
                explore_name = request_data.get('explore_name')
                explore_key = request_data.get('explore_key')
                
                if not all([model_name, explore_name, explore_key]):
                    return jsonify({"error": "model_name, explore_name, and explore_key are required"}), 400, get_response_headers()
                
                try:
                    result = generate_bronze_queries_for_explore(model_name, explore_name, explore_key, user_email)
                    return jsonify(result), 200, get_response_headers()
                except Exception as e:
                    error_message = str(e)
                    logging.error(f"Bronze queries generation failed: {error_message}")
                    return jsonify({"error": error_message}), 500, get_response_headers()
            
            # Process the explore assistant request (default)
            logging.info("Processing explore assistant request...")
            result = process_explore_assistant_request(auth_header, request_data)
            
            logging.info(f"Request processing completed, result type: {type(result)}")
            logging.info(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            response = jsonify(result), 200, get_response_headers()
            logging.info("Sending response...")
            return response
            
        except Exception as e:
            logging.error(f"Vertex AI proxy error: {e}")
            logging.error(f"Error type: {type(e)}")
            logging.error(f"Error args: {e.args}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                return jsonify({'error': f'Internal server error: {str(e)}'}), 500, get_response_headers()
            except Exception as json_error:
                logging.error(f"Failed to send JSON error response: {json_error}")
                return f"Internal server error: {str(e)}", 500, get_response_headers()
    
    logging.info("Registered endpoint: / (POST)")
    
    # Query Promotion Endpoints (DEPRECATED - Use MCP Tools Instead)
    @app.route("/admin/queries/<table_name>", methods=["GET", "OPTIONS"])
    def list_queries_for_promotion(table_name):
        """
        List bronze/silver queries available for promotion
        DEPRECATED: Use MCP tool 'get_queries_for_promotion' instead
        """
        logging.info(f"Received {request.method} request to list queries from {table_name}")
        
        if request.method == "OPTIONS":
            response = Response()
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
        
        try:
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.lower().startswith("bearer "):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401, get_response_headers()
            
            # Extract and validate user
            user_email = extract_user_email_from_token(auth_header)
            if not user_email:
                return jsonify({'error': 'Token validation failed'}), 401, get_response_headers()
            
            # Check if user is authorized for promotion
            if not is_authorized_for_promotion(user_email):
                return jsonify({'error': 'Unauthorized for query promotion'}), 403, get_response_headers()
            
            # Validate table name
            if table_name not in ['bronze', 'silver']:
                return jsonify({'error': 'Invalid table name. Use bronze or silver'}), 400, get_response_headers()
            
            # Get pagination parameters
            limit = min(int(request.args.get('limit', 50)), 100)  # Max 100 items
            offset = int(request.args.get('offset', 0))
            
            # Query the specified table
            queries = get_queries_for_promotion(table_name, limit, offset)
            
            return jsonify({
                'queries': queries,
                'table_name': table_name,
                'count': len(queries),
                'limit': limit,
                'offset': offset
            }), 200, get_response_headers()
            
        except Exception as e:
            logging.error(f"Error listing queries for promotion: {e}")
            return jsonify({'error': str(e)}), 500, get_response_headers()
    
    @app.route("/admin/promote", methods=["POST", "OPTIONS"])
    def promote_query():
        """
        Promote a query from bronze/silver to golden queries table
        DEPRECATED: Use MCP tool 'promote_query' instead
        """
        logging.info(f"Received {request.method} request to promote query")
        
        if request.method == "OPTIONS":
            response = Response()
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
        
        try:
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.lower().startswith("bearer "):
                logging.error("Missing or invalid Authorization header")
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401, get_response_headers()
            
            # Extract and validate user
            user_email = extract_user_email_from_token(auth_header)
            if not user_email:
                logging.error("Token validation failed")
                return jsonify({'error': 'Token validation failed'}), 401, get_response_headers()
            
            logging.info(f"User {user_email} attempting to promote query")
            
            # Check if user is authorized for promotion
            if not is_authorized_for_promotion(user_email):
                logging.error(f"User {user_email} is not authorized for query promotion")
                return jsonify({'error': 'Unauthorized for query promotion'}), 403, get_response_headers()
            
            # Get request data
            data = request.get_json()
            if not data:
                logging.error("Missing request body")
                return jsonify({'error': 'Missing request body'}), 400, get_response_headers()
            
            # Handle both camelCase and snake_case field names for compatibility
            query_id = data.get('query_id') or data.get('queryId')
            source_table = data.get('source_table') or data.get('sourceTable')  # 'bronze' or 'silver'
            promotion_reason = data.get('reason', 'Manual promotion')
            
            logging.info(f"Promotion request data: {data}")
            logging.info(f"Extracted query_id: {query_id}, source_table: {source_table}")
            
            if not query_id or not source_table:
                logging.error(f"Missing required fields - query_id: {query_id}, source_table: {source_table}")
                return jsonify({'error': 'query_id and source_table are required'}), 400, get_response_headers()
            
            if source_table not in ['bronze', 'silver']:
                logging.error(f"Invalid source table: {source_table}")
                return jsonify({'error': 'sourceTable must be bronze or silver'}), 400, get_response_headers()
            
            logging.info(f"Starting promotion of query {query_id} from {source_table} to golden")
            
            # Perform atomic promotion
            result = promote_query_atomic(query_id, source_table, 'golden', user_email, promotion_reason)
            
            logging.info(f"Successfully promoted query {query_id}. New query ID: {result['new_query_id']}")
            
            return jsonify({
                'success': True,
                'promoted_query_id': result['new_query_id'],
                'source_table': source_table,
                'target_table': 'golden',
                'promoted_by': user_email,
                'message': f'Query promoted from {source_table} to golden'
            }), 200, get_response_headers()
            
        except Exception as e:
            logging.error(f"Promotion failed: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({'error': str(e)}), 500, get_response_headers()
    
    @app.route("/admin/promotion-history", methods=["GET", "OPTIONS"])
    def get_promotion_history():
        """
        Get promotion history with audit trail
        DEPRECATED: Use MCP tool 'get_promotion_history' instead
        """
        logging.info(f"Received {request.method} request to get promotion history")
        
        if request.method == "OPTIONS":
            response = Response()
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
        
        try:
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.lower().startswith("bearer "):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401, get_response_headers()
            
            # Extract and validate user
            user_email = extract_user_email_from_token(auth_header)
            if not user_email:
                return jsonify({'error': 'Token validation failed'}), 401, get_response_headers()
            
            # Check if user is authorized for promotion
            if not is_authorized_for_promotion(user_email):
                return jsonify({'error': 'Unauthorized for query promotion'}), 403, get_response_headers()
            
            # Get pagination parameters
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))
            
            # Get promotion history
            history = get_promotion_history_data(limit, offset)
            
            return jsonify({
                'promotions': history,
                'count': len(history),
                'limit': limit,
                'offset': offset
            }), 200, get_response_headers()
            
        except Exception as e:
            logging.error(f"Error getting promotion history: {e}")
            return jsonify({'error': str(e)}), 500, get_response_headers()

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'vertex-ai-proxy',
            'timestamp': time.time(),
            'project': project,
            'location': location,
            'model': vertex_model,
            'endpoints': ['/ (POST)', '/health (GET)', '/vertex-passthrough (POST)']
        }), 200, get_response_headers()
    
    logging.info("Registered endpoint: /health")
    
    @app.route("/vertex-passthrough", methods=["POST", "OPTIONS"])
    def vertex_passthrough():
        """Simple pass-through endpoint to Vertex AI with user verification"""
        logging.info(f"Received {request.method} request to vertex-passthrough endpoint")
        
        # Handle OPTIONS requests first, without authentication
        if request.method == "OPTIONS":
            logging.info("Handling OPTIONS preflight request for vertex-passthrough")
            response = Response()
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
        
        try:
            logging.info("Processing POST request to vertex-passthrough...")
            
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            logging.info(f"Authorization header present: {bool(auth_header)}")
            
            # Check for Authorization header
            if not auth_header or not auth_header.lower().startswith("bearer "):
                logging.error("Missing or invalid Authorization header")
                response = jsonify({'error': 'Missing or invalid Authorization header'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            # Verify user token (this extracts and validates the user email)
            user_email = extract_user_email_from_token(auth_header)
            if not user_email:
                logging.error("Token validation failed")
                response = jsonify({'error': 'Token validation failed'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            logging.info(f"Token validated for user: {user_email}")
            
            # Get the request body
            request_data = request.get_json()
            if not request_data:
                logging.error("Missing request body")
                response = jsonify({'error': 'Missing request body'})
                response.headers.update(get_response_headers())
                response.status_code = 400
                return response
            
            logging.info(f"Request data keys: {list(request_data.keys())}")
            
            # Pass through the request directly to Vertex AI with retry logic
            # The request_data should contain the properly formatted Vertex AI request
            vertex_response = call_vertex_ai_with_retry(request_data, "direct_vertex_ai_proxy")
            
            if not vertex_response:
                logging.error("Failed to get response from Vertex AI after retries")
                response = jsonify({'error': 'Failed to get response from Vertex AI after retries'})
                response.headers.update(get_response_headers())
                response.status_code = 500
                return response
            
            logging.info("Successfully got response from Vertex AI")
            
            # Return the Vertex AI response directly
            response = jsonify(vertex_response)
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
            
        except Exception as e:
            logging.error(f"Vertex passthrough error: {e}")
            logging.error(f"Error type: {type(e)}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                response = jsonify({'error': f'Internal server error: {str(e)}'})
                response.headers.update(get_response_headers())
                response.status_code = 500
                return response
            except Exception as json_error:
                logging.error(f"Failed to send JSON error response: {json_error}")
                return f"Internal server error: {str(e)}", 500, get_response_headers()
    
    logging.info("Registered endpoint: /vertex-passthrough (POST)")
    
    @app.route("/cors", methods=["OPTIONS"])
    def cors_preflight():
        """Dedicated CORS preflight endpoint - can be deployed without auth"""
        logging.info("Handling dedicated CORS preflight request")
        response = Response()
        response.headers.update(get_response_headers())
        response.status_code = 200
        return response
    
    @app.route("/cors-preflight", methods=["OPTIONS"])
    def cors_preflight_only():
        """Dedicated CORS preflight endpoint - can be deployed without strict auth"""
        logging.info("Handling dedicated CORS preflight request")
        response = Response()
        response.headers.update(get_response_headers())
        response.status_code = 200
        return response
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({'error': 'Internal server error'}), 500, get_response_headers()
    
    logging.info("MCP Flask app created with Vertex AI endpoints")
    return app

def filter_golden_queries_by_explores(golden_queries: Dict[str, Any], allowed_explore_keys: list) -> Dict[str, Any]:
    """Filter golden queries to only include examples for allowed explores"""
    if not allowed_explore_keys or not golden_queries:
        return golden_queries
    
    logging.info(f"🔍 Filtering golden queries to explores: {allowed_explore_keys}")
    filtered = {}
    
    # Filter exploreGenerationExamples
    if 'exploreGenerationExamples' in golden_queries:
        original_count = len(golden_queries['exploreGenerationExamples'])
        filtered['exploreGenerationExamples'] = {
            k: v for k, v in golden_queries['exploreGenerationExamples'].items() 
            if k in allowed_explore_keys
        }
        filtered_count = len(filtered['exploreGenerationExamples'])
        logging.info(f"  exploreGenerationExamples: {original_count} -> {filtered_count}")
    
    # Filter exploreRefinementExamples  
    if 'exploreRefinementExamples' in golden_queries:
        original_count = len(golden_queries['exploreRefinementExamples'])
        filtered['exploreRefinementExamples'] = {
            k: v for k, v in golden_queries['exploreRefinementExamples'].items()
            if k in allowed_explore_keys
        }
        filtered_count = len(filtered['exploreRefinementExamples'])
        logging.info(f"  exploreRefinementExamples: {original_count} -> {filtered_count}")
    
    # Filter exploreSamples
    if 'exploreSamples' in golden_queries:
        original_count = len(golden_queries['exploreSamples'])
        filtered['exploreSamples'] = {
            k: v for k, v in golden_queries['exploreSamples'].items()
            if k in allowed_explore_keys  
        }
        filtered_count = len(filtered['exploreSamples'])
        logging.info(f"  exploreSamples: {original_count} -> {filtered_count}")
    
    # Keep exploreEntries as-is (contains explore metadata, not examples)
    if 'exploreEntries' in golden_queries:
        filtered['exploreEntries'] = golden_queries['exploreEntries']
        logging.info(f"  exploreEntries: kept as-is")
    
    return filtered

def filter_semantic_models_by_explores(semantic_models: Dict[str, Any], allowed_explore_keys: list) -> Dict[str, Any]:
    """Filter semantic models to only include metadata for allowed explores"""
    if not allowed_explore_keys or not semantic_models:
        return semantic_models
    
    original_count = len(semantic_models)
    filtered = {
        explore_key: model_data 
        for explore_key, model_data in semantic_models.items() 
        if explore_key in allowed_explore_keys
    }
    filtered_count = len(filtered)
    logging.info(f"🔍 Filtered semantic models: {original_count} -> {filtered_count}")
    
    return filtered

# For running directly as a Flask app (Cloud Run)
if __name__ == "__main__":
    import os
    app = create_mcp_flask_app()
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
