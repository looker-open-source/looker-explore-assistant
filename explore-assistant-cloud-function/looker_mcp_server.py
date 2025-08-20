#!/usr/bin/env python3
"""
Looker Explore Assistant MCP Server

A comprehensive Model Context Protocol server that provides:
1. Vertex AI API proxy functionality for secure access
2. Semantic field discovery using vector search
3. Looker explore assistance with golden query examples
4. BigQuery integration for query storage and feedback
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Sequence

from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.cloud import bigquery
import looker_sdk
from pydantic import BaseModel, Field
import requests

# Flask imports for HTTP adapter
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

# MCP imports
from mcp import server
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel
)

# Import existing utilities
from llm_utils import parse_llm_response, VertexAIResponse
from olympic_query_manager import OlympicQueryManager, QueryRank
from looker_reference import get_system_prompt_template
# Import modular functions
from parameter_generation.generator import generate_explore_params_from_query
from explore_selection.context import synthesize_conversation_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
PROJECT_ID = os.environ.get("PROJECT", "combined-genai-bi")
REGION = os.environ.get("REGION", "us-central1")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")

# BigQuery configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
BQ_DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")

# Looker configuration for area-based facts tools (using standard LOOKERSDK_ prefix)
LOOKER_BASE_URL = os.environ.get("LOOKERSDK_BASE_URL", "https://bytecodeef.looker.com")
LOOKER_CLIENT_ID = os.environ.get("LOOKERSDK_CLIENT_ID", "")
LOOKER_CLIENT_SECRET = os.environ.get("LOOKERSDK_CLIENT_SECRET", "")

# Debug logging for environment variables
logger.info(f"🔗 LOOKERSDK_BASE_URL loaded: {LOOKER_BASE_URL}")
logger.info(f"🔑 LOOKERSDK_CLIENT_ID loaded: {'[SET]' if LOOKER_CLIENT_ID else '[NOT SET]'}")
logger.info(f"🔐 LOOKERSDK_CLIENT_SECRET loaded: {'[SET]' if LOOKER_CLIENT_SECRET else '[NOT SET]'}")
logger.info(f"📊 Available environment variables: {[k for k in os.environ.keys() if 'LOOKER' in k]}")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

# Pydantic models for structured responses
class FieldMatch(BaseModel):
    """A single field match from vector search"""
    field_location: str = Field(description="Full field path: model.explore.view.field")
    model_name: str
    explore_name: str
    view_name: str
    field_name: str
    field_type: str
    field_description: Optional[str]
    search_term: str
    similarity: float
    matching_values: List[Dict[str, Any]] = Field(description="List of matching field values")

class VertexResponse(BaseModel):
    """Structured response from Vertex AI"""
    response_text: str
    model_used: str
    tokens_used: Optional[int] = None
    processing_time: float

# Utility functions moved from mcp_server.py
def get_max_tokens_for_model(model_name: str) -> dict:
    """Get maximum input and output tokens for the current model"""
    model_limits = {
        # Gemini 2.5 Models (anticipated)
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
    
    if "gemini-1.0" in model_name.lower() or model_name.lower() == "gemini-pro":
        return {"input": 32760, "output": 2048}
    
    # Default fallback for unknown models
    logging.warning(f"Unknown model '{model_name}', using default token limits")
    return {"input": 32760, "output": 2048}

def update_token_warning_thresholds(model_name: str) -> dict:
    """Get appropriate warning thresholds based on model capabilities"""
    model_limits = get_max_tokens_for_model(model_name)
    
    return {
        "prompt_warning": int(model_limits["input"] * 0.8),  # Warn at 80% of input limit
        "total_warning": int((model_limits["input"] + model_limits["output"]) * 0.8),
        "prompt_critical": int(model_limits["input"] * 0.95),  # Critical at 95% of input limit
        "total_critical": int((model_limits["input"] + model_limits["output"]) * 0.95)
    }

def call_vertex_ai_api_with_service_account(request_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Call Vertex AI API using service account credentials"""
    try:
        if not PROJECT_ID or not REGION:
            logging.error("Project or location not configured for Vertex AI API")
            return None
        
        # Get service account credentials
        credentials, _ = default()
        auth_req = Request()
        credentials.refresh(auth_req)
        access_token = credentials.token
        
        # Construct Vertex AI API URL
        vertex_api_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{VERTEX_MODEL}:generateContent"
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Log the request for debugging
        logging.info(f"Calling Vertex AI API with service account: {vertex_api_url}")
        logging.info(f"Using model: {VERTEX_MODEL}")
        
        response = requests.post(vertex_api_url, headers=headers, json=request_body)
        
        if not response.ok:
            logging.error(f"Vertex AI API call failed: {response.status_code} - {response.text}")
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
            thresholds = update_token_warning_thresholds(VERTEX_MODEL)
            
            # Model-aware warnings
            if prompt_tokens > thresholds["prompt_critical"]:
                logging.error(f"🚨 CRITICAL: Prompt token usage ({prompt_tokens:,}) approaching model limit for {VERTEX_MODEL}")
            elif prompt_tokens > thresholds["prompt_warning"]:
                logging.warning(f"⚠️ High prompt token usage: {prompt_tokens:,} tokens for model {VERTEX_MODEL}")
            
            if total_tokens > thresholds["total_critical"]:
                logging.error(f"🚨 CRITICAL: Total token usage ({total_tokens:,}) approaching model limit for {VERTEX_MODEL}")
            elif total_tokens > thresholds["total_warning"]:
                logging.warning(f"⚠️ High total token usage: {total_tokens:,} tokens for model {VERTEX_MODEL}")
            
            # Log model capacity utilization
            model_limits = get_max_tokens_for_model(VERTEX_MODEL)
            prompt_utilization = (prompt_tokens / model_limits["input"]) * 100
            logging.info(f"📊 Model capacity utilization: {prompt_utilization:.1f}% of input limit")
        
        logging.info("Vertex AI API call successful")
        return response_data
        
    except Exception as e:
        logging.error(f"Error calling Vertex AI API: {e}")
        return None

def extract_vertex_response_text(vertex_response: Dict[str, Any]) -> Optional[str]:
    """
    Extract and parse text from Vertex AI response, with robust validation and JSON parsing.
    Returns parsed object if valid JSON or raw text fallback.
    """
    try:
        logging.info(f"🔍 extract_vertex_response_text - Input: {vertex_response}")
        
        # Check for MAX_TOKENS or other finish reasons that indicate incomplete responses
        candidates = vertex_response.get('candidates', [])
        if candidates:
            finish_reason = candidates[0].get('finishReason')
            if finish_reason == 'MAX_TOKENS':
                logging.error("❌ VERTEX AI RESPONSE TRUNCATED: Hit maximum token limit")
                logging.error("💡 Consider reducing prompt size or using a model with higher token limits")
                usage_metadata = vertex_response.get('usageMetadata', {})
                logging.error(f"📊 Token usage: {usage_metadata}")
                return None
            elif finish_reason and finish_reason != 'STOP':
                logging.warning(f"⚠️ Unexpected finish reason: {finish_reason}")
        
        # Validate structure using pydantic
        resp_model = VertexAIResponse.parse_obj(vertex_response)
        # Extract raw text
        first = resp_model.candidates[0]
        content = first.get('content', {})
        parts = content.get('parts', []) or []
        if not parts:
            logging.warning("❌ No parts found in response content")
            return None
        raw_text = parts[0].get('text') if isinstance(parts[0], dict) else parts[0]
        logging.info(f"🔍 Extracted raw text: '{raw_text}' (type: {type(raw_text)})")
        
        # Attempt to parse JSON from raw_text
        parsed = parse_llm_response(raw_text)
        logging.info(f"🔍 Parsed result: {parsed} (type: {type(parsed)})")
        
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
    except Exception as ve:
        logging.warning(f"Vertex AI response schema mismatch: {ve}")
        # Fallback extraction
        try:
            candidates = vertex_response.get('candidates', [])
            logging.info(f"🔍 Fallback - candidates: {candidates}")
            if candidates:
                # Check finish reason in fallback as well
                finish_reason = candidates[0].get('finishReason')
                if finish_reason == 'MAX_TOKENS':
                    logging.error("❌ FALLBACK: Response truncated due to MAX_TOKENS")
                    return None
                
                content = candidates[0].get('content', {})
                parts = content.get('parts', []) or []
                logging.info(f"🔍 Fallback - parts: {parts}")
                if parts:
                    raw_text = parts[0].get('text', '') if isinstance(parts[0], dict) else parts[0]
                    logging.info(f"🔍 Fallback - raw text: '{raw_text}' (type: {type(raw_text)})")
                    parsed = parse_llm_response(raw_text)
                    logging.info(f"🔍 Fallback - parsed: {parsed} (type: {type(parsed)})")
                    return parsed if parsed is not None else raw_text
        except Exception as e:
            logging.error(f"Fallback extraction error: {e}")
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
        
        system_prompt = f"""You are a Looker Explore Assistant. Your job is to determine which Looker explore is most appropriate for answering a user's question.

IMPORTANT: You must analyze the user's question independently and select the BEST explore for their needs, regardless of any previous explore selections or model information.
{restriction_text}
Available Explores:
{explores_text}

{f"Conversation Context:{newline_char}{conversation_context}{newline_char}" if conversation_context else ""}

Instructions:
1. Analyze the user's current prompt: "{prompt}"
2. Consider the conversation context to understand what the user has been asking about
3. Compare against the available explores
4. Determine which explore would be BEST suited to answer this question
5. {"Restrict your selection to the provided explore keys only" if restricted_explore_keys else "Ignore any previous explore selections - choose the optimal explore for this specific question"}
6. Return ONLY the explore key (e.g., "order_items", "events", etc.) as a single string

Current user prompt: {prompt}

Response format: Return only the explore key as plain text (no JSON, no explanation)"""

        logging.info(f"🔍 System prompt length: {len(system_prompt)} characters")
        logging.info(f"🔍 System prompt preview: {system_prompt[:500]}...")
        if len(system_prompt) > 10000:
            logging.warning(f"⚠️ System prompt is very long ({len(system_prompt)} chars) - may cause issues")

        # Format request for Vertex AI
        defaults = get_model_generation_defaults(VERTEX_MODEL)
        
        vertex_request = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                }
            ],
            "generationConfig": {
                "temperature": defaults["temperature"],
                "topP": defaults["topP"],
                "topK": defaults["topK"],
                "maxOutputTokens": 1000,  # Small for explore selection
                "candidateCount": 1
            }
        }
        
        # Call Vertex AI using service account
        vertex_response = call_vertex_ai_api_with_service_account(vertex_request)
        if not vertex_response:
            logging.error("❌ Failed to get response from Vertex AI")
            return None
        
        logging.info(f"✅ Got Vertex AI response: {vertex_response}")
        
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

def get_model_generation_defaults(model_name: str) -> dict:
    """Get appropriate generation config defaults based on model type"""
    is_thinking_model = "thinking" in model_name.lower() or "2.5" in model_name.lower()
    
    if is_thinking_model:
        # Thinking models - slightly more conservative due to internal reasoning
        return {
            "temperature": 0.15,
            "topP": 0.6,
            "topK": 30
        }
    else:
        # Standard models - more creative for field name matching
        return {
            "temperature": 0.2,
            "topP": 0.7,
            "topK": 40
        }

class LookerExploreAssistantMCPServer:
    """MCP Server for Looker Explore Assistant with comprehensive functionality"""
    
    def __init__(self):
        self.server = Server("looker-explore-assistant")
        self.bq_client = None
        self.looker_sdk = None
        self.olympic_manager = None
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="looker://explore-assistant",
                    name="Looker Explore Assistant",
                    description="Comprehensive Looker data exploration with AI assistance and Olympic Query Management",
                    mimeType="application/json"
                ),
                Resource(
                    uri="looker://field-discovery",
                    name="Field Discovery Service", 
                    description="Semantic field discovery using vector search",
                    mimeType="application/json"
                ),
                Resource(
                    uri="looker://vertex-ai-proxy",
                    name="Vertex AI Proxy",
                    description="Secure Vertex AI API access with token management",
                    mimeType="application/json"
                ),
                Resource(
                    uri="looker://status",
                    name="Service Status",
                    description="Current status of all services including Olympic Query Management",
                    mimeType="application/json"
                ),
                Resource(
                    uri="looker://olympic-queries",
                    name="Olympic Query Management",
                    description="Bronze/Silver/Gold query storage and promotion system",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "looker://explore-assistant":
                return json.dumps({
                    "service": "looker-explore-assistant",
                    "version": "2.0.0",
                    "description": "Comprehensive Looker data exploration with AI assistance and Olympic Query Management",
                    "capabilities": [
                        "vertex_ai_proxy",
                        "semantic_field_search", 
                        "field_value_lookup",
                        "looker_query_generation",
                        "golden_query_examples",
                        "olympic_query_management"
                    ]
                }, indent=2)
            elif uri == "looker://field-discovery":
                return json.dumps({
                    "service": "field-discovery",
                    "description": "Semantic field discovery for Looker explores",
                    "vector_table": f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}",
                    "embedding_model": f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{EMBEDDING_MODEL}"
                }, indent=2)
            elif uri == "looker://vertex-ai-proxy":
                return json.dumps({
                    "service": "vertex-ai-proxy",
                    "project": PROJECT_ID,
                    "region": REGION,
                    "default_model": VERTEX_MODEL,
                    "description": "Secure proxy for Vertex AI API access"
                }, indent=2)
            elif uri == "looker://status":
                return json.dumps({
                    "status": "active",
                    "bigquery_connected": self.bq_client is not None,
                    "looker_connected": self.looker_sdk is not None,
                    "olympic_manager_connected": self.olympic_manager is not None,
                    "project_id": PROJECT_ID,
                    "bq_project_id": BQ_PROJECT_ID,
                    "timestamp": datetime.now().isoformat()
                }, indent=2)
            elif uri == "looker://olympic-queries":
                return json.dumps({
                    "service": "olympic-query-management",
                    "description": "Single-table query management with Bronze/Silver/Gold ranks",
                    "table": f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.olympic_queries",
                    "ranks": ["bronze", "silver", "gold"],
                    "capabilities": [
                        "add_bronze_query",
                        "add_silver_query", 
                        "promote_to_gold",
                        "get_gold_queries",
                        "query_statistics"
                    ]
                }, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                # Vertex AI Proxy Tools
                Tool(
                    name="vertex_ai_query",
                    description="Send queries to Vertex AI with secure token management and response parsing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to send to Vertex AI"
                            },
                            "model": {
                                "type": "string",
                                "description": "Optional model to use (defaults to configured model)",
                                "default": VERTEX_MODEL
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "Maximum tokens for response",
                                "default": 8192
                            },
                            "temperature": {
                                "type": "number",
                                "description": "Sampling temperature (0.0 to 1.0)",
                                "default": 0.1,
                                "minimum": 0.0,
                                "maximum": 1.0
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                
                # Field Discovery Tools  
                Tool(
                    name="semantic_field_search",
                    description="Find Looker fields that semantically match search terms using vector similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of specific terms to search for (not full sentences)"
                            },
                            "explore_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "pattern": "^[^:]+:[^:]+$"
                                },
                                "description": "Optional list of explore filters (model:explore format)"
                            },
                            "limit_per_term": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum results per search term"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "default": 0.1,
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Minimum cosine similarity threshold"
                            }
                        },
                        "required": ["search_terms"]
                    }
                ),
                
                Tool(
                    name="field_value_lookup",
                    description="Find dimension values that match specific strings (useful for filter values)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_string": {
                                "type": "string",
                                "description": "Specific string to find in dimension values"
                            },
                            "field_location": {
                                "type": "string",
                                "description": "Optional specific field to search within (model.explore.view.field format)"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10,
                                "description": "Maximum number of matching values to return"
                            }
                        },
                        "required": ["search_string"]
                    }
                ),
                
                # Looker Integration Tools
                Tool(
                    name="get_explore_fields",
                    description="Get available fields for a Looker explore",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "model_name": {
                                "type": "string",
                                "description": "Looker model name"
                            },
                            "explore_name": {
                                "type": "string", 
                                "description": "Looker explore name"
                            }
                        },
                        "required": ["model_name", "explore_name"]
                    }
                ),
                
                Tool(
                    name="run_looker_query",
                    description="Execute a Looker inline query and return results",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_body": {
                                "type": "object",
                                "description": "Looker query body with model, explore, fields, etc."
                            },
                            "result_format": {
                                "type": "string",
                                "default": "json",
                                "enum": ["json", "csv"],
                                "description": "Format for query results"
                            }
                        },
                        "required": ["query_body"]
                    }
                ),
                
                # Core Explore Assistant Tool - The Missing Piece!
                Tool(
                    name="generate_explore_params",
                    description="Convert natural language queries into Looker explore parameters. Automatically determines the best explore from restricted options and transforms user questions into structured Looker queries.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Natural language query from the user (e.g., 'Show me sales by brand for Q2 2023')"
                            },
                            "restricted_explore_keys": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of allowed explore keys in format model:explore (e.g., ['ecommerce:order_items', 'events:events']). The system will choose the best one automatically."
                            },
                            "conversation_context": {
                                "type": "string",
                                "description": "Previous conversation context for multi-turn interactions",
                                "default": ""
                            },
                            "golden_queries": {
                                "type": "object",
                                "description": "Golden query examples for explore selection and parameter generation",
                                "default": {}
                            },
                            "semantic_models": {
                                "type": "object", 
                                "description": "Semantic model metadata with field descriptions",
                                "default": {}
                            }
                        },
                        "required": ["prompt", "restricted_explore_keys"]
                    }
                ),
                
                # Olympic Query Management Tools
                Tool(
                    name="add_bronze_query",
                    description="Add a new bronze (raw) query to the Olympic system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "explore_id": {
                                "type": "string",
                                "description": "Explore ID in model:explore format"
                            },
                            "input": {
                                "type": "string",
                                "description": "User's natural language input"
                            },
                            "output": {
                                "type": "string",
                                "description": "Generated Looker query or response"
                            },
                            "link": {
                                "type": "string",
                                "description": "Looker explore URL or reference"
                            },
                            "user_email": {
                                "type": "string",
                                "description": "User's email address"
                            },
                            "query_run_count": {
                                "type": "integer",
                                "default": 1,
                                "description": "Initial run count for the query"
                            }
                        },
                        "required": ["explore_id", "input", "output", "link", "user_email"]
                    }
                ),
                
                Tool(
                    name="add_silver_query",
                    description="Add a silver (feedback) query to the Olympic system",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "explore_id": {
                                "type": "string",
                                "description": "Explore ID in model:explore format"
                            },
                            "input": {
                                "type": "string",
                                "description": "User's natural language input"
                            },
                            "output": {
                                "type": "string",
                                "description": "Generated Looker query or response"
                            },
                            "link": {
                                "type": "string",
                                "description": "Looker explore URL or reference"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier"
                            },
                            "feedback_type": {
                                "type": "string",
                                "description": "Type of feedback (positive, negative, refinement, etc.)"
                            },
                            "conversation_history": {
                                "type": "string",
                                "description": "Conversation context for multi-turn interactions"
                            }
                        },
                        "required": ["explore_id", "input", "output", "link", "user_id", "feedback_type"]
                    }
                ),
                
                Tool(
                    name="promote_to_gold",
                    description="Promote a bronze or silver query to gold status for training",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_id": {
                                "type": "string",
                                "description": "ID of the query to promote"
                            },
                            "promoted_by": {
                                "type": "string",
                                "description": "Identifier of who is promoting the query"
                            }
                        },
                        "required": ["query_id", "promoted_by"]
                    }
                ),
                
                Tool(
                    name="get_gold_queries",
                    description="Get gold (training) queries for a specific explore or all explores",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "explore_id": {
                                "type": "string",
                                "description": "Optional explore ID to filter queries"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50,
                                "description": "Maximum number of queries to return"
                            }
                        }
                    }
                ),
                
                Tool(
                    name="get_query_stats",
                    description="Get statistics about queries across all Olympic ranks",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                
                # Explicit Feedback Tools
                Tool(
                    name="submit_positive_feedback",
                    description="Submit positive feedback for a query response",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_id": {
                                "type": "string",
                                "description": "Unique identifier for the query"
                            },
                            "user_input": {
                                "type": "string",
                                "description": "The user's original input/question"
                            },
                            "response": {
                                "type": "string", 
                                "description": "The generated response that received positive feedback"
                            },
                            "feedback_notes": {
                                "type": "string",
                                "description": "Optional notes about why this response was helpful"
                            }
                        },
                        "required": ["query_id", "user_input", "response"]
                    }
                ),
                
                Tool(
                    name="submit_negative_feedback",
                    description="Submit negative feedback for a query response with improvement suggestions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_id": {
                                "type": "string",
                                "description": "Unique identifier for the query"
                            },
                            "user_input": {
                                "type": "string",
                                "description": "The user's original input/question"
                            },
                            "response": {
                                "type": "string",
                                "description": "The generated response that received negative feedback"
                            },
                            "issues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of specific issues with the response"
                            },
                            "improvement_suggestions": {
                                "type": "string",
                                "description": "Suggestions for how to improve the response"
                            },
                            "feedback_notes": {
                                "type": "string",
                                "description": "Additional feedback notes"
                            }
                        },
                        "required": ["query_id", "user_input", "response", "issues"]
                    }
                ),
                
                Tool(
                    name="request_response_improvement",
                    description="Request an improved version of a query response based on feedback",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_id": {
                                "type": "string",
                                "description": "Unique identifier for the original query"
                            },
                            "original_input": {
                                "type": "string",
                                "description": "The user's original input/question"
                            },
                            "original_response": {
                                "type": "string",
                                "description": "The original response that needs improvement"
                            },
                            "improvement_request": {
                                "type": "string",
                                "description": "Specific request for how to improve the response"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context or clarification"
                            }
                        },
                        "required": ["query_id", "original_input", "original_response", "improvement_request"]
                    }
                ),
                
                Tool(
                    name="submit_query_feedback",
                    description="Submit explicit user feedback on a generated query",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_id": {
                                "type": "string",
                                "description": "Optional ID of existing query to provide feedback on"
                            },
                            "explore_id": {
                                "type": "string",
                                "description": "Explore ID in model:explore format"
                            },
                            "original_prompt": {
                                "type": "string",
                                "description": "User's original natural language prompt"
                            },
                            "generated_params": {
                                "type": "object",
                                "description": "The Looker explore parameters that were generated"
                            },
                            "share_url": {
                                "type": "string",
                                "description": "Looker share URL for the query"
                            },
                            "feedback_type": {
                                "type": "string",
                                "enum": ["positive", "negative", "refinement", "alternative"],
                                "description": "Type of feedback: positive (thumbs up), negative (thumbs down), refinement (needs improvement), alternative (different approach)"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "User identifier (email or user ID)"
                            },
                            "user_comment": {
                                "type": "string",
                                "description": "Optional detailed feedback comment from user"
                            },
                            "suggested_improvements": {
                                "type": "object",
                                "description": "Optional suggested parameter improvements from user"
                            }
                        },
                        "required": ["explore_id", "original_prompt", "generated_params", "share_url", "feedback_type", "user_id"]
                    }
                ),
                
                Tool(
                    name="get_query_feedback_history",
                    description="Get feedback history for queries to understand user preferences",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "explore_id": {
                                "type": "string",
                                "description": "Optional explore ID to filter feedback"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "Optional user ID to filter feedback"
                            },
                            "feedback_type": {
                                "type": "string",
                                "enum": ["positive", "negative", "refinement", "alternative"],
                                "description": "Optional feedback type to filter"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 20,
                                "description": "Maximum number of feedback entries to return"
                            }
                        }
                    }
                ),
                
                # Query Promotion Management Tools
                Tool(
                    name="get_queries_by_rank",
                    description="Get queries filtered by Olympic rank (bronze, silver, or gold)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rank": {
                                "type": "string",
                                "enum": ["bronze", "silver", "gold"],
                                "description": "Query rank to filter by"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 50,
                                "description": "Maximum number of queries to return"
                            },
                            "offset": {
                                "type": "integer",
                                "default": 0,
                                "description": "Number of queries to skip for pagination"
                            }
                        },
                        "required": ["rank"]
                    }
                ),
                
                Tool(
                    name="get_promotion_history",
                    description="Get audit trail of query promotions between ranks",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "default": 50,
                                "description": "Maximum number of promotion records to return"
                            },
                            "offset": {
                                "type": "integer",
                                "default": 0,
                                "description": "Number of records to skip for pagination"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls - delegates to the main handler method"""
            return await self.handle_tool_call(name, arguments)
    
    def _get_areas_from_bigquery(self) -> List[Dict[str, str]]:
        """Get areas from BigQuery areas table"""
        try:
            if not self.bq_client:
                self.bq_client = bigquery.Client()
            
            query = f"""
            SELECT DISTINCT area, explore_key, description
            FROM `{PROJECT_ID}.explore_assistant.areas`
            ORDER BY area
            """
            
            results = list(self.bq_client.query(query))
            return [
                {
                    "area": row.area,
                    "explore_key": row.explore_key, 
                    "description": row.description
                }
                for row in results
            ]
        except Exception as e:
            logging.warning(f"Could not load areas from BigQuery: {e}")
            return []

    async def get_tools_list(self) -> List[Tool]:
        """Get the list of available tools - used by HTTP adapter"""
        tools = [
            # Vertex AI Proxy Tools
            Tool(
                name="vertex_ai_query",
                description="Send queries to Vertex AI with secure token management and response parsing",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to send to Vertex AI"
                        },
                        "model": {
                            "type": "string",
                            "description": "Optional model to use (defaults to configured model)",
                            "default": VERTEX_MODEL
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens for response",
                            "default": 8192
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature (0.0 to 1.0)",
                            "default": 0.1,
                            "minimum": 0.0,
                            "maximum": 1.0
                        }
                    },
                    "required": ["prompt"]
                }
            ),
            Tool(
                name="vector_search", 
                description="Search vector database for semantically similar fields, tables, and content. Use this tool to discover relevant database fields when the user asks about specific business concepts or metrics.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query describing the business concept, metric, or field you're looking for"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 10)",
                            "default": 10
                        },
                        "similarity_threshold": {
                            "type": "number",
                            "description": "Minimum similarity score (0-1, default 0.7)",
                            "default": 0.7
                        }
                    },
                    "required": ["query"]
                }
            )
        ]
        
        # Add dynamic area-based facts tools
        areas = self._get_areas_from_bigquery()
        unique_areas = {}
        for area_info in areas:
            area = area_info["area"]
            if area not in unique_areas:
                unique_areas[area] = area_info
        
        for area, area_info in unique_areas.items():
            # Create a clean tool name from the area
            tool_name = area.lower().replace(' ', '_').replace('&', 'and').replace('-', '_') + "_facts"
            tool_name = re.sub(r'[^a-z0-9_]', '', tool_name)  # Remove any other special characters
            
            tools.append(Tool(
                name=tool_name,
                description=f"Use this tool to get {area.lower()} data from Looker. Call this tool whenever a user asks ANY question about {area.lower()}, sales, revenue, brands, or related metrics. Pass their question directly to the user_question parameter.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_question": {
                            "type": "string",
                            "description": "The user's question exactly as they asked it. For example: 'what were total sales in 2024 for Adidas?' or 'show me top brands by revenue'. Copy their question word-for-word."
                        },
                        "oauth_token": {
                            "type": "string",
                            "description": "Optional Looker OAuth token for API access"
                        }
                    },
                    "required": ["user_question"]
                }
            ))
        
        return tools
            
    async def handle_tool_call(self, name: str, arguments: dict) -> List[TextContent]:
        """Main tool call handler - accessible from Flask adapter"""
        try:
                if name == "vertex_ai_query":
                    return await self._handle_vertex_ai_query(arguments)
                elif name == "semantic_field_search":
                    return await self._handle_semantic_field_search(arguments) 
                elif name == "field_value_lookup":
                    return await self._handle_field_value_lookup(arguments)
                elif name == "get_explore_fields":
                    return await self._handle_get_explore_fields(arguments)
                elif name == "run_looker_query":
                    return await self._handle_run_looker_query(arguments)
                elif name == "generate_explore_params" or name == "generate_explore_parameters":
                    return await self._handle_generate_explore_params(arguments)
                elif name == "add_bronze_query":
                    return await self._handle_add_bronze_query(arguments)
                elif name == "add_silver_query":
                    return await self._handle_add_silver_query(arguments)
                elif name == "promote_to_gold":
                    return await self._handle_promote_to_gold(arguments)
                elif name == "get_gold_queries":
                    return await self._handle_get_gold_queries(arguments)
                elif name == "get_query_stats":
                    return await self._handle_get_query_stats(arguments)
                elif name == "submit_positive_feedback":
                    return await self._handle_submit_positive_feedback(arguments)
                elif name == "submit_negative_feedback":
                    return await self._handle_submit_negative_feedback(arguments)
                elif name == "request_response_improvement":
                    return await self._handle_request_response_improvement(arguments)
                elif name == "submit_query_feedback":
                    return await self._handle_submit_query_feedback(arguments)
                elif name == "get_query_feedback_history":
                    return await self._handle_get_query_feedback_history(arguments)
                elif name == "get_queries_by_rank":
                    return await self._handle_get_queries_by_rank(arguments)
                elif name == "get_promotion_history":
                    return await self._handle_get_promotion_history(arguments)
                elif name == "vector_search":
                    return await self._handle_vector_search(arguments)
                elif name.endswith("_facts"):
                    return await self._handle_area_facts(name, arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    # Tool implementation methods
    async def _handle_vertex_ai_query(self, arguments: dict) -> List[TextContent]:
        """Handle Vertex AI query requests"""
        prompt = arguments["prompt"]
        model = arguments.get("model", VERTEX_MODEL)
        max_tokens = arguments.get("max_tokens", 8192)
        defaults = get_model_generation_defaults(model)
        temperature = arguments.get("temperature", defaults["temperature"])
        
        try:
            start_time = time.time()
            
            # Build request for Vertex AI
            request_body = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature
                }
            }
            
            # Call Vertex AI (implement the service account call from original server)
            response = await self._call_vertex_ai_with_service_account(request_body, model)
            
            processing_time = time.time() - start_time
            
            if response and "candidates" in response:
                response_text = response["candidates"][0]["content"]["parts"][0]["text"]
                
                result = VertexResponse(
                    response_text=response_text,
                    model_used=model,
                    processing_time=processing_time
                )
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result.dict(), indent=2)
                )]
            else:
                return [TextContent(
                    type="text", 
                    text=json.dumps({"error": "No response from Vertex AI"}, indent=2)
                )]
                
        except Exception as e:
            logger.error(f"Vertex AI query failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Vertex AI query failed: {e}"}, indent=2)
            )]
    
    async def _handle_semantic_field_search(self, arguments: dict) -> List[TextContent]:
        """Handle semantic field search requests"""
        search_terms = arguments["search_terms"]
        explore_ids = arguments.get("explore_ids")
        limit_per_term = arguments.get("limit_per_term", 5) 
        similarity_threshold = arguments.get("similarity_threshold", 0.1)
        
        await self._ensure_bigquery_client()
        
        try:
            all_results = []
            
            for term in search_terms:
                # Use BigQuery VECTOR_SEARCH to find similar fields - using exact working query from field_lookup_service.py
                search_query = f"""
                SELECT 
                    base.model_name,
                    base.explore_name,
                    base.view_name,
                    base.field_name,
                    base.field_type,
                    base.field_description,
                    base.field_value,
                    base.value_frequency,
                    base.field_location,
                    distance,
                    (1 - distance) as similarity
                FROM VECTOR_SEARCH(
                    TABLE `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}`,
                    'ml_generate_embedding_result',
                    (
                        SELECT ml_generate_embedding_result 
                        FROM ML.GENERATE_EMBEDDING(
                            MODEL `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{EMBEDDING_MODEL}`,
                            (SELECT @search_term as content),
                            STRUCT(TRUE AS flatten_json_output)
                        )
                    ),
                    top_k => @limit_per_term
                )
                WHERE (1 - distance) >= @similarity_threshold
                """
                
                # Add explore filtering if specified
                if explore_ids:
                    explore_conditions = []
                    for explore_id in explore_ids:
                        model_name, explore_name = explore_id.split(':')
                        explore_conditions.append(f"(model_name = '{model_name}' AND explore_name = '{explore_name}')")
                    search_query += f" AND ({' OR '.join(explore_conditions)})"
                
                search_query += " ORDER BY similarity DESC"
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("search_term", "STRING", term),
                        bigquery.ScalarQueryParameter("limit_per_term", "INT64", limit_per_term),
                        bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold)
                    ]
                )
                
                results = self.bq_client.query(search_query, job_config=job_config).result()
                
                # Group results by field and collect matching values
                field_matches = {}
                for row in results:
                    field_location = row.field_location
                    
                    if field_location not in field_matches:
                        field_matches[field_location] = {
                            "field_location": field_location,
                            "model_name": row.model_name,
                            "explore_name": row.explore_name,
                            "view_name": row.view_name,
                            "field_name": row.field_name,
                            "field_type": row.field_type,
                            "field_description": row.field_description,
                            "search_term": term,
                            "similarity": float(row.similarity),
                            "matching_values": []
                        }
                    
                    # Add this value to the matching values
                    field_matches[field_location]["matching_values"].append({
                        "value": row.field_value,
                        "similarity": float(row.similarity),
                        "frequency": int(row.value_frequency)
                    })
                    
                    # Keep track of best similarity for this field
                    if float(row.similarity) > field_matches[field_location]["similarity"]:
                        field_matches[field_location]["similarity"] = float(row.similarity)
                
                all_results.extend(field_matches.values())
            
            # Remove duplicates and sort by similarity
            unique_results = {}
            for result in all_results:
                key = result["field_location"]
                if key not in unique_results or result["similarity"] > unique_results[key]["similarity"]:
                    unique_results[key] = result
            
            sorted_results = sorted(unique_results.values(), key=lambda x: x["similarity"], reverse=True)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "search_terms": search_terms,
                    "results_count": len(sorted_results),
                    "field_matches": sorted_results
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Semantic field search failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Semantic field search failed: {e}"}, indent=2)
            )]
    
    async def _handle_field_value_lookup(self, arguments: dict) -> List[TextContent]:
        """Handle field value lookup requests"""
        search_string = arguments["search_string"]
        field_location = arguments.get("field_location")
        limit = arguments.get("limit", 10)
        
        await self._ensure_bigquery_client()
        
        try:
            # Build query to find dimension values containing the search string
            base_query = f"""
            SELECT 
                field_location,
                model_name,
                explore_name,
                view_name,
                field_name,
                field_type,
                field_value,
                value_frequency
            FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}`
            WHERE LOWER(field_value) LIKE LOWER(@search_pattern)
            """
            
            query_params = [
                bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_string}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            # Add field location filter if specified
            if field_location:
                base_query += " AND field_location = @field_location"
                query_params.append(
                    bigquery.ScalarQueryParameter("field_location", "STRING", field_location)
                )
            
            base_query += " ORDER BY value_frequency DESC, field_value LIMIT @limit"
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            results = self.bq_client.query(base_query, job_config=job_config).result()
            
            matching_values = []
            for row in results:
                matching_values.append({
                    "field_location": row.field_location,
                    "model_name": row.model_name,
                    "explore_name": row.explore_name,
                    "view_name": row.view_name,
                    "field_name": row.field_name,
                    "field_type": row.field_type,
                    "field_value": row.field_value,
                    "value_frequency": int(row.value_frequency)
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "search_string": search_string,
                    "field_location_filter": field_location,
                    "results_count": len(matching_values),
                    "matching_values": matching_values
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Field value lookup failed: {e}"}, indent=2)
            )]
    
    async def _handle_get_explore_fields(self, arguments: dict) -> List[TextContent]:
        """Handle get explore fields requests"""
        model_name = arguments["model_name"]
        explore_name = arguments["explore_name"]
        
        await self._ensure_looker_sdk()
        
        try:
            explore_detail = self.looker_sdk.lookml_model_explore(
                lookml_model_name=model_name,
                explore_name=explore_name,
                fields='fields'
            )
            
            fields_info = {
                "dimensions": [],
                "measures": [],
                "filters": []
            }
            
            if explore_detail.fields:
                if explore_detail.fields.dimensions:
                    for dim in explore_detail.fields.dimensions:
                        field_info = {
                            "name": dim.name,
                            "label": dim.label,
                            "type": dim.type,
                            "description": dim.description,
                            "view": dim.view,
                            "field_reference": f"{dim.view}.{dim.name}" if dim.view else dim.name
                        }
                        fields_info["dimensions"].append(field_info)
                        fields_info["filters"].append(field_info)  # Dimensions can be filters
                
                if explore_detail.fields.measures:
                    for measure in explore_detail.fields.measures:
                        field_info = {
                            "name": measure.name,
                            "label": measure.label,
                            "type": measure.type,
                            "description": measure.description,
                            "view": measure.view,
                            "field_reference": f"{measure.view}.{measure.name}" if measure.view else measure.name
                        }
                        fields_info["measures"].append(field_info)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "model_name": model_name,
                    "explore_name": explore_name,
                    "fields": fields_info
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Get explore fields failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Get explore fields failed: {e}"}, indent=2)
            )]
    
    async def _handle_generate_explore_params(self, arguments: dict) -> List[TextContent]:
        """Handle explore parameter generation - The core Explore Assistant function"""
        prompt = arguments["prompt"]
        restricted_explore_keys = arguments["restricted_explore_keys"]
        conversation_context = arguments.get("conversation_context", "")
        golden_queries = arguments.get("golden_queries", {})
        semantic_models = arguments.get("semantic_models", {})
        
        try:
            # Step 1: Determine the best explore from the restricted list
            logger.info(f"Determining best explore from restricted keys: {restricted_explore_keys}")
            
            # Create auth header for determine_explore_from_prompt function
            # This is typically passed as Bearer token, but we'll use service account
            auth_header = "Bearer service_account"  # Placeholder since we use service account
            
            # Use the vector search enhanced parameter generation from mcp_server.py
            logger.info("🔍 Using vector search enhanced parameter generation")
            
            # Step 1: Determine the best explore (with vector search capabilities)
            determined_explore_key = determine_explore_from_prompt(
                auth_header=auth_header,
                prompt=prompt,
                golden_queries=golden_queries,
                conversation_context=conversation_context,
                restricted_explore_keys=restricted_explore_keys
            )
            
            if not determined_explore_key:
                raise ValueError("Unable to determine appropriate explore for this query")
            
            logger.info(f"Determined explore: {determined_explore_key}")
            
            # Extract model and explore names
            if ":" not in determined_explore_key:
                raise ValueError("determined explore_key must be in format 'model:explore'")
            
            model_name, explore_name = determined_explore_key.split(":", 1)
            
            # Create current_explore context
            current_explore = {
                'exploreKey': explore_name,
                'exploreId': determined_explore_key,
                'modelName': model_name
            }
            
            # Step 2: Synthesize conversation context if provided
            synthesized_query = prompt
            if conversation_context:
                logger.info("🔄 Synthesizing conversation context...")
                synthesized_result = synthesize_conversation_context(auth_header, prompt, conversation_context)
                if synthesized_result:
                    synthesized_query = synthesized_result
                    logger.info(f"✅ Synthesized query: {synthesized_query}")
            
            # Step 3: Generate parameters with MANDATORY vector search enhancement
            logger.info("🚀 Generating parameters with vector search enhancement...")
            
            # Get semantic models for this explore (empty dict for now, can be enhanced later)
            semantic_models = {determined_explore_key: {}}
            
            # Call the vector search enhanced parameter generation
            result = generate_explore_params_from_query(
                auth_header=auth_header,
                query=synthesized_query,
                explore_key=determined_explore_key,
                golden_queries=golden_queries,
                semantic_models=semantic_models,
                current_explore=current_explore
            )
            
            if result and isinstance(result, dict):
                # Ensure explore_params has model and view for inline Looker queries
                explore_params = result.get("explore_params", {})
                if "model" not in explore_params:
                    explore_params["model"] = model_name
                if "view" not in explore_params:
                    explore_params["view"] = explore_name
                result["explore_params"] = explore_params
                
                # Add MCP-specific metadata
                result.update({
                    "original_prompt": prompt,
                    "has_conversation_context": bool(conversation_context),
                    "generation_method": "vector_search_enhanced_mcp",
                    "restricted_explore_keys": restricted_explore_keys,
                    "determined_explore": determined_explore_key,
                    "model_name": model_name,
                    "explore_name": explore_name,
                    "explore_key": determined_explore_key
                })
                
                # Log vector search usage if present
                if result.get('vector_search_used'):
                    logger.info(f"🔍 Vector search was used: {len(result['vector_search_used'])} operations")
                    vector_summary = result.get('vector_search_summary', {})
                    if vector_summary.get('user_messages'):
                        logger.info(f"📝 Vector search insights: {vector_summary['user_messages']}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            else:
                # Fallback if vector search enhanced generation fails
                logger.warning("Vector search enhanced generation failed, using basic fallback")
                fallback_params = {
                    "model": model_name,
                    "view": explore_name,
                    "fields": [],
                    "filters": {},
                    "limit": 500
                }
                
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "explore_params": fallback_params,
                        "error": "Vector search enhanced generation failed, using fallback",
                        "explore_key": determined_explore_key,
                        "determined_explore": determined_explore_key,
                        "generation_method": "fallback_no_vector_search"
                    }, indent=2)
                )]
                
        except Exception as e:
            logger.error(f"Generate explore params failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Generate explore params failed: {e}"}, indent=2)
            )]
    
    async def _handle_run_looker_query(self, arguments: dict) -> List[TextContent]:
        """Handle Looker query execution requests"""
        query_body = arguments["query_body"]
        result_format = arguments.get("result_format", "json")
        
        await self._ensure_looker_sdk()
        
        try:
            query_result = self.looker_sdk.run_inline_query(
                result_format=result_format,
                body=query_body
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "query_body": query_body,
                    "result_format": result_format,
                    "result": json.loads(query_result) if result_format == "json" else query_result
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Looker query execution failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Looker query execution failed: {e}"}, indent=2)
            )]
    
    # Olympic Query Management Tools
    async def _handle_add_bronze_query(self, arguments: dict) -> List[TextContent]:
        """Handle adding bronze queries"""
        explore_id = arguments["explore_id"]
        input_text = arguments["input"]
        output = arguments["output"]
        link = arguments["link"]
        user_email = arguments["user_email"]
        query_run_count = arguments.get("query_run_count", 1)
        
        await self._ensure_olympic_manager()
        
        try:
            query_id = self.olympic_manager.add_bronze_query(
                explore_id=explore_id,
                input_text=input_text,
                output=output,
                link=link,
                user_email=user_email,
                query_run_count=query_run_count
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query_id": query_id,
                    "explore_id": explore_id,
                    "rank": "bronze",
                    "user_email": user_email,
                    "query_run_count": query_run_count
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to add bronze query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to add bronze query: {e}"}, indent=2)
            )]
    
    async def _handle_add_silver_query(self, arguments: dict) -> List[TextContent]:
        """Handle adding silver queries"""
        explore_id = arguments["explore_id"]
        input_text = arguments["input"]
        output = arguments["output"]
        link = arguments["link"]
        user_id = arguments["user_id"]
        feedback_type = arguments["feedback_type"]
        conversation_history = arguments.get("conversation_history")
        
        await self._ensure_olympic_manager()
        
        try:
            query_id = self.olympic_manager.add_silver_query(
                explore_id=explore_id,
                input_text=input_text,
                output=output,
                link=link,
                user_id=user_id,
                feedback_type=feedback_type,
                conversation_history=conversation_history
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query_id": query_id,
                    "explore_id": explore_id,
                    "rank": "silver",
                    "user_id": user_id,
                    "feedback_type": feedback_type
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to add silver query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to add silver query: {e}"}, indent=2)
            )]
    
    async def _handle_promote_to_gold(self, arguments: dict) -> List[TextContent]:
        """Handle query promotion to gold"""
        query_id = arguments["query_id"]
        promoted_by = arguments["promoted_by"]
        
        await self._ensure_olympic_manager()
        
        try:
            success = self.olympic_manager.promote_to_gold(
                query_id=query_id,
                promoted_by=promoted_by
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": success,
                    "query_id": query_id,
                    "promoted_by": promoted_by,
                    "promoted_to": "gold" if success else None,
                    "message": "Query promoted successfully" if success else "Query not found or already gold"
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to promote query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to promote query: {e}"}, indent=2)
            )]
    
    async def _handle_get_gold_queries(self, arguments: dict) -> List[TextContent]:
        """Handle getting gold queries for training"""
        explore_id = arguments.get("explore_id")
        limit = arguments.get("limit", 50)
        
        await self._ensure_olympic_manager()
        
        try:
            gold_queries = self.olympic_manager.get_gold_queries_for_training(
                explore_id=explore_id
            )
            
            # Limit results
            gold_queries = gold_queries[:limit]
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "explore_id_filter": explore_id,
                    "results_count": len(gold_queries),
                    "gold_queries": gold_queries
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to get gold queries: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to get gold queries: {e}"}, indent=2)
            )]
    
    async def _handle_get_query_stats(self, arguments: dict) -> List[TextContent]:
        """Handle getting query statistics"""
        await self._ensure_olympic_manager()
        
        try:
            stats = self.olympic_manager.get_query_stats()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "query_statistics": stats,
                    "total_queries": sum(rank_stats.get("count", 0) for rank_stats in stats.values()),
                    "ranks_available": list(stats.keys())
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to get query stats: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to get query stats: {e}"}, indent=2)
            )]
    
    async def _handle_submit_query_feedback(self, arguments: dict) -> List[TextContent]:
        """Handle explicit user feedback submission"""
        query_id = arguments.get("query_id")
        explore_id = arguments["explore_id"]
        original_prompt = arguments["original_prompt"]
        generated_params = arguments["generated_params"]
        share_url = arguments["share_url"]
        feedback_type = arguments["feedback_type"]
        user_id = arguments["user_id"]
        user_comment = arguments.get("user_comment", "")
        suggested_improvements = arguments.get("suggested_improvements")
        
        await self._ensure_olympic_manager()
        
        try:
            # Build conversation history with feedback details
            feedback_details = {
                "feedback_type": feedback_type,
                "original_prompt": original_prompt,
                "generated_params": generated_params,
                "user_comment": user_comment,
                "timestamp": datetime.now().isoformat()
            }
            
            if suggested_improvements:
                feedback_details["suggested_improvements"] = suggested_improvements
            
            conversation_history = json.dumps(feedback_details, indent=2)
            
            # Determine what to store based on feedback type
            if feedback_type == "positive":
                # Positive feedback goes to silver queries as approved examples
                new_query_id = self.olympic_manager.add_silver_query(
                    explore_id=explore_id,
                    input_text=original_prompt,
                    output=json.dumps(generated_params),
                    link=share_url,
                    user_id=user_id,
                    feedback_type="positive_feedback",
                    conversation_history=conversation_history
                )
                message = "Positive feedback recorded. This query is saved as an approved example."
                
            elif feedback_type == "negative":
                # Negative feedback goes to silver with details for improvement
                new_query_id = self.olympic_manager.add_silver_query(
                    explore_id=explore_id,
                    input_text=original_prompt,
                    output=json.dumps(generated_params),
                    link=share_url,
                    user_id=user_id,
                    feedback_type="negative_feedback",
                    conversation_history=conversation_history
                )
                message = "Negative feedback recorded. This will help improve future query generation."
                
            elif feedback_type == "refinement":
                # Refinement suggestions stored with improvement details
                output_data = {
                    "original_params": generated_params,
                    "suggested_improvements": suggested_improvements,
                    "user_comment": user_comment
                }
                new_query_id = self.olympic_manager.add_silver_query(
                    explore_id=explore_id,
                    input_text=original_prompt,
                    output=json.dumps(output_data),
                    link=share_url,
                    user_id=user_id,
                    feedback_type="refinement_suggestion",
                    conversation_history=conversation_history
                )
                message = "Refinement suggestions recorded. Thank you for helping improve the system."
                
            elif feedback_type == "alternative":
                # Alternative approach suggestions
                output_data = {
                    "original_params": generated_params,
                    "alternative_approach": suggested_improvements,
                    "user_comment": user_comment
                }
                new_query_id = self.olympic_manager.add_silver_query(
                    explore_id=explore_id,
                    input_text=original_prompt,
                    output=json.dumps(output_data),
                    link=share_url,
                    user_id=user_id,
                    feedback_type="alternative_approach",
                    conversation_history=conversation_history
                )
                message = "Alternative approach recorded. This helps expand our query generation capabilities."
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "query_id": new_query_id,
                    "feedback_type": feedback_type,
                    "explore_id": explore_id,
                    "user_id": user_id,
                    "message": message,
                    "stored_in": "silver_queries"
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to submit query feedback: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to submit query feedback: {e}"}, indent=2)
            )]
    
    async def _handle_get_query_feedback_history(self, arguments: dict) -> List[TextContent]:
        """Handle getting query feedback history"""
        explore_id = arguments.get("explore_id")
        user_id = arguments.get("user_id")
        feedback_type = arguments.get("feedback_type")
        limit = arguments.get("limit", 20)
        
        await self._ensure_olympic_manager()
        
        try:
            # Build query to get feedback history from silver queries
            base_query = f"""
            SELECT 
                id,
                explore_id,
                input,
                output,
                link,
                user_id,
                feedback_type,
                conversation_history,
                created_at
            FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.olympic_queries`
            WHERE rank = 'silver'
            AND feedback_type LIKE '%_feedback%' OR feedback_type LIKE '%_suggestion' OR feedback_type LIKE '%_approach'
            """
            
            query_params = []
            
            # Add filters if specified
            if explore_id:
                base_query += " AND explore_id = @explore_id"
                query_params.append(
                    bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)
                )
            
            if user_id:
                base_query += " AND user_id = @user_id"
                query_params.append(
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
                )
            
            if feedback_type:
                # Map frontend feedback types to stored feedback types
                feedback_type_mapping = {
                    "positive": "positive_feedback",
                    "negative": "negative_feedback",
                    "refinement": "refinement_suggestion",
                    "alternative": "alternative_approach"
                }
                stored_feedback_type = feedback_type_mapping.get(feedback_type, feedback_type)
                base_query += " AND feedback_type = @feedback_type"
                query_params.append(
                    bigquery.ScalarQueryParameter("feedback_type", "STRING", stored_feedback_type)
                )
            
            base_query += " ORDER BY created_at DESC LIMIT @limit"
            query_params.append(
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            )
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            results = self.bq_client.query(base_query, job_config=job_config).result()
            
            feedback_history = []
            for row in results:
                # Parse conversation history for additional details
                try:
                    conversation_data = json.loads(row.conversation_history) if row.conversation_history else {}
                except:
                    conversation_data = {}
                
                feedback_entry = {
                    "query_id": row.id,
                    "explore_id": row.explore_id,
                    "original_prompt": row.input,
                    "generated_params": json.loads(row.output) if row.output else {},
                    "share_url": row.link,
                    "user_id": row.user_id,
                    "feedback_type": row.feedback_type,
                    "user_comment": conversation_data.get("user_comment", ""),
                    "suggested_improvements": conversation_data.get("suggested_improvements"),
                    "created_at": row.created_at.isoformat() if row.created_at else None
                }
                feedback_history.append(feedback_entry)
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "explore_id_filter": explore_id,
                    "user_id_filter": user_id,
                    "feedback_type_filter": feedback_type,
                    "results_count": len(feedback_history),
                    "feedback_history": feedback_history
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to get feedback history: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to get feedback history: {e}"}, indent=2)
            )]
    
    # New explicit feedback handlers
    async def _handle_submit_positive_feedback(self, arguments: dict) -> List[TextContent]:
        """Handle positive feedback submission"""
        query_id = arguments["query_id"]
        user_input = arguments["user_input"]
        response = arguments["response"]
        feedback_notes = arguments.get("feedback_notes", "")
        
        await self._ensure_olympic_manager()
        
        try:
            # Store positive feedback in silver tier for future use
            new_query_id = self.olympic_manager.add_silver_query(
                explore_id="feedback_query",  # Special explore_id for feedback
                input_text=user_input,
                output=response,
                link="",
                user_id="system",
                feedback_type="positive_feedback",
                conversation_history=feedback_notes
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "Positive feedback recorded successfully",
                    "query_id": query_id,
                    "feedback_id": new_query_id,
                    "feedback_type": "positive"
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to submit positive feedback: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to submit positive feedback: {e}"}, indent=2)
            )]
    
    async def _handle_submit_negative_feedback(self, arguments: dict) -> List[TextContent]:
        """Handle negative feedback submission with improvement suggestions"""
        query_id = arguments["query_id"]
        user_input = arguments["user_input"]
        response = arguments["response"]
        issues = arguments["issues"]
        improvement_suggestions = arguments.get("improvement_suggestions", "")
        feedback_notes = arguments.get("feedback_notes", "")
        
        await self._ensure_olympic_manager()
        
        try:
            # Store negative feedback with improvement suggestions
            feedback_data = {
                "issues": issues,
                "improvement_suggestions": improvement_suggestions,
                "feedback_notes": feedback_notes,
                "original_response": response
            }
            
            new_query_id = self.olympic_manager.add_silver_query(
                explore_id="feedback_query",
                input_text=user_input,
                output=json.dumps(feedback_data),
                link="",
                user_id="system",
                feedback_type="negative_feedback",
                conversation_history=json.dumps({"issues": issues, "suggestions": improvement_suggestions})
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "Negative feedback and improvement suggestions recorded",
                    "query_id": query_id,
                    "feedback_id": new_query_id,
                    "feedback_type": "negative",
                    "issues_count": len(issues),
                    "has_suggestions": bool(improvement_suggestions)
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to submit negative feedback: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to submit negative feedback: {e}"}, indent=2)
            )]
    
    async def _handle_request_response_improvement(self, arguments: dict) -> List[TextContent]:
        """Handle request for improved response based on feedback"""
        query_id = arguments["query_id"]
        original_input = arguments["original_input"]
        original_response = arguments["original_response"]
        improvement_request = arguments["improvement_request"]
        context = arguments.get("context", "")
        
        await self._ensure_olympic_manager()
        
        try:
            # Create an improvement request entry
            improvement_data = {
                "original_response": original_response,
                "improvement_request": improvement_request,
                "context": context,
                "status": "pending"
            }
            
            new_query_id = self.olympic_manager.add_silver_query(
                explore_id="improvement_request",
                input_text=original_input,
                output=json.dumps(improvement_data),
                link="",
                user_id="system", 
                feedback_type="improvement_request",
                conversation_history=context
            )
            
            # TODO: In a full implementation, this could trigger an AI system
            # to generate an improved response based on the feedback
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "message": "Improvement request recorded. A refined response will be generated.",
                    "query_id": query_id,
                    "improvement_id": new_query_id,
                    "improvement_request": improvement_request,
                    "next_steps": "The system will analyze the feedback and generate an improved response"
                }, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Failed to handle improvement request: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Failed to handle improvement request: {e}"}, indent=2)
            )]

    async def _handle_vector_search(self, arguments: dict) -> List[TextContent]:
        """Handle vector search requests"""
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        similarity_threshold = arguments.get("similarity_threshold", 0.7)
        
        try:
            # Import vector search functionality
            from vector_search_mcp_integration import VectorSearchMCPIntegration
            
            vector_search = VectorSearchMCPIntegration()
            results = await vector_search.search_vectors(
                query=query,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            return [TextContent(
                type="text",
                text=json.dumps(results, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Vector search failed: {e}"}, indent=2)
            )]

    async def _handle_area_facts(self, tool_name: str, arguments: dict) -> List[TextContent]:
        """Handle area-based facts requests using the well-tested explore parameter generation logic"""
        logger.info(f"🎯 Area facts tool called: {tool_name}")
        logger.info(f"📝 Arguments received: {arguments}")
        
        if "user_question" not in arguments:
            error_msg = "Missing required parameter 'user_question'. Please provide the user's question."
            logger.error(f"❌ {error_msg}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": error_msg,
                    "example": "user_question: 'what were the top 5 brands by revenue last year?'"
                }, indent=2)
            )]
            
        user_question = arguments["user_question"]
        oauth_token = arguments.get("oauth_token")  # Optional for demo
        
        logger.info(f"🔍 User question: {user_question}")
        logger.info(f"🔐 OAuth token provided: {'Yes' if oauth_token else 'No (demo mode)'}")
        
        try:
            # Extract area from tool name (e.g., "sales_and_revenue_facts" -> "Sales & Revenue")
            area_key = tool_name.replace("_facts", "").replace("_", " ").replace("and", "&").title()
            logger.info(f"🔍 Extracted area key: {area_key}")
            
            # Get all area entries from BigQuery (there may be multiple explore keys per area)
            logger.info("📊 Fetching areas from BigQuery...")
            all_areas = self._get_areas_from_bigquery()
            logger.info(f"📊 Found {len(all_areas)} total area entries in BigQuery")
            
            # Find all entries for this specific area
            area_entries = []
            for area_entry in all_areas:
                if area_entry["area"].lower().replace(" ", "_").replace("&", "and") == area_key.lower().replace(" ", "_").replace("&", "and"):
                    area_entries.append(area_entry)
            
            if not area_entries:
                error_msg = f"No area found for tool {tool_name}. Available areas: {list(set([a['area'] for a in all_areas]))}"
                logger.error(f"❌ {error_msg}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": error_msg}, indent=2)
                )]
            
            logger.info(f"✅ Found {len(area_entries)} explore(s) for area '{area_entries[0]['area']}':")
            for entry in area_entries:
                logger.info(f"   📊 {entry['explore_key']} - {entry['description']}")
            
            # Step 1: Retrieve golden queries for the area's explores
            logger.info("🏆 Retrieving golden queries for area explores...")
            
            # Collect all explore keys for this area
            restricted_explore_keys = [entry["explore_key"] for entry in area_entries]
            area_name = area_entries[0]["area"]  # All entries have the same area name
            
            # Get golden queries for each explore in this area
            golden_queries = {}
            await self._ensure_olympic_manager()
            
            for explore_key in restricted_explore_keys:
                try:
                    explore_gold_queries = self.olympic_manager.get_gold_queries_for_training(explore_id=explore_key)
                    if explore_gold_queries:
                        golden_queries[explore_key] = explore_gold_queries[:10]  # Limit to 10 golden queries per explore
                        logger.info(f"   📊 Found {len(explore_gold_queries)} golden queries for {explore_key}")
                    else:
                        logger.info(f"   ⚠️ No golden queries found for {explore_key}")
                        golden_queries[explore_key] = []
                except Exception as e:
                    logger.warning(f"   ❌ Failed to get golden queries for {explore_key}: {e}")
                    golden_queries[explore_key] = []
            
            total_golden_queries = sum(len(queries) for queries in golden_queries.values())
            logger.info(f"✅ Retrieved {total_golden_queries} total golden queries for {len(restricted_explore_keys)} explores")
            
            # Step 2: Use the well-tested explore parameter generation logic with golden queries
            logger.info("🧠 Generating explore parameters using existing logic with golden queries...")
            
            explore_params_args = {
                "prompt": user_question,
                "restricted_explore_keys": restricted_explore_keys,  # Pass all explores for this area
                "conversation_context": f"This is a {area_name} related question. Available explores: {', '.join(restricted_explore_keys)}",
                "golden_queries": golden_queries  # Include the golden queries for better parameter generation
            }
            
            # Call the existing explore parameter generation method
            explore_params_result = await self._handle_generate_explore_params(explore_params_args)
            
            # Parse the explore parameters result
            if not explore_params_result or len(explore_params_result) == 0:
                raise ValueError("Failed to generate explore parameters")
            
            params_text = explore_params_result[0].text
            params_data = json.loads(params_text)
            
            if "error" in params_data:
                logger.error(f"❌ Explore parameter generation failed: {params_data['error']}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "area": area_name,
                        "available_explores": restricted_explore_keys,
                        "user_question": user_question,
                        "status": "Parameter Generation Failed",
                        "error": params_data["error"]
                    }, indent=2)
                )]
            
            explore_params = params_data.get("explore_params", {})
            determined_explore_key = params_data.get("determined_explore", params_data.get("explore_key", "unknown"))
            logger.info(f"✅ Generated explore parameters for: {determined_explore_key}")
            logger.info(f"   Fields: {len(explore_params.get('fields', []))}, Filters: {len(explore_params.get('filters', {}))}")
            
            # Ensure model and view parameters are present for inline Looker query
            if ":" in determined_explore_key:
                model_name, explore_name = determined_explore_key.split(":", 1)
                if "model" not in explore_params:
                    explore_params["model"] = model_name
                    logger.info(f"   Added missing model parameter: {model_name}")
                if "view" not in explore_params:
                    explore_params["view"] = explore_name
                    logger.info(f"   Added missing view parameter: {explore_name}")
            
            logger.info(f"   Final query params: model={explore_params.get('model')}, view={explore_params.get('view')}")
            
            # Step 3: Use the generated parameters to run the Looker query
            logger.info("📊 Running Looker query with generated parameters...")
            
            query_args = {
                "query_body": explore_params,
                "result_format": "json"
            }
            
            # Call the existing run_looker_query method
            query_result = await self._handle_run_looker_query(query_args)
            
            # Parse the query result
            if not query_result or len(query_result) == 0:
                raise ValueError("Failed to execute Looker query")
            
            query_text = query_result[0].text
            query_data = json.loads(query_text)
            
            if "error" in query_data:
                logger.error(f"❌ Looker query failed: {query_data['error']}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "area": area_name,
                        "available_explores": restricted_explore_keys,
                        "selected_explore": determined_explore_key,
                        "user_question": user_question,
                        "status": "Query Execution Failed",
                        "error": query_data["error"],
                        "explore_params_used": explore_params
                    }, indent=2)
                )]
            
            # Extract the actual query results
            query_results = query_data.get("results", [])
            if isinstance(query_results, str):
                try:
                    query_results = json.loads(query_results)
                except:
                    query_results = []
            
            logger.info(f"✅ Query completed with {len(query_results)} rows from {determined_explore_key}")
            
            # Find which area entry was used (for description)
            used_area_entry = None
            for entry in area_entries:
                if entry["explore_key"] == determined_explore_key:
                    used_area_entry = entry
                    break
            if not used_area_entry:
                used_area_entry = area_entries[0]  # Fallback to first entry
            
            # Step 4: Structure the comprehensive response
            result = {
                "area": area_name,
                "available_explores": restricted_explore_keys,
                "selected_explore": determined_explore_key,
                "selected_explore_description": used_area_entry["description"],
                "user_question": user_question,
                "status": "Success - Using tested explore parameter generation",
                "method": "generate_explore_params + run_looker_query",
                "golden_queries_used": total_golden_queries,
                "explore_params_generated": {
                    "model": explore_params.get("model"),
                    "view": explore_params.get("view"),
                    "fields": explore_params.get("fields", []),
                    "filters": explore_params.get("filters", {}),
                    "pivots": explore_params.get("pivots", []),
                    "sorts": explore_params.get("sorts", []),
                    "limit": explore_params.get("limit")
                },
                "row_count": len(query_results),
                "sample_data": query_results[:5] if query_results else [],  # First 5 rows
                "insights": f"Selected '{determined_explore_key}' from {len(restricted_explore_keys)} available explores for '{user_question}' and retrieved {len(query_results)} rows",
                "fields_selected": explore_params.get("fields", []),
                "filters_applied": explore_params.get("filters", {})
            }
            
            logger.info(f"✅ Generated comprehensive response with {result['row_count']} rows using tested logic")
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
            
        except Exception as e:
            logger.error(f"Area facts generation failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({
                    "area": area_entries[0]["area"] if 'area_entries' in locals() and area_entries else "unknown",
                    "user_question": user_question,
                    "error": f"Area facts generation failed: {e}",
                    "method": "generate_explore_params + run_looker_query"
                }, indent=2)
            )]
    
    # Helper methods
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
            logger.info(f"Initialized BigQuery client for project: {BQ_PROJECT_ID}")
    
    async def _ensure_looker_sdk(self):
        """Ensure Looker SDK is initialized using environment variables"""
        if self.looker_sdk is None:
            try:
                logger.info("Initializing Looker SDK using LOOKERSDK_ environment variables...")
                
                # Check if required environment variables are set
                base_url = os.environ.get('LOOKERSDK_BASE_URL')
                client_id = os.environ.get('LOOKERSDK_CLIENT_ID')
                client_secret = os.environ.get('LOOKERSDK_CLIENT_SECRET')
                
                logger.info(f"LOOKERSDK_BASE_URL: {base_url}")
                logger.info(f"LOOKERSDK_CLIENT_ID: {client_id[:8] + '...' if client_id else 'None'}")
                logger.info(f"LOOKERSDK_CLIENT_SECRET: {'***' if client_secret else 'None'}")
                
                if not base_url:
                    raise Exception("LOOKERSDK_BASE_URL environment variable is not set")
                if not client_id:
                    raise Exception("LOOKERSDK_CLIENT_ID environment variable is not set")
                if not client_secret:
                    raise Exception("LOOKERSDK_CLIENT_SECRET environment variable is not set")
                
                # Initialize SDK using environment variables (no config file needed)
                self.looker_sdk = looker_sdk.init40()
                logger.info("Looker SDK initialized successfully")
                
                # Test the SDK by trying to get current user info
                try:
                    user = self.looker_sdk.me()
                    logger.info(f"Looker SDK test successful - logged in as: {user.email}")
                except Exception as test_error:
                    logger.warning(f"Looker SDK test failed: {test_error}")
                    # Don't fail completely, just log the warning
                    
            except Exception as e:
                logger.error(f"Failed to initialize Looker SDK: {e}")
                raise
    
    async def _ensure_olympic_manager(self):
        """Ensure Olympic Query Manager is initialized"""
        if self.olympic_manager is None:
            await self._ensure_bigquery_client()
            self.olympic_manager = OlympicQueryManager(
                bq_client=self.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            self.olympic_manager.ensure_table_exists()
            logger.info(f"Initialized Olympic Query Manager for {BQ_PROJECT_ID}.{BQ_DATASET_ID}")
    
    async def _call_vertex_ai_with_service_account(self, request_body: dict, model: str) -> dict:
        """Call Vertex AI API using service account credentials"""
        try:
            # Get service account credentials
            credentials, _ = default()
            credentials.refresh(Request())
            
            # Build API endpoint
            endpoint = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/{model}:generateContent"
            
            headers = {
                "Authorization": f"Bearer {credentials.token}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(endpoint, headers=headers, json=request_body)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Vertex AI API call failed: {e}")
            raise
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Looker Explore Assistant MCP Server...")
        logger.info(f"Project: {PROJECT_ID}, Region: {REGION}")
        logger.info(f"BigQuery Project: {BQ_PROJECT_ID}, Dataset: {BQ_DATASET_ID}")
        
        # Initialize clients
        await self._ensure_bigquery_client()
        await self._ensure_looker_sdk()
        await self._ensure_olympic_manager()
        
        # Run the server using stdio transport
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="looker-explore-assistant",
                    server_version="2.0.0",
                    capabilities={
                        "resources": {},
                        "tools": {},
                        "logging": {}
                    }
                )
            )

# =============================================================================
# Flask HTTP Adapter for Cloud Run Deployment
# =============================================================================

from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import asyncio
from threading import Thread

class FlaskMCPAdapter:
    """Flask HTTP adapter that wraps the MCP server for Cloud Run deployment"""
    
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)
        self.mcp_server = None
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route("/", methods=["POST", "OPTIONS"])
        def handle_mcp_request():
            """Main endpoint for MCP tool calls via HTTP"""
            if request.method == "OPTIONS":
                response = Response()
                response.headers.update(self._get_cors_headers())
                response.status_code = 200
                return response
            
            try:
                # Get request data first
                request_data = request.get_json()
                if not request_data:
                    return jsonify({'error': 'Missing request body'}), 400, self._get_cors_headers()
                
                # Check if this is a JSON-RPC MCP protocol request
                if 'method' in request_data:
                    return self._handle_mcp_protocol_request(request_data)
                
                # Otherwise, handle as a direct tool call
                tool_name = request_data.get('tool_name')
                arguments = request_data.get('arguments', {})
                
                if not tool_name:
                    return jsonify({'error': 'Missing tool_name parameter'}), 400, self._get_cors_headers()
                
                # Apply security validation based on tool requirements
                auth_header = request.headers.get("Authorization")
                user_context = self._validate_tool_security(tool_name, auth_header)
                
                # Add user context to arguments for tools that need it
                if user_context:
                    arguments['_user_context'] = user_context
                
                # Initialize MCP server if needed
                if not self.mcp_server:
                    self.mcp_server = LookerExploreAssistantMCPServer()
                
                # Call the MCP tool asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    # Use the MCP server's call_tool handler
                    result = loop.run_until_complete(
                        self._call_mcp_tool(tool_name, arguments)
                    )
                    
                    # Parse result from MCP TextContent format
                    if result and len(result) > 0:
                        import json
                        response_text = result[0].text
                        try:
                            parsed_result = json.loads(response_text)
                            return jsonify(parsed_result), 200, self._get_cors_headers()
                        except json.JSONDecodeError:
                            # If not JSON, return as plain text result
                            return jsonify({'result': response_text}), 200, self._get_cors_headers()
                    else:
                        return jsonify({'error': 'No result from MCP tool'}), 500, self._get_cors_headers()
                        
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Flask adapter error: {e}")
                return jsonify({'error': str(e)}), 500, self._get_cors_headers()
        
        @self.app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint"""
            return jsonify({'status': 'healthy', 'service': 'looker-mcp-server'}), 200
        
        @self.app.route("/cors", methods=["OPTIONS"])
        def cors_preflight():
            """Handle CORS preflight requests"""
            response = Response()
            response.headers.update(self._get_cors_headers())
            response.status_code = 200
            return response
    
    def _handle_mcp_protocol_request(self, request_data):
        """Handle MCP JSON-RPC protocol requests like tools/list"""
        try:
            method = request_data.get('method')
            params = request_data.get('params', {})
            request_id = request_data.get('id')
            
            # Initialize MCP server if needed
            if not self.mcp_server:
                self.mcp_server = LookerExploreAssistantMCPServer()
            
            # Handle different MCP protocol methods
            if method == 'tools/list':
                # Call the MCP server's list_tools handler
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    tools = loop.run_until_complete(self.mcp_server.get_tools_list())
                    
                    # Convert Tool objects to JSON format
                    tools_json = []
                    for tool in tools:
                        tools_json.append({
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        })
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": tools_json
                        }
                    }
                    return jsonify(response), 200, self._get_cors_headers()
                finally:
                    loop.close()
            
            elif method == 'tools/call':
                # Handle tool calls via MCP protocol
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if not tool_name:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": "Missing tool name"
                        }
                    }
                    return jsonify(error_response), 400, self._get_cors_headers()
                
                # Apply security validation
                auth_header = request.headers.get("Authorization")
                user_context = self._validate_tool_security(tool_name, auth_header)
                
                if user_context:
                    arguments['_user_context'] = user_context
                
                # Call the tool
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self._call_mcp_tool(tool_name, arguments)
                    )
                    
                    # Convert TextContent result to MCP protocol response
                    content = []
                    for item in result:
                        content.append({
                            "type": "text",
                            "text": item.text
                        })
                    
                    response = {
                        "jsonrpc": "2.0", 
                        "id": request_id,
                        "result": {
                            "content": content
                        }
                    }
                    return jsonify(response), 200, self._get_cors_headers()
                finally:
                    loop.close()
            
            else:
                # Unknown method
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
                return jsonify(error_response), 400, self._get_cors_headers()
                
        except Exception as e:
            logger.error(f"MCP protocol error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": request_data.get('id'),
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            return jsonify(error_response), 500, self._get_cors_headers()
    
    async def _call_mcp_tool(self, tool_name: str, arguments: dict):
        """Call MCP tool and return result"""
        # Call the MCP server's handle_tool_call method directly
        result = await self.mcp_server.handle_tool_call(tool_name, arguments)
        return result
    
    def _get_cors_headers(self):
        """Get CORS headers for responses"""
        return {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Max-Age': '3600'
        }
    
    def _validate_tool_security(self, tool_name: str, auth_header: str):
        """
        Validate authentication based on tool security requirements
        Returns user_context dict for tools that need it, None for low-security tools
        """
        # Define security levels for each tool
        HIGH_SECURITY_TOOLS = {
            'run_looker_query'  # Requires user impersonation
        }
        
        MEDIUM_SECURITY_TOOLS = {
            'promote_to_gold'  # Requires developer role validation
        }
        
        # All other tools are LOW_SECURITY (GCP infrastructure validation only)
        
        if tool_name in HIGH_SECURITY_TOOLS:
            # High security: Extract user email and create user-impersonated Looker SDK
            user_email = self._extract_user_email_from_token(auth_header)
            if not user_email:
                raise ValueError("User authentication required for this operation")
            
            # TODO: Initialize user-impersonated Looker SDK
            return {
                'security_level': 'high',
                'user_email': user_email,
                'requires_user_sdk': True
            }
            
        elif tool_name in MEDIUM_SECURITY_TOOLS:
            # Medium security: Validate user has developer role
            user_email = self._extract_user_email_from_token(auth_header)
            if not user_email:
                raise ValueError("Authentication required for promotion operations")
            
            # Validate developer role (simplified - just check user exists)
            # In production, you might want to validate actual Looker roles
            return {
                'security_level': 'medium',
                'user_email': user_email,
                'requires_developer_role': True
            }
            
        else:
            # Low security: No additional validation required
            # GCP infrastructure handles basic token validation
            return None
    
    def _extract_user_email_from_token(self, auth_header: str):
        """
        Extract user email from OAuth token
        Returns None if token is invalid or email cannot be extracted
        """
        if not auth_header:
            return None
            
        try:
            # Remove 'Bearer ' prefix if present
            token = auth_header
            if token.lower().startswith('bearer '):
                token = token[7:]
            
            # Remove any whitespace
            token = token.strip()
            
            # Split JWT into parts
            token_parts = token.split('.')
            if len(token_parts) != 3:
                logger.error(f"Invalid JWT format: expected 3 parts, got {len(token_parts)}")
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
                    logger.info(f"Extracted user email: {email}")
                    return email
                else:
                    logger.error("No email found in token payload")
                    return None
                    
            except Exception as e:
                logger.error(f"Failed to decode JWT payload: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract user email from token: {e}")
            return None
    
    def run(self, host='0.0.0.0', port=8080, debug=False):
        """Run the Flask app"""
        logger.info(f"Starting Flask MCP Adapter on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def create_flask_app():
    """Create and return Flask app for Cloud Run deployment"""
    adapter = FlaskMCPAdapter()
    return adapter.app

def main():
    """Main entry point - supports both MCP and Flask HTTP modes"""
    import sys
    
    # Default: run Flask HTTP server for Cloud Run
    # Only run desktop MCP mode if explicitly requested
    if len(sys.argv) > 1 and sys.argv[1] in ("--stdio", "--desktop"):
        # Pure MCP mode for desktop clients
        server = LookerExploreAssistantMCPServer()
        asyncio.run(server.run())
    else:
        # Flask HTTP mode for Cloud Run (default)
        adapter = FlaskMCPAdapter()
        port = int(os.environ.get("PORT", 8080))
        adapter.run(host='0.0.0.0', port=port, debug=False)

# For Cloud Run deployment
app = create_flask_app()

if __name__ == "__main__":
    main()
