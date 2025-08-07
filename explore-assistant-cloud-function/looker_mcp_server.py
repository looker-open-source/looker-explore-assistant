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

class LookerExploreAssistantMCPServer:
    """MCP Server for Looker Explore Assistant with comprehensive functionality"""
    
    def __init__(self):
        self.server = Server("looker-explore-assistant")
        self.bq_client = None
        self.looker_sdk = None
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
                    description="Comprehensive Looker data exploration with AI assistance",
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
                    description="Current status of all services",
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
                    "description": "Comprehensive Looker data exploration with AI assistance",
                    "capabilities": [
                        "vertex_ai_proxy",
                        "semantic_field_search", 
                        "field_value_lookup",
                        "looker_query_generation",
                        "golden_query_examples"
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
                    "project_id": PROJECT_ID,
                    "bq_project_id": BQ_PROJECT_ID,
                    "timestamp": datetime.now().isoformat()
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
                    description="Convert natural language queries into Looker explore parameters. This is the core function that transforms user questions into structured Looker queries.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Natural language query from the user (e.g., 'Show me sales by brand for Q2 2023')"
                            },
                            "explore_key": {
                                "type": "string", 
                                "description": "Target explore in format model:explore (e.g., 'ecommerce:order_items')"
                            },
                            "conversation_context": {
                                "type": "string",
                                "description": "Previous conversation context for multi-turn interactions",
                                "default": ""
                            },
                            "golden_queries": {
                                "type": "object",
                                "description": "Golden query examples for the explore",
                                "default": {}
                            },
                            "semantic_models": {
                                "type": "object", 
                                "description": "Semantic model metadata with field descriptions",
                                "default": {}
                            }
                        },
                        "required": ["prompt", "explore_key"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls"""
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
                elif name == "generate_explore_params":
                    return await self._handle_generate_explore_params(arguments)
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
        temperature = arguments.get("temperature", 0.1)
        
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
        explore_key = arguments["explore_key"]
        conversation_context = arguments.get("conversation_context", "")
        golden_queries = arguments.get("golden_queries", {})
        semantic_models = arguments.get("semantic_models", {})
        
        try:
            # Extract model and explore names from explore_key
            if ":" not in explore_key:
                raise ValueError("explore_key must be in format 'model:explore'")
            
            model_name, explore_name = explore_key.split(":", 1)
            
            # Create current_explore context for compatibility
            current_explore = {
                'exploreKey': explore_name,
                'exploreId': explore_key,
                'modelName': model_name
            }
            
            # For now, we'll create a simplified version that uses Vertex AI to generate parameters
            # This maintains the core functionality while working within the MCP framework
            
            # Build a comprehensive prompt for Vertex AI that includes field metadata
            system_prompt = f"""
You are an expert Looker analyst. Convert the user's natural language query into structured Looker explore parameters.

TARGET EXPLORE: {explore_key} (Model: {model_name}, Explore: {explore_name})

AVAILABLE FIELDS:
"""
            
            # Get available fields for this explore
            await self._ensure_looker_sdk()
            try:
                explore_detail = self.looker_sdk.lookml_model_explore(
                    lookml_model_name=model_name,
                    explore_name=explore_name,
                    fields='fields'
                )
                
                if explore_detail.fields:
                    if explore_detail.fields.dimensions:
                        system_prompt += "\nDIMENSIONS:\n"
                        for dim in explore_detail.fields.dimensions[:20]:  # Limit to avoid token overflow
                            system_prompt += f"- {dim.view}.{dim.name}: {dim.label or dim.name}"
                            if dim.description:
                                system_prompt += f" ({dim.description})"
                            system_prompt += "\n"
                    
                    if explore_detail.fields.measures:
                        system_prompt += "\nMEASURES:\n"
                        for measure in explore_detail.fields.measures[:20]:  # Limit to avoid token overflow
                            system_prompt += f"- {measure.view}.{measure.name}: {measure.label or measure.name}"
                            if measure.description:
                                system_prompt += f" ({measure.description})"
                            system_prompt += "\n"
                            
            except Exception as e:
                logger.warning(f"Could not fetch explore fields: {e}")
                system_prompt += "\n(Field metadata not available - using generic field patterns)\n"
            
            # Add conversation context if provided
            if conversation_context:
                system_prompt += f"\nCONVERSATION CONTEXT:\n{conversation_context}\n"
            
            system_prompt += f"""
USER QUERY: {prompt}

Generate a JSON response with these explore parameters (using Looker API format):
{{
  "model": "{model_name}",
  "view": "{explore_name}",
  "fields": ["dimension1", "measure1", "dimension2"],
  "filters": {{"field": "value"}},
  "sorts": ["field desc"],
  "limit": 500,
  "total": false,
  "query_timezone": "America/Los_Angeles"
}}

Instructions:
1. Only include fields that exist in the available fields list
2. Use proper field references (view.field_name format)
3. Choose appropriate filters based on the user query
4. Combine both dimensions and measures into the "fields" array
5. Use "view" instead of "explore" (legacy API requirement)
6. Add appropriate sorting if mentioned or implied
7. Keep limit reasonable (500 or less)
8. Return only valid JSON without additional text
"""
            
            # Call Vertex AI to generate the parameters
            vertex_request = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": system_prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 2048,
                    "temperature": 0.1
                }
            }
            
            vertex_response = await self._call_vertex_ai_with_service_account(vertex_request, VERTEX_MODEL)
            
            if "candidates" in vertex_response and len(vertex_response["candidates"]) > 0:
                response_text = vertex_response["candidates"][0]["content"]["parts"][0]["text"]
                
                # Try to parse the JSON response
                try:
                    # Clean up the response to extract JSON
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        explore_params = json.loads(json_str)
                        
                        # Validate and enhance the parameters for Looker API format
                        if not isinstance(explore_params.get('fields'), list):
                            explore_params['fields'] = []
                        if not isinstance(explore_params.get('filters'), dict):
                            explore_params['filters'] = {}
                        
                        # Ensure required fields are present
                        if 'model' not in explore_params:
                            explore_params['model'] = model_name
                        if 'view' not in explore_params:
                            explore_params['view'] = explore_name
                        
                        result = {
                            "explore_params": explore_params,
                            "explore_key": explore_key,
                            "model_name": model_name,
                            "explore_name": explore_name,
                            "original_prompt": prompt,
                            "has_conversation_context": bool(conversation_context),
                            "generation_method": "vertex_ai_mcp"
                        }
                        
                        return [TextContent(
                            type="text",
                            text=json.dumps(result, indent=2)
                        )]
                        
                    else:
                        raise ValueError("No valid JSON found in response")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response: {response_text}")
                    
                    # Fallback: return a basic structure using correct Looker API format
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
                            "error": "Failed to parse AI response, using fallback",
                            "raw_response": response_text[:500],
                            "explore_key": explore_key
                        }, indent=2)
                    )]
            else:
                raise ValueError("No response from Vertex AI")
                
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

def main():
    """Main entry point"""
    server = LookerExploreAssistantMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
