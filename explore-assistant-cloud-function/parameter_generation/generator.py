"""
Explore parameter generation

Core logic for generating Looker query parameters from natural language queries
with vector search enhancement and semantic field discovery.
"""

import json
import logging
from typing import Dict, Any, Optional, List

from vertex.client import call_vertex_ai_with_retry
from vector_search.client import VectorSearchClient
from core.config import get_model_generation_defaults, VERTEX_MODEL
from core.exceptions import ParameterGenerationError
from core.models import GenerationResult, QueryParameters

logger = logging.getLogger(__name__)


def generate_explore_params_from_query(auth_header: str, query: str, explore_key: str, 
                                     golden_queries: Dict[str, Any], semantic_models: Dict[str, Any],
                                     current_explore: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Generate explore parameters from a clear, synthesized query with vector search enhancement
    
    Args:
        auth_header: Authorization header
        query: Synthesized user query
        explore_key: Target explore key (model:explore)
        golden_queries: Golden query examples
        semantic_models: Semantic models for field information
        current_explore: Current explore context
        
    Returns:
        Dictionary containing explore parameters and metadata
        
    Raises:
        ParameterGenerationError: If parameter generation fails
    """
    try:
        logger.info(f"🚀 Generating parameters for query: {query}")
        logger.info(f"🎯 Target explore: {explore_key}")
        
        # Step 1: Get semantic model for this specific explore
        explore_semantic_model = semantic_models.get(explore_key, {})
        if not explore_semantic_model:
            logger.warning(f"⚠️ No semantic model found for explore: {explore_key}")
        
        # Step 2: Enhance query with vector search (temporarily disabled until async is fixed)
        # vector_client = VectorSearchClient()
        # param_context, explore_context, search_results = await vector_client.enhance_query_for_parameters(
        #     query, 
        #     lambda req: call_vertex_ai_with_retry(req, context="vector_search", process_response=False)
        # )
        
        # Temporary fallback without vector search
        param_context = f"Query: {query}\n\nPlease generate appropriate parameters."
        explore_context = ""
        search_results = {}
        
        # Step 3: Build comprehensive system prompt
        system_prompt = _build_parameter_generation_prompt(
            query, explore_key, explore_semantic_model, golden_queries, 
            param_context, explore_context
        )
        
        # Step 4: Call Vertex AI for parameter generation
        explore_params = _generate_parameters_with_ai(system_prompt, explore_key)
        
        if not explore_params:
            raise ParameterGenerationError(f"AI failed to generate parameters", explore_key)
        
        # Step 5: Validate and format parameters
        from parameter_generation.validator import validate_explore_parameters, format_parameters_for_looker
        
        validated_params = validate_explore_parameters(explore_params, explore_key)
        formatted_params = format_parameters_for_looker(validated_params)
        
        # Step 6: Build comprehensive result
        result = {
            "explore_params": formatted_params,
            "explore_key": explore_key,
            "original_query": query,
            "vector_search_used": _format_vector_search_results(search_results),
            "generation_method": "vector_search_enhanced",
            "model_used": VERTEX_MODEL,
            "field_context_available": bool(explore_semantic_model),
            "golden_examples_used": _count_golden_examples(golden_queries, explore_key)
        }
        
        # Add vector search summary if available
        if search_results:
            result["vector_search_summary"] = _generate_vector_search_summary(search_results)
        
        logger.info(f"✅ Successfully generated parameters for {explore_key}")
        return result
        
    except ParameterGenerationError:
        raise
    except Exception as e:
        logger.error(f"Parameter generation failed: {e}")
        raise ParameterGenerationError(f"Parameter generation failed: {e}", explore_key)


def _build_parameter_generation_prompt(query: str, explore_key: str, semantic_model: Dict[str, Any],
                                     golden_queries: Dict[str, Any], param_context: str, 
                                     explore_context: str) -> str:
    """Build comprehensive system prompt for parameter generation"""
    
    # Extract model and explore names
    model_name, explore_name = explore_key.split(':', 1) if ':' in explore_key else ('unknown', explore_key)
    
    # Build field context
    field_context = ""
    if semantic_model:
        dimensions = semantic_model.get('dimensions', [])
        measures = semantic_model.get('measures', [])
        
        if dimensions:
            field_context += f"\n## Available Dimensions ({len(dimensions)}):\n"
            for dim in dimensions[:50]:  # Limit for token efficiency
                name = dim.get('name', '')
                label = dim.get('label', '')
                description = dim.get('description', '')
                field_context += f"- {name}: {label}"
                if description:
                    field_context += f" ({description})"
                field_context += "\n"
        
        if measures:
            field_context += f"\n## Available Measures ({len(measures)}):\n"
            for measure in measures[:30]:  # Limit for token efficiency  
                name = measure.get('name', '')
                label = measure.get('label', '')
                description = measure.get('description', '')
                field_context += f"- {name}: {label}"
                if description:
                    field_context += f" ({description})"
                field_context += "\n"
    
    # Add golden query examples if available
    example_context = ""
    if golden_queries and explore_key in golden_queries:
        examples = golden_queries[explore_key][:3]  # Top 3 examples
        if examples:
            example_context = f"\n## Example Queries for {explore_key}:\n"
            for i, example in enumerate(examples, 1):
                if isinstance(example, dict):
                    example_query = example.get('input', '')
                    example_params = example.get('output', '')
                    example_context += f"{i}. Query: {example_query}\n   Parameters: {example_params}\n\n"
    
    # Build the comprehensive prompt
    system_prompt = f"""You are an expert Looker query builder. Generate JSON parameters for a Looker inline query.

EXPLORE: {explore_key}
QUERY: {query}

{field_context}

{param_context}

{example_context}

Generate a JSON object with these fields:
- "model": "{model_name}"
- "view": "{explore_name}"  
- "fields": array of field names to select
- "filters": object with field filters (field_name: "filter_value")
- "sorts": array of sort specifications ("field_name desc/asc")
- "pivots": array of pivot field names (optional)
- "limit": number (default 500)

Rules:
1. Use exact field names from the available fields above
2. Include relevant dimensions and measures based on the query
3. Add appropriate filters based on query requirements
4. Include sorts for logical ordering
5. Use vector search discoveries if available
6. Return only valid JSON

JSON Response:"""
    
    return system_prompt


def _generate_parameters_with_ai(system_prompt: str, explore_key: str) -> Optional[Dict[str, Any]]:
    """Generate parameters using Vertex AI"""
    
    # Build Vertex AI request
    defaults = get_model_generation_defaults(VERTEX_MODEL)
    
    vertex_request = {
        "contents": [{
            "role": "user",
            "parts": [{"text": system_prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 2000,  # Enough for complex parameters
            "temperature": defaults["temperature"],
            "topP": defaults["topP"],
            "topK": defaults["topK"]
        }
    }
    
    try:
        # Call Vertex AI
        vertex_response = call_vertex_ai_with_retry(
            vertex_request, 
            context=f"parameter_generation_{explore_key}", 
            process_response=False
        )
        
        if not vertex_response:
            logger.error("❌ No response from Vertex AI")
            return None
        
        # Extract and parse response
        from vertex.response_parser import extract_vertex_response_text
        response_text = extract_vertex_response_text(vertex_response)
        
        if not response_text:
            logger.error("❌ No text extracted from Vertex AI response")
            return None
        
        # Try to parse JSON response
        try:
            if isinstance(response_text, dict):
                # Already parsed
                return response_text
            elif isinstance(response_text, str):
                # Extract JSON from text
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response_text[:500]}")
        
        return None
        
    except Exception as e:
        logger.error(f"Error generating parameters with AI: {e}")
        return None


def _format_vector_search_results(search_results: Dict[str, List]) -> List[Dict[str, Any]]:
    """Format vector search results for inclusion in response"""
    
    formatted = []
    
    if "semantic_fields" in search_results:
        for field in search_results["semantic_fields"]:
            formatted.append({
                "function": "search_semantic_fields",
                "args": {"field_location": field["field_location"]},
                "phase": "parameter_generation_preprocessing",
                "results_summary": f"Found field: {field['field_location']}"
            })
    
    if "field_values" in search_results:
        for value in search_results["field_values"]:
            formatted.append({
                "function": "lookup_field_values", 
                "args": {"field_location": value["field_location"], "value": value["value"]},
                "phase": "parameter_generation_preprocessing",
                "results_summary": f"Found value: {value['value']} in {value['field_location']}"
            })
    
    return formatted


def _generate_vector_search_summary(search_results: Dict[str, List]) -> Dict[str, Any]:
    """Generate user-friendly summary of vector search usage"""
    
    field_count = len(search_results.get("semantic_fields", []))
    value_count = len(search_results.get("field_values", []))
    
    messages = []
    if field_count > 0:
        messages.append(f"Discovered {field_count} relevant fields using semantic search")
    if value_count > 0:
        messages.append(f"Found {value_count} matching values in database fields")
    
    return {
        "total_vector_searches": field_count + value_count,
        "search_semantic_fields_count": field_count,
        "lookup_field_values_count": value_count,
        "user_messages": messages,
        "detailed_usage": _format_vector_search_results(search_results)
    }


def _count_golden_examples(golden_queries: Dict[str, Any], explore_key: str) -> int:
    """Count available golden examples for the explore"""
    
    if not golden_queries:
        return 0
    
    count = 0
    
    # Count from different golden query sections
    for key in ['exploreGenerationExamples', 'exploreRefinementExamples', 'exploreSamples']:
        if key in golden_queries and isinstance(golden_queries[key], dict):
            if explore_key in golden_queries[key]:
                examples = golden_queries[key][explore_key]
                if isinstance(examples, list):
                    count += len(examples)
                elif isinstance(examples, dict):
                    count += len(examples)
                else:
                    count += 1
    
    return count