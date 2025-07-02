# MIT License

# Copyright (c) 2023 Looker Data Sciences, Inc.

# MCP (Model Context Protocol) Server for Looker Explore Assistant
# This server acts as a credential proxy for non-admin users to access
# Vertex AI API by providing secure token exchange.

import os
import time
import json
import uuid
import logging
from typing import Dict, Any, Optional, Tuple
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import functions_framework
import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import looker_sdk
from google.cloud import bigquery
import jwt
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

logging.basicConfig(level=logging.INFO)

# Initialize environment variables
project = os.environ.get("PROJECT")
location = os.environ.get("REGION", "us-central1")
vertex_model = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")
looker_api_client_id = os.environ.get("LOOKER_API_CLIENT_ID")
looker_api_client_secret = os.environ.get("LOOKER_API_CLIENT_SECRET")
looker_base_url = os.environ.get("LOOKER_BASE_URL")

# BigQuery configuration for suggested golden queries
bq_project_id = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
bq_dataset_id = os.environ.get("BQ_DATASET_ID", "explore_assistant")
bq_suggested_table = os.environ.get("BQ_SUGGESTED_TABLE", "suggested_golden_queries")
looker_base_url = os.environ.get("LOOKER_BASE_URL")

def get_response_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "3600",
        "Access-Control-Allow-Credentials": "false"
    }

def validate_oauth_token(bearer_token: str) -> Optional[Dict[str, Any]]:
    """Validate OAuth token using GCP token_info endpoint"""
    try:
        logging.info("Starting OAuth token validation")
        
        # Remove 'Bearer ' prefix if present
        if bearer_token.startswith('Bearer '):
            bearer_token = bearer_token[7:]
        
        logging.info(f"Token length: {len(bearer_token)}")
        
        # Call Google's token info endpoint
        token_info_url = f"https://oauth2.googleapis.com/tokeninfo?access_token={bearer_token}"
        logging.info("Calling Google token info endpoint")
        
        response = requests.get(token_info_url, timeout=10)
        
        logging.info(f"Token validation status: {response.status_code}")

        if not response.ok:
            logging.error(f"Token validation failed: {response.status_code} - {response.text}")
            return None
        
        token_info = response.json()
        logging.info(f"Token info received: {list(token_info.keys())}")
        
        # Check if token has required scopes
        scopes = token_info.get('scope', '').split()
        logging.info(f"Token scopes: {scopes}")
        
        # Check for required scopes
        required_scopes = [
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/userinfo.email'
        ]
        
        missing_scopes = []
        for required_scope in required_scopes:
            if required_scope not in scopes:
                missing_scopes.append(required_scope)
        
        if missing_scopes:
            logging.error(f"Token missing required scopes: {missing_scopes}")
            logging.error(f"Available scopes: {scopes}")
            return None

        # Extract user information
        email = token_info.get('email')
        if not email:
            logging.error("No email found in token info")
            logging.error(f"Available token fields: {list(token_info.keys())}")
            return None

        logging.info(f"Token validated for user: {email}")
        return {
            'email': email,
            'user_id': token_info.get('sub'),
            'expires_in': token_info.get('expires_in', 0)
        }
        
    except Exception as e:
        logging.error(f"Error validating OAuth token: {e}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
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
        
        response = requests.post(vertex_api_url, headers=headers, json=request_body)
        
        if not response.ok:
            logging.error(f"Vertex AI API call failed: {response.status_code} - {response.text}")
            return None
        
        logging.info("Vertex AI API call successful")
        return response.json()
        
    except Exception as e:
        logging.error(f"Error calling Vertex AI API: {e}")
        return None

def get_looker_sdk():
    """Initialize and return Looker SDK instance"""
    try:
        # Configure Looker SDK settings
        config = {
            'base_url': looker_base_url,
            'client_id': looker_api_client_id,
            'client_secret': looker_api_client_secret,
            'verify_ssl': True
        }
        
        # Initialize SDK
        sdk = looker_sdk.init40(**config)
        logging.info("Looker SDK initialized successfully")
        return sdk
        
    except Exception as e:
        logging.error(f"Error initializing Looker SDK: {e}")
        return None

def find_looker_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Find Looker user by email address using Looker SDK"""
    try:
        # Initialize Looker SDK
        sdk = get_looker_sdk()
        if not sdk:
            logging.error("Failed to initialize Looker SDK")
            return None
        
        # Search for user by email using SDK
        users = sdk.search_users(email=email)
        
        if not users:
            logging.error(f"No Looker user found with email: {email}")
            return None
        
        # Convert the first user object to dict
        user = users[0]
        user_dict = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_disabled': user.is_disabled,
            'role_ids': user.role_ids
        }
        
        logging.info(f"Found Looker user: {user_dict['id']} - {user_dict['email']}")
        return user_dict
        
    except Exception as e:
        logging.error(f"Error finding Looker user: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def extract_vertex_response_text(vertex_response: Dict[str, Any]) -> Optional[str]:
    """Extract text from Vertex AI response"""
    try:
        candidates = vertex_response.get('candidates', [])
        if candidates:
            content = candidates[0].get('content', {})
            parts = content.get('parts', [])
            if parts:
                return parts[0].get('text', '')
        return None
    except Exception as e:
        logging.error(f"Error extracting Vertex AI response: {e}")
        return None

def determine_explore_from_prompt(oauth_token: str, prompt: str, golden_queries: Dict[str, Any], 
                                 conversation_context: str = "") -> Optional[str]:
    """Enhanced explore determination with conversation context"""
    try:
        # Build system prompt with conversation context
        newline_char = "\n"
        system_prompt = f"""You are a Looker Explore Assistant. Your job is to determine which Looker explore is most appropriate for answering a user's question.

Available Explores and Examples:
{json.dumps(golden_queries, indent=2)}

{f"Conversation Context:{newline_char}{conversation_context}{newline_char}" if conversation_context else ""}

Instructions:
1. Analyze the user's current prompt: "{prompt}"
2. Consider the conversation context to understand what the user has been asking about
3. Compare against all available explores and their examples
4. Determine which explore would be best suited to answer this question
5. Return ONLY the explore key (e.g., "order_items", "events", etc.) as a single string

Current user prompt: {prompt}

Response format: Return only the explore key as plain text (no JSON, no explanation)"""

        # Format request for Vertex AI
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 100
            }
        }
        
        # Call Vertex AI using service account
        vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
        if not vertex_response:
            return None
        
        # Extract the explore key from response
        response_text = extract_vertex_response_text(vertex_response)
        if response_text:
            # Clean up the response - remove any extra whitespace or formatting
            explore_key = response_text.strip().replace('"', '').replace('\n', '')
            logging.info(f"Determined explore with context: {explore_key}")
            return explore_key
        
        return None
        
    except Exception as e:
        logging.error(f"Error determining explore: {e}")
        return None

def generate_explore_params(oauth_token: str, prompt: str, explore_key: str, 
                          golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                          current_explore: Dict[str, Any], conversation_context: str = "") -> Optional[Dict[str, Any]]:
    """Enhanced parameter generation with two-step LLM approach for better conversation context handling"""
    try:
        logging.info(f"=== GENERATE_EXPLORE_PARAMS START ===")
        logging.info(f"Original prompt: {prompt}")
        logging.info(f"Has conversation context: {bool(conversation_context)}")
        
        # Step 1: Synthesize conversation context into a clear, standalone query
        synthesized_query = synthesize_conversation_context(oauth_token, prompt, conversation_context)
        if not synthesized_query:
            logging.warning("❌ SYNTHESIS FAILED - Using original prompt")
            synthesized_query = prompt
        else:
            logging.info(f"✅ SYNTHESIS SUCCESS - Original: '{prompt}' -> Synthesized: '{synthesized_query}'")
        
        logging.info(f"Using query for explore params: {synthesized_query}")
        
        # Step 2: Generate explore parameters using the synthesized query
        result = generate_explore_params_from_query(oauth_token, synthesized_query, explore_key, 
                                                golden_queries, semantic_models, current_explore)
        
        logging.info(f"=== GENERATE_EXPLORE_PARAMS RESULT ===")
        if result:
            logging.info(f"Result keys: {list(result.keys())}")
            if 'explore_params' in result:
                logging.info(f"Explore params fields: {result['explore_params'].get('fields', [])}")
        else:
            logging.warning("No result from generate_explore_params_from_query")
            
        return result
        
    except Exception as e:
        logging.error(f"Error in generate_explore_params: {e}")
        return None

def synthesize_conversation_context(oauth_token: str, current_prompt: str, conversation_context: str) -> Optional[str]:
    """First LLM call: Synthesize conversation history and current prompt into a clear, standalone query"""
    try:
        logging.info(f"=== SYNTHESIS STEP ===")
        logging.info(f"Current prompt: {current_prompt}")
        logging.info(f"Conversation context: {conversation_context}")
        
        # If there's no conversation context, just return the original prompt
        if not conversation_context or conversation_context.strip() == "":
            logging.info("No conversation context, returning original prompt")
            return current_prompt
            
        synthesis_prompt = f"""You are an expert at understanding user conversations about data analysis. Your task is to synthesize a conversation history and the current user prompt into a single, clear, comprehensive query that captures the user's complete intent.

CONVERSATION HISTORY:
{conversation_context}

CURRENT USER PROMPT:
{current_prompt}

Your task:
1. Analyze the conversation history to understand what the user has been working on
2. Interpret the current prompt in the context of the conversation
3. Combine them into a single, clear, standalone query that fully captures what the user wants

Rules:
- If the current prompt is a refinement (like "use a table", "make it a chart", "show top 10"), incorporate the context from previous queries
- The output should be a complete, standalone question that someone could understand without seeing the conversation history
- Focus on the data analysis intent, not the visualization preferences
- Be specific about what data fields, time periods, filters, etc. the user wants

Output only the synthesized query, nothing else."""

        # Format request for Vertex AI
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
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 512,
                "responseMimeType": "text/plain"
            }
        }
        
        # Call Vertex AI using service account
        vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
        if not vertex_response:
            return None
        
        # Extract the synthesized query
        synthesized_query = extract_vertex_response_text(vertex_response)
        if synthesized_query:
            synthesized_query = synthesized_query.strip()
            logging.info(f"=== SYNTHESIS RESULT ===")
            logging.info(f"Synthesized query: {synthesized_query}")
            return synthesized_query
        
        logging.warning("Failed to extract synthesized query from Vertex AI response")
        return None
        
    except Exception as e:
        logging.error(f"Error synthesizing conversation context: {e}")
        return None

def generate_explore_params_from_query(oauth_token: str, query: str, explore_key: str, 
                                     golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                                     current_explore: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Second LLM call: Generate explore parameters from a clear, synthesized query"""
    try:
        # Get relevant golden queries for this specific explore
        relevant_examples = {}
        if 'exploreEntries' in golden_queries and explore_key in golden_queries['exploreEntries']:
            relevant_examples['exploreEntries'] = {explore_key: golden_queries['exploreEntries'][explore_key]}
        
        if 'exploreGenerationExamples' in golden_queries and explore_key in golden_queries['exploreGenerationExamples']:
            relevant_examples['exploreGenerationExamples'] = {explore_key: golden_queries['exploreGenerationExamples'][explore_key]}
        
        if 'exploreRefinementExamples' in golden_queries and explore_key in golden_queries['exploreRefinementExamples']:
            relevant_examples['exploreRefinementExamples'] = {explore_key: golden_queries['exploreRefinementExamples'][explore_key]}
        
        if 'exploreSamples' in golden_queries and explore_key in golden_queries['exploreSamples']:
            relevant_examples['exploreSamples'] = {explore_key: golden_queries['exploreSamples'][explore_key]}
        
        # Get semantic model for this explore
        explore_semantic_model = semantic_models.get(explore_key, {})
        
        # Format table context for this explore
        dimensions = explore_semantic_model.get('dimensions', [])
        measures = explore_semantic_model.get('measures', [])
        
        def format_row(field):
            name = field.get('name', '')
            type_val = field.get('type', '')
            label = field.get('label', '')
            description = field.get('description', '')
            tags = ', '.join(field.get('tags', []))
            return f"| {name} | {type_val} | {label} | {description} | {tags} |"

        table_context = f"""
# Looker Explore Metadata
Explore: {explore_key}

## Dimensions (for grouping data):
| Field Id | Field Type | Label | Description | Tags |
|----------|------------|-------|-------------|------|
{chr(10).join([format_row(dim) for dim in dimensions])}

## Measures (for calculations):
| Field Id | Field Type | Label | Description | Tags |
|----------|------------|-------|-------------|------|
{chr(10).join([format_row(measure) for measure in measures])}
"""

        # Build system prompt for explore parameter generation
        system_prompt = f"""You are a Looker Explore Assistant. Generate Looker explore parameters based on the user's natural language question.

{table_context}

Relevant Examples for this explore:
{json.dumps(relevant_examples, indent=2)}

Instructions:
1. Analyze the user's query: "{query}"
2. Generate appropriate Looker query parameters using the available fields
3. Return a JSON object with the following structure:

{{
  "explore_key": "{explore_key}",
  "explore_params": {{
    "fields": ["field1", "field2"],
    "filters": {{}},
    "sorts": ["field1"],
    "limit": "500",
    "vis_config": {{
      "type": "table"
    }}
  }},
  "message_type": "explore",
  "summary": "Description of what this explore shows"
}}

VALID VIS_CONFIG TYPES:
- Single Number: single_value
- Tables: table, looker_grid, looker_single_record
- Charts: looker_column, looker_bar, looker_scatter, looker_line, looker_area, looker_pie, looker_donut_multiples, looker_funnel, looker_timeline, looker_waterfall, looker_boxplot
- Maps: looker_map, looker_google_map, looker_geo_coordinates, looker_geo_choropleth

IMPORTANT: 
- Always include relevant fields that answer the user's question
- For table requests, use "table" or "looker_grid" as the vis_config type
- For chart requests, choose the most appropriate chart type from the valid options above
- For geographic data, use appropriate map visualizations
- The query has already been processed to be clear and standalone

User query: "{query}"
"""

        # Format request for Vertex AI
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
                "temperature": 0.1,
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }
        
        # Call Vertex AI using service account
        vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
        if not vertex_response:
            return None
        
        # Extract and parse the JSON response
        response_text = extract_vertex_response_text(vertex_response)
        if response_text:
            try:
                result = json.loads(response_text)
                logging.info(f"Generated explore params for {explore_key} from synthesized query")
                logging.info(f"Response structure: {list(result.keys())}")
                
                # Ensure the response has the expected structure
                if 'explore_params' not in result:
                    # If the AI returned explore parameters directly, wrap them
                    if 'fields' in result or 'filters' in result:
                        result = {
                            "explore_key": explore_key,
                            "explore_params": result,
                            "message_type": "explore",
                            "summary": f"Generated query for: {query}"
                        }
                    else:
                        # Create a minimal response with context understanding
                        logging.warning(f"Unexpected response structure, creating fallback")
                        result = create_context_aware_fallback(query, explore_key, "", semantic_models)
                
                # Check if explore_params is empty and use fallback if needed
                explore_params = result.get('explore_params', {})
                if not explore_params or not explore_params.get('fields'):
                    logging.warning(f"Empty explore_params detected, using context-aware fallback")
                    logging.info(f"Original response: {result}")
                    fallback_result = create_context_aware_fallback(query, explore_key, "", semantic_models)
                    # Preserve the original summary if it exists and is meaningful
                    if result.get('summary') and 'unable' not in result.get('summary', '').lower():
                        fallback_result['summary'] = result.get('summary')
                    result = fallback_result
                
                return result
                
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Raw response: {response_text}")
                # Create a context-aware fallback response
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

def process_explore_assistant_request(oauth_token: str, request_data: Dict[str, Any], user_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """Process the explore assistant request with conversation context"""
    try:
        logging.info("Starting process_explore_assistant_request")
        
        # Extract conversation data from the request
        prompt = request_data.get('prompt', '')
        conversation_id = request_data.get('conversation_id', '')
        prompt_history = request_data.get('prompt_history', [])
        current_explore = request_data.get('current_explore', {})
        golden_queries = request_data.get('golden_queries', {})
        semantic_models = request_data.get('semantic_models', {})
        model_name = request_data.get('model_name', '')
        data_to_summarize = request_data.get('data_to_summarize', '')
        test_mode = request_data.get('test_mode', False)
        
        # NEW: Handle conversation context
        thread_messages = request_data.get('thread_messages', [])
        
        logging.info(f"Conversation ID: {conversation_id}")
        logging.info(f"Prompt history length: {len(prompt_history)}")
        logging.info(f"Thread messages length: {len(thread_messages)}")
        
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
        
        # Check if current explore is null/empty
        current_explore_key = current_explore.get('exploreKey') if current_explore else None
        
        if not current_explore_key or current_explore_key == '' or current_explore_key == 'null':
            # Two-step process with conversation context
            determined_explore_key = determine_explore_from_prompt(
                oauth_token, prompt, golden_queries, conversation_context
            )
            
            if not determined_explore_key:
                return {
                    'error': 'Failed to determine appropriate explore',
                    'message_type': 'error'
                }
            
            current_explore = {
                'exploreKey': determined_explore_key,
                'exploreId': determined_explore_key,
                'modelName': model_name
            }
            
            result = generate_explore_params(
                oauth_token, prompt, determined_explore_key, 
                golden_queries, semantic_models, current_explore, conversation_context
            )
        else:
            # Single call with conversation context
            result = generate_explore_params(
                oauth_token, prompt, current_explore_key, 
                golden_queries, semantic_models, current_explore, conversation_context
            )
        
        if not result:
            return {
                'error': 'Failed to generate explore parameters',
                'message_type': 'error'
            }
        
        # Add conversation tracking to response
        result['conversation_id'] = conversation_id
        result['prompt_added_to_history'] = prompt
        
        # Check for feedback pattern and save suggested golden query if detected
        has_feedback, approved_explore_params = detect_feedback_pattern(prompt_history, thread_messages, prompt)
        if has_feedback and approved_explore_params:
            # Extract user email from user_info
            user_email = user_info.get('email', 'anonymous') if user_info else 'anonymous'
            
            # Save the suggested golden query with the APPROVED explore_params (not the current confirmation params)
            save_success = save_suggested_golden_query(
                oauth_token, 
                result.get('explore_key', ''), 
                prompt_history,  # Pass entire prompt history instead of just original prompt
                approved_explore_params,  # Use the approved params, not the current result params
                user_email
            )
            
            if save_success:
                # Add feedback message to response (but don't change the main result)
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

def save_suggested_golden_query(oauth_token: str, explore_key: str, prompt_history: list, 
                               explore_params: Dict[str, Any], user_email: str) -> bool:
    """
    Save a suggested golden query to the BigQuery suggested_golden_queries table
    Now stores the complete prompt history for better context
    """
    try:
        # Create BigQuery client using default credentials (Cloud Run service account)
        client = bigquery.Client(project=bq_project_id)
        
        # Prepare the record to insert
        current_time = time.time()
        suggested_query = {
            'explore_key': explore_key,
            'prompt': json.dumps(prompt_history),  # Store complete prompt history as JSON string
            'explore_params': json.dumps(explore_params),  # Store as JSON string
            'user_id': user_email,
            'timestamp': current_time,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(current_time)),
            'approved': False,  
            'feedback_type': 'user_correction',
            'id': str(uuid.uuid4()),  # Generate UUID for the id field
            'created_date': time.strftime('%Y-%m-%d', time.gmtime(current_time))  # Date for partitioning
        }
        
        logging.info(f"Saving suggested golden query to BigQuery: {explore_key} for user {user_email}")
        
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
            'explore_key': explore_key,
            'prompt_history': prompt_history,  # Use prompt_history instead of original_prompt
            'explore_params': explore_params,
            'user_id': user_email,
            'timestamp': time.time(),
            'feedback_type': 'user_correction'
        }
        logging.info(f"FALLBACK LOG - Suggested query data: {json.dumps(fallback_data, indent=2)}")
        return False

def validate_identity_token(bearer_token: str) -> Optional[Dict[str, Any]]:
    """Validate Google Identity token (JWT)"""
    try:
        logging.info("Starting Identity token validation")
        
        # Remove 'Bearer ' prefix if present
        if bearer_token.startswith('Bearer '):
            bearer_token = bearer_token[7:]
        
        logging.info(f"Identity token length: {len(bearer_token)}")
        
        # Verify the token using Google's library
        # This validates the signature, expiration, and issuer
        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(bearer_token, request)
        
        logging.info(f"Identity token info received: {list(id_info.keys())}")
        
        # Extract user information from the JWT payload
        email = id_info.get('email')
        if not email:
            logging.error("No email found in identity token")
            logging.error(f"Available token fields: {list(id_info.keys())}")
            return None

        logging.info(f"Identity token validated for user: {email}")
        return {
            'email': email,
            'user_id': id_info.get('sub'),
            'expires_at': id_info.get('exp', 0),
            'audience': id_info.get('aud'),
            'token_type': 'identity'
        }
        
    except ValueError as e:
        logging.error(f"Identity token validation failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Error validating identity token: {e}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None

def validate_token(bearer_token: str) -> Optional[Dict[str, Any]]:
    """Validate either OAuth access token or Identity token"""
    if not bearer_token:
        return None
    
    # Remove 'Bearer ' prefix if present
    clean_token = bearer_token[7:] if bearer_token.startswith('Bearer ') else bearer_token
    
    # Try to determine token type by structure
    # JWT tokens have 3 parts separated by dots
    if clean_token.count('.') == 2:
        logging.info("Token appears to be a JWT (Identity token), trying identity validation first")
        result = validate_identity_token(bearer_token)
        if result:
            return result
        logging.info("Identity token validation failed, trying as access token")
    
    # Try as access token
    logging.info("Trying OAuth access token validation")
    return validate_oauth_token(bearer_token)

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
            
            if not auth_header or not auth_header.startswith("Bearer "):
                logging.error("Missing or invalid Authorization header")
                response = jsonify({'error': 'Missing or invalid Authorization header'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            logging.info("Validating OAuth/Identity token...")
            # Validate OAuth token or Identity token
            oauth_token_info = validate_token(auth_header)
            if not oauth_token_info:
                logging.error("Token validation failed")
                return jsonify({'error': 'Invalid token'}), 401, get_response_headers()
            
            token_type = oauth_token_info.get('token_type', 'access')
            logging.info(f"{token_type.capitalize()} token validated for user: {oauth_token_info.get('email')}")
            
            # Get the request body
            logging.info("Getting request body...")
            request_data = request.get_json()
            if not request_data:
                logging.error("Missing request body")
                return jsonify({'error': 'Missing request body'}), 400, get_response_headers()
            
            logging.info(f"Request data keys: {list(request_data.keys())}")
            logging.info(f"Test mode: {request_data.get('test_mode', False)}")
            
            # Process the explore assistant request
            logging.info("Processing explore assistant request...")
            result = process_explore_assistant_request(auth_header, request_data, oauth_token_info)
            
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
            'endpoints': ['/ (POST)', '/health (GET)']
        }), 200, get_response_headers()
    
    logging.info("Registered endpoint: /health")
    
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

@functions_framework.http
def mcp_cloud_function_entrypoint(request):
    """Cloud Function entry point for MCP server"""
    
    # Handle OPTIONS requests first, without authentication
    if request.method == "OPTIONS":
        logging.info("Handling OPTIONS preflight request")
        response = Response()
        response.headers.update(get_response_headers())
        response.status_code = 200
        return response
    
    path = request.path
    
    if path == "/" or path == "":
        try:
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                logging.error("Missing or invalid Authorization header")
                response = jsonify({'error': 'Missing or invalid Authorization header'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            # Validate OAuth token or Identity token
            oauth_token_info = validate_token(auth_header)
            if not oauth_token_info:
                logging.error("Token validation failed")
                response = jsonify({'error': 'Invalid token'})
                response.headers.update(get_response_headers())
                response.status_code = 401
                return response
            
            # Get the request body
            request_data = request.get_json()
            if not request_data:
                logging.error("Missing request body")
                response = jsonify({'error': 'Missing request body'})
                response.headers.update(get_response_headers())
                response.status_code = 400
                return response
            
            # Process the explore assistant request
            result = process_explore_assistant_request(auth_header, request_data, oauth_token_info)
            
            response = jsonify(result)
            response.headers.update(get_response_headers())
            response.status_code = 200
            return response
            
        except Exception as e:
            logging.error(f"Vertex AI proxy error: {e}")
            response = jsonify({'error': f'Internal server error: {str(e)}'})
            response.headers.update(get_response_headers())
            response.status_code = 500
            return response
    
    elif path == "/health":
        response = jsonify({
            'status': 'healthy',
            'service': 'vertex-ai-proxy',
            'timestamp': time.time(),
            'project': project,
            'location': location,
            'model': vertex_model,
            'endpoints': ['/ (POST)', '/health (GET)']
        })
        response.headers.update(get_response_headers())
        return response
    
    else:
        response = jsonify({'error': 'Endpoint not found'})
        response.headers.update(get_response_headers())
        response.status_code = 404
        return response
