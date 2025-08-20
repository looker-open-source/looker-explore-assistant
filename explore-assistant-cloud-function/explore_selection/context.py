"""
Conversation context synthesis

Handles conversation context processing and synthesis for better
explore selection and parameter generation.
"""

import logging
from typing import Optional

from vertex.client import call_vertex_ai_with_retry
from vertex.response_parser import extract_vertex_response_text
from core.config import get_model_generation_defaults, VERTEX_MODEL

# Import from migrated core module
from core.config import calculate_max_output_tokens

logger = logging.getLogger(__name__)


def synthesize_conversation_context(auth_header: str, current_prompt: str, conversation_context: str) -> Optional[str]:
    """First LLM call: Synthesize conversation history and current prompt into a clear, standalone query"""
    try:
        logger.info("=== SYNTHESIS STEP ===")
        logger.info(f"Current prompt: {current_prompt}")
        logger.info(f"Conversation context: {conversation_context}")
        
        # If there's no conversation context, just return the original prompt
        if not conversation_context or conversation_context.strip() == "":
            logger.info("No conversation context, returning original prompt")
            return current_prompt
        
        # Monitor conversation context size to prevent token overflow
        if len(conversation_context) > 2000:
            logger.warning(f"⚠️ Large conversation context ({len(conversation_context)} chars) - truncating to prevent token issues")
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

        logger.info(f"🔍 Synthesis prompt size: ~{len(synthesis_prompt)} characters")

        # Format request for Vertex AI with task-appropriate tokens
        max_tokens = calculate_max_output_tokens(synthesis_prompt, VERTEX_MODEL, "synthesis")
        defaults = get_model_generation_defaults(VERTEX_MODEL)
        
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
                "temperature": defaults["temperature"],
                "topP": defaults["topP"],
                "topK": defaults["topK"],
                "maxOutputTokens": max_tokens,
                "responseMimeType": "text/plain",
                "candidateCount": 1
            }
        }
        
        # Log concise request summary for debugging
        logger.info(f"🤖 LLM Request - Conversation Synthesis | Current: '{current_prompt[:80]}{'...' if len(current_prompt) > 80 else ''}' | "
                    f"Context: {len(conversation_context)} chars | "
                    f"Prompt: {len(synthesis_prompt):,} chars | MaxTokens: {max_tokens}")
        
        # Call Vertex AI using service account with retry logic
        vertex_response = call_vertex_ai_with_retry(vertex_request, "conversation_synthesis")
        if not vertex_response:
            logger.warning("❌ SYNTHESIS: No response from Vertex AI after retries, using original prompt")
            return current_prompt
        
        logger.info(f"🔍 SYNTHESIS: Got Vertex AI response: {vertex_response}")
        
        # Extract the synthesized query
        synthesized_query = extract_vertex_response_text(vertex_response)
        logger.info(f"🔍 SYNTHESIS: Extracted text: '{synthesized_query}' (type: {type(synthesized_query)})")
        
        if synthesized_query:
            # Handle different response types
            if isinstance(synthesized_query, dict):
                logger.warning(f"❌ SYNTHESIS: Response is dict, trying to extract text: {synthesized_query}")
                # Try to find text in common fields
                if 'text' in synthesized_query:
                    synthesized_query = str(synthesized_query['text'])
                elif 'content' in synthesized_query:
                    synthesized_query = str(synthesized_query['content'])
                elif 'query' in synthesized_query:
                    synthesized_query = str(synthesized_query['query'])
                else:
                    logger.warning("❌ SYNTHESIS: Cannot extract text from dict, using original prompt")
                    return current_prompt
            elif isinstance(synthesized_query, list):
                logger.warning(f"❌ SYNTHESIS: Response is list, taking first element: {synthesized_query}")
                if synthesized_query and isinstance(synthesized_query[0], str):
                    synthesized_query = synthesized_query[0]
                else:
                    logger.warning("❌ SYNTHESIS: Cannot extract text from list, using original prompt")
                    return current_prompt
            
            synthesized_query = str(synthesized_query).strip()
            
            # Validate that we got a meaningful synthesis
            if not synthesized_query or synthesized_query.lower() in ['none', 'null', 'undefined']:
                logger.warning("❌ SYNTHESIS: Got empty or invalid result, using original prompt")
                return current_prompt
            
            logger.info("=== SYNTHESIS RESULT ===")
            logger.info(f"✅ Synthesized query: {synthesized_query}")
            return synthesized_query
        
        logger.warning("❌ SYNTHESIS: Failed to extract synthesized query from Vertex AI response")
        logger.warning(f"❌ SYNTHESIS: Falling back to original prompt: '{current_prompt}'")
        return current_prompt
        
    except Exception as e:
        logger.error(f"Error synthesizing conversation context: {e}")
        return None


def build_conversation_context(prompt_history: list, thread_messages: list) -> str:
    """
    Build conversation context from prompt history and thread messages
    
    Args:
        prompt_history: List of previous prompts
        thread_messages: List of thread messages
        
    Returns:
        Formatted conversation context string
    """
    context_parts = []
    
    # Add prompt history
    if prompt_history:
        context_parts.append("Previous prompts:")
        for i, prompt in enumerate(prompt_history[-3:]):  # Last 3 prompts
            context_parts.append(f"{i+1}. {prompt}")
    
    # Add thread messages
    if thread_messages:
        context_parts.append("\\nThread messages:")
        for msg in thread_messages[-5:]:  # Last 5 messages
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if content:
                    context_parts.append(f"{role}: {content[:200]}...")  # Truncate long messages
            elif isinstance(msg, str):
                context_parts.append(f"message: {msg[:200]}...")
    
    return "\\n".join(context_parts)


def extract_approved_explore_params(thread_messages: list) -> Optional[dict]:
    """
    Extract approved explore parameters from thread messages
    
    Args:
        thread_messages: List of thread messages
        
    Returns:
        Dictionary of approved parameters or None
    """
    try:
        # Look for messages containing approved parameters
        for msg in reversed(thread_messages):  # Start from most recent
            if isinstance(msg, dict):
                content = msg.get('content', '')
                if 'approved' in content.lower() and 'parameters' in content.lower():
                    # Try to extract parameters from the message
                    # This would need more sophisticated parsing in practice
                    logger.info("Found approved parameters in thread message")
                    # For now, return None - this would need implementation based on message format
                    return None
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting approved explore params: {e}")
        return None