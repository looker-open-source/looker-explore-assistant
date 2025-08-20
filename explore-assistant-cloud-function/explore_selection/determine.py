"""
Explore determination logic

Determines the best Looker explore to use based on user queries,
conversation context, and available golden query examples.
"""

import logging
from typing import Dict, Any, Optional, List

from vertex.client import call_vertex_ai_with_retry
from core.exceptions import ExploreNotFoundError
from core.config import get_model_generation_defaults, VERTEX_MODEL

logger = logging.getLogger(__name__)


def determine_explore_from_prompt(auth_header: str, prompt: str, golden_queries: Dict[str, Any], 
                                conversation_context: str = "", restricted_explore_keys: List[str] = None, semantic_models: Dict[str, Any] = None) -> Optional[str]:
    """
    Enhanced explore determination with conversation context, area restrictions, and optional semantic field discovery.
    Uses Vertex AI function calling to intelligently search for relevant fields when needed.
    
    Args:
        auth_header: Authorization header (for compatibility)
        prompt: User's natural language query
        golden_queries: Dictionary of golden query examples
        conversation_context: Previous conversation context
        restricted_explore_keys: Optional list to restrict explore selection to
        
    Returns:
        Selected explore key in format 'model:explore'
        
    Raises:
        ExploreNotFoundError: If no suitable explore is found
    """
    try:
        logger.info("=== EXPLORE DETERMINATION START ===")
        logger.info(f"Determining best explore for prompt: {prompt}")
        logger.info(f"Has conversation context: {bool(conversation_context)}")
        logger.info(f"Restricted explore keys: {restricted_explore_keys}")
        logger.info(f"semantic_models provided: {type(semantic_models)}")

        # Log the keys in golden_queries
        if isinstance(golden_queries, dict):
            logger.info(f"golden_queries top-level keys: {list(golden_queries.keys())}")
        else:
            logger.info(f"golden_queries is not a dict: {type(golden_queries)}")

        # Optionally log semantic_models keys
        if isinstance(semantic_models, dict):
            logger.info(f"semantic_models keys: {list(semantic_models.keys())}")

        # Filter golden queries by restricted explore keys if provided
        filtered_golden_queries = _filter_golden_queries(golden_queries, restricted_explore_keys)

        # Log the keys in filtered_golden_queries
        if isinstance(filtered_golden_queries, dict):
            logger.info(f"filtered_golden_queries keys: {list(filtered_golden_queries.keys())}")
            if 'exploreEntries' in filtered_golden_queries:
                logger.info(f"filtered_golden_queries['exploreEntries'] count: {len(filtered_golden_queries['exploreEntries'])}")
                logger.info(f"filtered_golden_queries['exploreEntries'] sample: {[e.get('golden_queries.explore_id') for e in filtered_golden_queries['exploreEntries'][:3]]}")
        else:
            logger.info(f"filtered_golden_queries is not a dict: {type(filtered_golden_queries)}")

        # Extract available explores
        available_explores = _extract_available_explores(filtered_golden_queries, restricted_explore_keys)

        logger.info(f"available_explores after extraction: {available_explores}")

        if not available_explores:
            logger.error("❌ No explores available for selection")
            logger.error(f"restricted_explore_keys: {restricted_explore_keys}")
            logger.error(f"filtered_golden_queries: {filtered_golden_queries}")
            raise ExploreNotFoundError("No explores available for selection", available_explores)

        logger.info(f"🔍 Available explores for selection: {available_explores}")

        # Optimization: If only one explore is available, skip LLM call and return it directly
        if len(available_explores) == 1:
            single_explore = available_explores[0]
            logger.info(f"✅ Only one explore available ({single_explore}) - skipping LLM call for efficiency")
            logger.info("=== EXPLORE DETERMINATION COMPLETE (OPTIMIZED) ===")
            return single_explore

        # Use Vertex AI to determine the best explore
        selected_explore = _select_explore_with_ai(prompt, conversation_context, available_explores, 
                                                  filtered_golden_queries, restricted_explore_keys)

        if not selected_explore:
            logger.error("❌ No explore selected by AI")
            raise ExploreNotFoundError("AI could not select an appropriate explore", available_explores)

        logger.info(f"✅ Selected explore: {selected_explore}")
        logger.info("=== EXPLORE DETERMINATION COMPLETE ===")

        return selected_explore

    except ExploreNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Error in explore determination: {e}")
        raise ExploreNotFoundError(f"Explore determination failed: {e}")


def _filter_golden_queries(golden_queries: Dict[str, Any], restricted_explore_keys: List[str] = None) -> Dict[str, Any]:
    """Filter golden queries by restricted explore keys"""
    
    if not restricted_explore_keys:
        return golden_queries

    logger.info(f"Filtering golden queries by restricted keys: {restricted_explore_keys}")
    filtered_golden_queries = {}

    # Lowercase all restricted keys for case-insensitive match
    restricted_keys_lower = set(k.lower() for k in restricted_explore_keys)

    for key, value in golden_queries.items():
        if key == 'exploreEntries':
            # Filter explore entries by restricted keys (case-insensitive)
            filtered_entries = [
                entry for entry in value
                if entry.get('golden_queries.explore_id') and entry.get('golden_queries.explore_id').lower() in restricted_keys_lower
            ]
            filtered_golden_queries[key] = filtered_entries
            logger.info(f"Filtered {key}: {len(filtered_entries)} entries after filtering")
        else:
            # For other keys, filter based on explore keys (case-insensitive)
            if isinstance(value, dict):
                filtered_value = {
                    k: v for k, v in value.items()
                    if k and k.lower() in restricted_keys_lower
                }
                filtered_golden_queries[key] = filtered_value
                logger.info(f"Filtered {key}: {len(filtered_value)} entries after filtering")
            else:
                filtered_golden_queries[key] = value
                logger.info(f"Copied {key} without filtering (not a dict)")

    return filtered_golden_queries


def _extract_available_explores(filtered_golden_queries: Dict[str, Any], restricted_explore_keys: List[str] = None) -> List[str]:
    """Extract available explores from filtered golden queries"""
    
    available_explores = []

    # Lowercase all restricted keys for case-insensitive fallback
    restricted_keys_lower = set(k.lower() for k in restricted_explore_keys) if restricted_explore_keys else set()

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

    # Remove duplicates (case-insensitive) and ensure we have explores to choose from
    # Keep original casing for output, but deduplicate by lowercased value
    seen = set()
    deduped_explores = []
    for ex in available_explores:
        ex_lower = ex.lower() if isinstance(ex, str) else ex
        if ex_lower not in seen:
            seen.add(ex_lower)
            deduped_explores.append(ex)
    available_explores = deduped_explores

    # Fallback to restricted keys if no explores found
    if not available_explores and restricted_explore_keys:
        available_explores = restricted_explore_keys

    return available_explores


def _select_explore_with_ai(prompt: str, conversation_context: str, available_explores: List[str], 
                           filtered_golden_queries: Dict[str, Any], restricted_explore_keys: List[str] = None) -> Optional[str]:
    """Use Vertex AI to select the best explore"""
    
    # Build system prompt
    restriction_text = ""
    if restricted_explore_keys:
        restriction_text = f"\nIMPORTANT: You must only select explores from this restricted list: {restricted_explore_keys}\n"
    
    explores_text = "\n".join([f"- {explore}" for explore in available_explores])
    
    context_text = ""
    if conversation_context:
        context_text = f"\n\nConversation Context:\n{conversation_context}\n"
    
    system_prompt = f"""You are an expert data analyst. Your task is to select the most appropriate Looker explore for answering the user's question.

{restriction_text}

Available explores:
{explores_text}

User's question: {prompt}{context_text}

Instructions:
1. Analyze the user's question to understand what data they need
2. Consider the conversation context if provided
3. Select the explore that would contain the most relevant data
4. Respond with ONLY the explore name (e.g., "ecommerce:order_items")
5. If unsure, select the explore most likely to contain general business metrics

Your response:"""
    
    # Build Vertex AI request
    defaults = get_model_generation_defaults(VERTEX_MODEL)
    vertex_request = {
        "contents": [{
            "role": "user",
            "parts": [{"text": system_prompt}]
        }],
        "generationConfig": {
            "maxOutputTokens": 100,  # Short response expected
            "temperature": defaults["temperature"],
            "topP": defaults["topP"],
            "topK": defaults["topK"]
        }
    }
    
    try:
        # Call Vertex AI
        vertex_response = call_vertex_ai_with_retry(
            vertex_request, 
            context="explore_determination", 
            process_response=False
        )
        
        if not vertex_response:
            logger.error("❌ No response from Vertex AI")
            return None
        
        # Extract response text
        from vertex.response_parser import extract_vertex_response_text
        response_text = extract_vertex_response_text(vertex_response)
        
        if not response_text:
            logger.error("❌ No text extracted from Vertex AI response")
            return None
        
        # Clean up the response
        selected_explore = response_text.strip()
        
        # Validate that the selected explore is in our available list
        if selected_explore not in available_explores:
            logger.warning(f"⚠️ AI selected '{selected_explore}' which is not in available explores")
            # Try to find a partial match
            for explore in available_explores:
                if selected_explore.lower() in explore.lower() or explore.lower() in selected_explore.lower():
                    logger.info(f"✅ Using partial match: {explore}")
                    return explore
            
            # Fallback to first available explore
            logger.warning(f"⚠️ No match found, using first available explore: {available_explores[0]}")
            return available_explores[0]
        
        return selected_explore
        
    except Exception as e:
        logger.error(f"Error calling Vertex AI for explore selection: {e}")
        # Fallback to first available explore
        return available_explores[0] if available_explores else None