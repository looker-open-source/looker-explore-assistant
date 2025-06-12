# MIT License

# Copyright (c) 2023 Looker Data Sciences, Inc.

# MCP (Model Context Protocol) Server for Looker Explore Assistant
# This server acts as a credential proxy for non-admin users to access
# Vertex AI API by providing secure token exchange.

import os
import time
import json
import logging
from typing import Dict, Any, Optional
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import functions_framework
import requests
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account

logging.basicConfig(level=logging.INFO)

# Initialize environment variables
project = os.environ.get("PROJECT")
location = os.environ.get("REGION", "us-central1")
vertex_model = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")
looker_api_client_id = os.environ.get("LOOKER_API_CLIENT_ID")
looker_api_client_secret = os.environ.get("LOOKER_API_CLIENT_SECRET")
looker_base_url = os.environ.get("LOOKER_BASE_URL")
service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

def get_response_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
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

def call_vertex_ai_api(oauth_token: str, request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call Vertex AI API using the user's OAuth token"""
    try:
        if not project or not location:
            logging.error("Project or location not configured for Vertex AI API")
            return None
        
        # Remove 'Bearer ' prefix if present
        if oauth_token.startswith('Bearer '):
            oauth_token = oauth_token[7:]
        
        # Construct Vertex AI API URL
        vertex_api_url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/google/models/{vertex_model}:generateContent"
        
        headers = {
            'Authorization': f'Bearer {oauth_token}',
            'Content-Type': 'application/json'
        }
        
        # Log the request for debugging
        logging.info(f"Calling Vertex AI API: {vertex_api_url}")
        
        response = requests.post(vertex_api_url, headers=headers, json=request_body)
        
        if not response.ok:
            logging.error(f"Vertex AI API call failed: {response.status_code} - {response.text}")
            return None
        
        logging.info("Vertex AI API call successful")
        return response.json()
        
    except Exception as e:
        logging.error(f"Error calling Vertex AI API: {e}")
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

def determine_explore_from_prompt(oauth_token: str, prompt: str, golden_queries: Dict[str, Any]) -> Optional[str]:
    """First Vertex AI call: Determine which explore to use based on the prompt and all golden queries"""
    try:
        # Build system prompt for explore determination
        system_prompt = f"""You are a Looker Explore Assistant. Your job is to determine which Looker explore is most appropriate for answering a user's question.

Available Explores and Examples:
{json.dumps(golden_queries, indent=2)}

Instructions:
1. Analyze the user's prompt: "{prompt}"
2. Compare it against all available explores and their examples
3. Determine which explore would be best suited to answer this question
4. Return ONLY the explore key (e.g., "order_items", "events", etc.) as a single string
5. If no explore seems appropriate, return the first available explore key

User prompt: {prompt}

Response format: Return only the explore key as plain text (no JSON, no explanation)"""

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
                "maxOutputTokens": 100
            }
        }
        
        # Call Vertex AI
        vertex_response = call_vertex_ai_api(oauth_token, vertex_request)
        if not vertex_response:
            return None
        
        # Extract the explore key from response
        response_text = extract_vertex_response_text(vertex_response)
        if response_text:
            # Clean up the response - remove any extra whitespace or formatting
            explore_key = response_text.strip().replace('"', '').replace('\n', '')
            logging.info(f"Determined explore: {explore_key}")
            return explore_key
        
        return None
        
    except Exception as e:
        logging.error(f"Error determining explore: {e}")
        return None

def generate_explore_params(oauth_token: str, prompt: str, explore_key: str, 
                          golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                          current_explore: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Second Vertex AI call: Generate explore parameters for the chosen explore"""
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
1. Analyze the user's prompt: "{prompt}"
2. Generate appropriate Looker query parameters using the available fields
3. Return a JSON object with the explore parameters

Required JSON format:
{{
  "explore_params": {{
    "fields": ["dimension1", "measure1"],
    "filters": {{"dimension1": "value"}},
    "sorts": ["dimension1 desc"],
    "limit": "500"
  }},
  "message_type": "explore",
  "explore_key": "{explore_key}",
  "summary": "Brief description of what this explore shows"
}}

User prompt: {prompt}"""

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
        
        # Call Vertex AI
        vertex_response = call_vertex_ai_api(oauth_token, vertex_request)
        if not vertex_response:
            return None
        
        # Extract and parse the JSON response
        response_text = extract_vertex_response_text(vertex_response)
        if response_text:
            try:
                result = json.loads(response_text)
                logging.info(f"Generated explore params for {explore_key}")
                return result
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                # Return a fallback response
                return {
                    "explore_params": {
                        "fields": [],
                        "filters": {},
                        "sorts": [],
                        "limit": "500"
                    },
                    "message_type": "explore",
                    "explore_key": explore_key,
                    "summary": f"Unable to generate specific parameters for: {prompt}"
                }
        
        return None
        
    except Exception as e:
        logging.error(f"Error generating explore params: {e}")
        return None

def process_explore_assistant_request(oauth_token: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process the explore assistant request and handle single or dual Vertex AI calls"""
    try:
        logging.info("Starting process_explore_assistant_request")
        
        # Extract data from the Cloud Run request
        prompt = request_data.get('prompt', '')
        conversation_id = request_data.get('conversation_id', '')
        current_explore = request_data.get('current_explore', {})
        golden_queries = request_data.get('golden_queries', {})
        semantic_models = request_data.get('semantic_models', {})
        model_name = request_data.get('model_name', '')
        prompt_history = request_data.get('prompt_history', [])
        data_to_summarize = request_data.get('data_to_summarize', '')
        test_mode = request_data.get('test_mode', False)
        
        logging.info(f"Extracted request data - prompt: '{prompt[:50]}...', test_mode: {test_mode}")
        
        # Handle test mode
        if test_mode:
            logging.info("Returning test mode response")
            return {
                'status': 'ok',
                'message': 'Vertex AI connection test successful',
                'timestamp': time.time()
            }
        
        # Check if current explore is null/empty
        current_explore_key = current_explore.get('exploreKey') if current_explore else None
        
        if not current_explore_key or current_explore_key == '' or current_explore_key == 'null':
            logging.info("Current explore is null - performing two-step process")
            
            # Step 1: Determine which explore to use
            determined_explore_key = determine_explore_from_prompt(oauth_token, prompt, golden_queries)
            if not determined_explore_key:
                return {
                    'error': 'Failed to determine appropriate explore',
                    'message_type': 'error'
                }
            
            # Update current_explore with the determined explore
            current_explore = {
                'exploreKey': determined_explore_key,
                'exploreId': determined_explore_key,
                'modelName': model_name
            }
            
            # Step 2: Generate explore parameters for the determined explore
            result = generate_explore_params(oauth_token, prompt, determined_explore_key, 
                                           golden_queries, semantic_models, current_explore)
            if not result:
                return {
                    'error': 'Failed to generate explore parameters',
                    'message_type': 'error'
                }
            
            # Ensure the explore_key is set in the response
            result['explore_key'] = determined_explore_key
            return result
            
        else:
            # Current explore exists - single call to generate parameters
            logging.info(f"Using current explore: {current_explore_key}")
            
            result = generate_explore_params(oauth_token, prompt, current_explore_key, 
                                           golden_queries, semantic_models, current_explore)
            if not result:
                return {
                    'error': 'Failed to generate explore parameters',
                    'message_type': 'error'
                }
            
            return result
        
    except Exception as e:
        logging.error(f"Error processing explore assistant request: {e}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {
            'error': f'Internal processing error: {str(e)}',
            'message_type': 'error'
        }

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
        
        if request.method == "OPTIONS":
            logging.info("Handling OPTIONS request")
            return "", 204, get_response_headers()
        
        try:
            logging.info("Processing POST request...")
            
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            logging.info(f"Authorization header present: {bool(auth_header)}")
            
            if not auth_header or not auth_header.startswith("Bearer "):
                logging.error("Missing or invalid Authorization header")
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401, get_response_headers()
            
            logging.info("Validating OAuth token...")
            # Validate OAuth token
            oauth_token_info = validate_oauth_token(auth_header)
            if not oauth_token_info:
                logging.error("OAuth token validation failed")
                return jsonify({'error': 'Invalid OAuth token'}), 401, get_response_headers()
            
            logging.info(f"OAuth token validated for user: {oauth_token_info.get('email')}")
            
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
            'endpoints': ['/ (POST)', '/health (GET)']
        }), 200, get_response_headers()
    
    logging.info("Registered endpoint: /health")
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({'error': 'Internal server error'}), 500, get_response_headers()
    
    logging.info("MCP Flask app created with Vertex AI endpoints")
    return app

@functions_framework.http
def mcp_cloud_function_entrypoint(request):
    """Cloud Function entry point for MCP server"""
    if request.method == "OPTIONS":
        return "", 204, get_response_headers()
    
    path = request.path
    
    if path == "/" or path == "":
        try:
            # Get Bearer token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401, get_response_headers()
            
            # Validate OAuth token
            oauth_token_info = validate_oauth_token(auth_header)
            if not oauth_token_info:
                return jsonify({'error': 'Invalid OAuth token'}), 401, get_response_headers()
            
            # Get the request body
            request_data = request.get_json()
            if not request_data:
                return jsonify({'error': 'Missing request body'}), 400, get_response_headers()
            
            # Process the explore assistant request
            result = process_explore_assistant_request(auth_header, request_data)
            
            return jsonify(result), 200, get_response_headers()
            
        except Exception as e:
            logging.error(f"Vertex AI proxy error: {e}")
            return jsonify({'error': 'Internal server error'}), 500, get_response_headers()
    
    elif path == "/health":
        return jsonify({
            'status': 'healthy',
            'service': 'vertex-ai-proxy',
            'timestamp': time.time(),
            'project': project,
            'location': location,
            'model': vertex_model,
            'endpoints': ['/ (POST)', '/health (GET)']
        }), 200, get_response_headers()
    
    else:
        return jsonify({'error': 'Endpoint not found'}), 404, get_response_headers()

if __name__ == "__main__":
    # For local development
    if os.environ.get("FUNCTIONS_FRAMEWORK"):
        # Cloud Function mode
        pass
    else:
        # Local Flask mode
        app = create_mcp_flask_app()
        port = int(os.environ.get("PORT", 8001))
        
        logging.info(f"Starting Vertex AI Proxy Server on port {port}")
        logging.info("Available endpoints:")
        logging.info("  - POST /")
        logging.info("  - GET  /health")
        logging.info(f"Using Vertex AI model: {vertex_model}")
        logging.info(f"Project: {project}, Location: {location}")
        
        app.run(debug=True, host="0.0.0.0", port=port)
        print(f"Vertex AI Proxy Server running on port {port}")
