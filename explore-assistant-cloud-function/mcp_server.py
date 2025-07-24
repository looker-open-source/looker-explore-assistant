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
import traceback
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
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

# Initialize environment variables
project = os.environ.get("PROJECT")
location = os.environ.get("REGION", "us-central1")
vertex_model = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")

# BigQuery configuration for suggested golden queries
bq_project_id = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
bq_dataset_id = os.environ.get("BQ_DATASET_ID", "explore_assistant")
bq_suggested_table = os.environ.get("BQ_SUGGESTED_TABLE", "silver_queries")

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
        
        # Remove 'Bearer ' prefix if present
        if bearer_token.lower().startswith('bearer '):
            bearer_token = bearer_token[7:]
        
        # Remove any whitespace
        bearer_token = bearer_token.strip()
        
        # Split JWT into parts
        token_parts = bearer_token.split('.')
        if len(token_parts) != 3:
            logging.error(f"Invalid JWT format: expected 3 parts, got {len(token_parts)}")
            return None
        
        # Decode the payload (second part) to extract email
        import base64
        import json
        
        payload_data = token_parts[1]
        # Add padding if needed for base64 decoding
        payload_data += '=' * (4 - len(payload_data) % 4)
        
        try:
            payload_json = base64.urlsafe_b64decode(payload_data).decode('utf-8')
            payload = json.loads(payload_json)
            
            email = payload.get('email')
            if email:
                logging.info(f"Extracted user email: {email}")
                return email
            else:
                logging.error("No email found in token payload")
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

def determine_explore_from_prompt(auth_header: str, prompt: str, golden_queries: Dict[str, Any], 
                                 conversation_context: str = "", restricted_explore_keys: list = None) -> Optional[str]:
    """
    Enhanced explore determination with conversation context and area restrictions.
    Always determines the best explore based on the prompt and conversation context,
    but restricts selection to specified explore keys if provided.
    """
    try:
        logging.info("=== EXPLORE DETERMINATION START ===")
        logging.info(f"Determining best explore for prompt: {prompt}")
        logging.info(f"Has conversation context: {bool(conversation_context)}")
        logging.info(f"Restricted explore keys: {restricted_explore_keys}")
        
        # Filter golden queries by restricted explore keys if provided
        filtered_golden_queries = golden_queries
        if restricted_explore_keys:
            filtered_golden_queries = {}
            for key, value in golden_queries.items():
                if key == 'exploreEntries':
                    # Filter explore entries by restricted keys
                    filtered_entries = [
                        entry for entry in value 
                        if entry.get('golden_queries.explore_id') in restricted_explore_keys
                    ]
                    filtered_golden_queries[key] = filtered_entries
                else:
                    # For other keys, filter based on explore keys
                    if isinstance(value, dict):
                        filtered_value = {
                            k: v for k, v in value.items() 
                            if k in restricted_explore_keys
                        }
                        filtered_golden_queries[key] = filtered_value
                    else:
                        filtered_golden_queries[key] = value
        
        # Build system prompt with conversation context
        newline_char = "\n"
        restriction_text = ""
        if restricted_explore_keys:
            restriction_text = f"{newline_char}IMPORTANT: You must only select explores from this restricted list: {restricted_explore_keys}{newline_char}"
        
        system_prompt = f"""You are a Looker Explore Assistant. Your job is to determine which Looker explore is most appropriate for answering a user's question.

IMPORTANT: You must analyze the user's question independently and select the BEST explore for their needs, regardless of any previous explore selections or model information.
{restriction_text}
Available Explores and Examples:
{json.dumps(filtered_golden_queries, indent=2)}

{f"Conversation Context:{newline_char}{conversation_context}{newline_char}" if conversation_context else ""}

Instructions:
1. Analyze the user's current prompt: "{prompt}"
2. Consider the conversation context to understand what the user has been asking about
3. Compare against ALL available explores and their examples
4. Determine which explore would be BEST suited to answer this question
5. {"Restrict your selection to the provided explore keys only" if restricted_explore_keys else "Ignore any previous explore selections - choose the optimal explore for this specific question"}
6. Return ONLY the explore key (e.g., "order_items", "events", etc.) as a single string

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
            logging.error("❌ Failed to get response from Vertex AI")
            return None
        
        # Extract the explore key from response
        response_text = extract_vertex_response_text(vertex_response)
        if response_text:
            # Clean up the response - remove any extra whitespace or formatting
            explore_key = response_text.strip().replace('"', '').replace('\n', '')
            
            # Validate that the determined explore is in the restricted list if restrictions apply
            if restricted_explore_keys and explore_key not in restricted_explore_keys:
                logging.warning(f"Determined explore '{explore_key}' not in restricted list. Selecting first available.")
                explore_key = restricted_explore_keys[0] if restricted_explore_keys else explore_key
            
            logging.info(f"✅ Determined explore with context: {explore_key}")
            logging.info("=== EXPLORE DETERMINATION COMPLETE ===")
            return explore_key
        
        logging.error("❌ Failed to extract explore key from response")
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
        
        # Step 1: Synthesize conversation context into a clear, standalone query
        synthesized_query = synthesize_conversation_context(auth_header, prompt, conversation_context)
        if not synthesized_query:
            logging.warning("❌ SYNTHESIS FAILED - Using original prompt")
            synthesized_query = prompt
        else:
            logging.info(f"✅ SYNTHESIS SUCCESS - Original: '{prompt}' -> Synthesized: '{synthesized_query}'")
        
        logging.info(f"Using query for explore params: {synthesized_query}")
        
        # Step 2: Generate explore parameters using the synthesized query
        result = generate_explore_params_from_query(auth_header, synthesized_query, explore_key, 
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

def generate_explore_params_from_query(auth_header: str, query: str, explore_key: str, 
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
        explore_description = explore_semantic_model.get('description', '')
        
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
{f"Additional instructions: {explore_description}" if explore_description else ""}

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
        logging.info("Always determining explore from prompt and conversation context")
        determined_explore_key = determine_explore_from_prompt(
            auth_header, prompt, golden_queries, conversation_context, restricted_explore_keys
        )
        
        if not determined_explore_key:
            # If AI couldn't determine explore, try to use first available explore as fallback
            if golden_queries.get('exploreEntries'):
                first_explore = list(golden_queries['exploreEntries'].keys())[0]
                logging.warning(f"Failed to determine explore, using first available: {first_explore}")
                determined_explore_key = first_explore
            else:
                return {
                    'error': 'Failed to determine appropriate explore and no fallback available',
                    'message_type': 'error'
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
        
        # Generate explore parameters using the determined explore
        result = generate_explore_params(
            auth_header, prompt, determined_explore_key, 
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
            # Save the suggested golden query with the APPROVED explore_params
            save_success = save_suggested_silver_query(
                auth_header, 
                result.get('explore_key', ''), 
                prompt_history,  # Pass entire prompt history
                approved_explore_params,  # Use the approved params
                user_email
            )
            
            if save_success:
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
                "topP": 0.8,
                "topK": 40,
                "maxOutputTokens": 256,
                "responseMimeType": "text/plain"
            }
        }
        
        # Call Vertex AI using service account
        vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
        if not vertex_response:
            logging.error("Failed to get response from Vertex AI for suggested prompt")
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
            'created_date': time.strftime('%Y-%m-%d', time.gmtime(current_time)),  # Date for partitioning
            'suggested_new_prompt': suggested_prompt  # New field with LLM-generated suggested prompt
        }
        
        logging.info(f"Saving suggested golden query to BigQuery: {explore_key} for user {user_email}")
        logging.info(f"Generated suggested prompt: {suggested_prompt}")
        
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
            'feedback_type': 'user_correction',
            'suggested_new_prompt': suggested_prompt if 'suggested_prompt' in locals() else 'Not generated'
        }
        logging.info(f"FALLBACK LOG - Suggested query data: {json.dumps(fallback_data, indent=2)}")
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
            
            # Pass through the request directly to Vertex AI
            # The request_data should contain the properly formatted Vertex AI request
            vertex_response = call_vertex_ai_api_with_service_account(request_data)
            
            if not vertex_response:
                logging.error("Failed to get response from Vertex AI")
                response = jsonify({'error': 'Failed to get response from Vertex AI'})
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

def ensure_bronze_queries_table_exists():
    """
    Create the bronze_queries table if it doesn't exist, or update schema if needed
    """
    try:
        client = bigquery.Client()
        bronze_table_id = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
        
        # Check if table exists
        try:
            table = client.get_table(bronze_table_id)
            logging.info(f"Bronze queries table {bronze_table_id} already exists")
            
            # Check if the new fields exist, add them if they don't
            existing_field_names = {field.name for field in table.schema}
            required_fields = {
                'explore_params': bigquery.SchemaField("explore_params", "STRING", mode="NULLABLE"),
                'query_url_params': bigquery.SchemaField("query_url_params", "STRING", mode="NULLABLE")
            }
            
            fields_to_add = []
            for field_name, field_schema in required_fields.items():
                if field_name not in existing_field_names:
                    fields_to_add.append(field_schema)
                    logging.info(f"Need to add field: {field_name}")
            
            if fields_to_add:
                logging.info(f"Adding {len(fields_to_add)} missing fields to bronze queries table")
                # Create new schema with existing fields plus new fields
                new_schema = list(table.schema) + fields_to_add
                table.schema = new_schema
                table = client.update_table(table, ["schema"])
                logging.info(f"Successfully updated bronze queries table schema")
            
            return True
            
        except Exception as table_error:
            logging.info(f"Bronze queries table {bronze_table_id} does not exist, creating it: {table_error}")
        
        # Define the complete table schema for new table creation
        schema = [
            bigquery.SchemaField("explore_key", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("model_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("input_question", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("output_description", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("explore_params", "STRING", mode="NULLABLE"),  # Store query parameters as JSON
            bigquery.SchemaField("query_url_params", "STRING", mode="NULLABLE"),  # Store URL parameters
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("source", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_email", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("query_run_count", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("original_query_url", "STRING", mode="NULLABLE")
        ]
        
        # Create table reference
        table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table("bronze_queries")
        table = bigquery.Table(table_ref, schema=schema)
        
        # Set table description
        table.description = "Bronze queries generated from historical Looker query patterns for explore assistant training"
        
        # Create the table
        table = client.create_table(table)
        logging.info(f"Successfully created bronze queries table: {bronze_table_id}")
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to create bronze queries table: {e}")
        raise Exception(f"Failed to create bronze queries table: {e}")

def ensure_silver_queries_table_exists():
    """
    Create the silver_queries table if it doesn't exist, or update schema if needed.
    """
    try:
        client = bigquery.Client(project=bq_project_id)
        silver_table_id = f"{bq_project_id}.{bq_dataset_id}.{bq_suggested_table}"

        # Check if table exists
        try:
            table = client.get_table(silver_table_id)
            logging.info(f"Silver queries table {silver_table_id} already exists")
            
            # Check if the new suggested_new_prompt field exists, add it if it doesn't
            existing_field_names = {field.name for field in table.schema}
            if 'suggested_new_prompt' not in existing_field_names:
                logging.info("Adding suggested_new_prompt field to existing silver queries table")
                new_field = bigquery.SchemaField("suggested_new_prompt", "STRING", mode="NULLABLE")
                table.schema = table.schema + [new_field]
                table = client.update_table(table, ["schema"])
                logging.info("Successfully added suggested_new_prompt field to silver queries table")
            
            return True
        except Exception as table_error:
            logging.info(f"Silver queries table {silver_table_id} does not exist, creating it: {table_error}")

        # Define the table schema (including the new suggested_new_prompt field)
        schema = [
            bigquery.SchemaField("explore_key", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("prompt", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_params", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("timestamp", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("created_at", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("approved", "BOOLEAN", mode="NULLABLE"),
            bigquery.SchemaField("feedback_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_date", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("suggested_new_prompt", "STRING", mode="NULLABLE"),
        ]

        # Create table reference
        table_ref = client.dataset(bq_dataset_id, project=bq_project_id).table(bq_suggested_table)
        table = bigquery.Table(table_ref, schema=schema)
        table.description = "Suggested golden queries for Looker Explore Assistant"

        # Create the table
        table = client.create_table(table)
        logging.info(f"Successfully created silver queries table: {silver_table_id}")
        return True

    except Exception as e:
        logging.error(f"Failed to create silver queries table: {e}")
        raise Exception(f"Failed to create silver queries table: {e}")

def generate_bronze_queries_for_explore(model_name: str, explore_name: str, explore_key: str, user_email: str = None) -> Dict[str, Any]:
    """
    Generate bronze queries for a specific explore by analyzing recent query history
    and using Vertex AI to create natural language descriptions.
    """
    try:
        # Ensure the bronze queries table exists
        ensure_bronze_queries_table_exists()
        
        # Initialize Looker SDK
        looker_sdk = get_looker_sdk()
        if not looker_sdk:
            raise Exception("Failed to initialize Looker SDK")
        
        logging.info(f"Generating bronze queries for explore: {explore_key}")
        
        # Fetch recent query history for this explore (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Query Looker's query history using the system activity explore
        # This replicates the logic from generate_examples.py
        history_queries = []
        
        try:
            # Use Looker API to get query history for this specific explore
            query_params = {
                'model': 'system__activity',
                'explore': 'history',
                'view': 'history',  # Add the required view field
                'fields': ['history.query_run_count', 'query.model', 'query.view', 'query.formatted_fields', 'query.formatted_filters', 'query.formatted_pivots', 'query.sorts', 'query.limit', 'query.share_url'],
                'filters': {
                    'history.created_date': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'query.model': model_name,
                    'query.view': explore_name
                },
                'sorts': ['history.query_run_count desc'],
                'limit': 50  # Get top 50 most-run queries
            }
            
            # Create and run the query
            query_response = looker_sdk.create_query(query_params)
            if query_response and query_response.id:
                results = looker_sdk.run_query(query_response.id, 'json')
                if results:
                    history_queries = json.loads(results)
                    
        except Exception as e:
            logging.warning(f"Could not fetch query history: {e}")
            # If we can't get history, check if the explore exists at least
            try:
                explore_info = looker_sdk.lookml_model_explore(model_name, explore_name)
                if not explore_info:
                    raise Exception(f"Explore {model_name}:{explore_name} not found")
            except Exception as explore_error:
                raise Exception(f"Explore validation failed: {explore_error}")
            
            # If explore exists but no history, return specific error
            raise Exception("The explore is not yet used, so no queries could be retrieved.")
        
        if not history_queries or len(history_queries) == 0:
            raise Exception("The explore is not yet used, so no queries could be retrieved.")
        
        logging.info(f"Found {len(history_queries)} historical queries for analysis")
        
        # Fetch explore metadata to provide context to the AI
        try:
            explore_metadata = looker_sdk.lookml_model_explore(
                model_name, 
                explore_name, 
                fields='dimensions,measures,dimension_groups'
            )
        except Exception as e:
            logging.warning(f"Could not fetch explore metadata: {e}")
            explore_metadata = None
        
        # Prepare context for Vertex AI
        context_parts = []
        if explore_metadata:
            # Add dimensions
            if hasattr(explore_metadata, 'dimensions') and explore_metadata.dimensions:
                dims = [d.name for d in explore_metadata.dimensions if d.name]
                context_parts.append(f"Available dimensions: {', '.join(dims[:20])}")  # Limit to first 20
            
            # Add measures
            if hasattr(explore_metadata, 'measures') and explore_metadata.measures:
                measures = [m.name for m in explore_metadata.measures if m.name]
                context_parts.append(f"Available measures: {', '.join(measures[:20])}")  # Limit to first 20
        
        explore_context = '\n'.join(context_parts) if context_parts else f"Explore: {model_name}.{explore_name}"
        
        # Process queries with Vertex AI to generate natural language descriptions
        bronze_queries = []
        
        try:
            # Process queries in batches to avoid token limits
            batch_size = 10
            for i in range(0, min(len(history_queries), 30), batch_size):  # Process max 30 queries
                batch = history_queries[i:i+batch_size]
                
                # Prepare prompt for this batch
                query_descriptions = []
                for idx, query_data in enumerate(batch):
                    query_desc = f"Query {i+idx+1}:\n"
                    if query_data.get('query.formatted_fields'):
                        query_desc += f"Fields: {query_data['query.formatted_fields']}\n"
                    if query_data.get('query.formatted_filters'):
                        query_desc += f"Filters: {query_data['query.formatted_filters']}\n"
                    if query_data.get('query.formatted_pivots'):
                        query_desc += f"Pivots: {query_data['query.formatted_pivots']}\n"
                    if query_data.get('query.sorts'):
                        query_desc += f"Sorts: {query_data['query.sorts']}\n"
                    if query_data.get('query.limit'):
                        query_desc += f"Limit: {query_data['query.limit']}\n"
                    query_descriptions.append({
                        'description': query_desc,
                        'query_data': query_data
                    })
                
                prompt = f"""
You are analyzing Looker queries for the explore "{model_name}.{explore_name}".

{explore_context}

Please convert these Looker queries into natural language questions that a business user might ask. Each question should be clear, business-focused, and reflect what the query is trying to answer.

Queries to convert:
{chr(10).join([q['description'] for q in query_descriptions])}

For each query, provide ONLY the natural language question on a single line, starting with "Q{i+1}: ". Keep questions concise and business-oriented.
"""
                
                # Use existing Vertex AI API function instead of SDK
                vertex_request = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topP": 0.8,
                        "topK": 40,
                        "maxOutputTokens": 1024
                    }
                }
                
                try:
                    vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
                    if vertex_response:
                        response_text = extract_vertex_response_text(vertex_response)
                        if response_text:
                            # Parse the response to extract individual questions
                            lines = response_text.strip().split('\n')
                            for line_idx, line in enumerate(lines):
                                line = line.strip()
                                if line.startswith('Q') and ':' in line:
                                    question = line.split(':', 1)[1].strip()
                                    if question and line_idx < len(query_descriptions):
                                        original_query = query_descriptions[line_idx]['query_data']
                                        
                                        # Extract query parameters from the historical query
                                        explore_params = {}
                                        query_url_params = {}
                                        
                                        # Parse fields from formatted_fields
                                        if original_query.get('query.formatted_fields'):
                                            fields_str = original_query['query.formatted_fields']
                                            # Clean up the fields string and split into list
                                            fields = [f.strip() for f in fields_str.split(',') if f.strip()]
                                            explore_params['fields'] = fields
                                            query_url_params['fields'] = fields
                                        
                                        # Parse filters from formatted_filters
                                        if original_query.get('query.formatted_filters'):
                                            filters_str = original_query['query.formatted_filters']
                                            # For now, store as string - could be parsed more sophisticatedly
                                            explore_params['filters'] = filters_str
                                            query_url_params['f'] = filters_str
                                        
                                        # Parse sorts
                                        if original_query.get('query.sorts'):
                                            sorts_str = original_query['query.sorts']
                                            sorts = [s.strip() for s in sorts_str.split(',') if s.strip()]
                                            explore_params['sorts'] = sorts
                                            query_url_params['sorts'] = sorts
                                        
                                        # Parse limit
                                        if original_query.get('query.limit'):
                                            explore_params['limit'] = str(original_query['query.limit'])
                                            query_url_params['limit'] = str(original_query['query.limit'])
                                        
                                        # Parse pivots if available
                                        if original_query.get('query.formatted_pivots'):
                                            pivots_str = original_query['query.formatted_pivots']
                                            pivots = [p.strip() for p in pivots_str.split(',') if p.strip()]
                                            explore_params['pivots'] = pivots
                                            query_url_params['pivots'] = pivots
                                        
                                        bronze_queries.append({
                                            'input': question,
                                            'output': 'Generated from historical query patterns',
                                            'explore_params': explore_params,  # Store structured query parameters
                                            'query_url_params': query_url_params,  # Store URL-compatible parameters
                                            'query_run_count': original_query.get('history.query_run_count'),
                                            'original_query_url': original_query.get('query.share_url')
                                        })
                
                except Exception as ai_error:
                    logging.error(f"Vertex AI processing failed for batch {i}: {ai_error}")
                    continue
        
        except Exception as ai_setup_error:
            logging.error(f"Vertex AI setup failed: {ai_setup_error}")
            raise Exception(f"AI service failed to generate queries: {ai_setup_error}")
        
        if not bronze_queries:
            raise Exception("No bronze queries could be generated from the available data.")
        
        # Store bronze queries in BigQuery
        try:
            client = bigquery.Client()
            bronze_table_id = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
            
            # Prepare rows for insertion
            rows_to_insert = []
            current_timestamp = datetime.now()
            
            for query in bronze_queries:
                rows_to_insert.append({
                    'explore_key': explore_key,
                    'model_name': model_name,
                    'explore_name': explore_name,
                    'input_question': query['input'],
                    'output_description': query['output'],
                    'explore_params': json.dumps(query.get('explore_params', {})),  # Store as JSON string
                    'query_url_params': json.dumps(query.get('query_url_params', {})),  # Store as JSON string
                    'created_at': current_timestamp.isoformat(),
                    'source': 'auto_generated',
                    'user_email': user_email,
                    'query_run_count': query.get('query_run_count'),
                    'original_query_url': query.get('original_query_url')
                })
            
            # Insert the data
            errors = client.insert_rows_json(bronze_table_id, rows_to_insert)
            
            if errors:
                logging.error(f"BigQuery insertion errors: {errors}")
                raise Exception(f"Failed to store bronze queries: {errors}")
            
            logging.info(f"Successfully stored {len(bronze_queries)} bronze queries for {explore_key}")
            
        except Exception as bq_error:
            logging.error(f"BigQuery storage failed: {bq_error}")
            raise Exception(f"Failed to store bronze queries: {bq_error}")
        
        return {
            'success': True,
            'message': f'Successfully generated {len(bronze_queries)} bronze queries for {explore_key}',
            'queries_generated': len(bronze_queries),
            'explore_key': explore_key
        }
        
    except Exception as e:
        logging.error(f"Bronze query generation failed: {e}")
        raise e

# For running directly as a Flask app (Cloud Run)
if __name__ == "__main__":
    import os
    app = create_mcp_flask_app()
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
