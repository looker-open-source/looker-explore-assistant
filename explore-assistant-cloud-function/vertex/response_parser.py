"""
Vertex AI response parsing utilities

Handles response validation, text extraction, and JSON parsing from Vertex AI responses.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import ValidationError

from core.exceptions import TokenLimitExceededException
from core.models import VertexResponse
from llm_utils import parse_llm_response, VertexAIResponse


def extract_vertex_response_text(vertex_response: Dict[str, Any]) -> Optional[str]:
    """
    Extract and parse text from Vertex AI response, with robust validation and JSON parsing.
    Returns parsed object if valid JSON or raw text fallback.
    """
    try:
        logging.info(f"🔍 extract_vertex_response_text - Input keys: {list(vertex_response.keys()) if vertex_response else 'None'}")
        logging.info(f"🔍 extract_vertex_response_text - Input type: {vertex_response}")
        # # extract as string for logs
        # logging.info(f"🔍 extract_vertex_response_text - Input as string: {json.dumps(vertex_response, indent=2) if vertex_response else 'None'}")
        
        # Add proper null and type validation
        if not vertex_response or not isinstance(vertex_response, dict):
            logging.error("❌ Invalid vertex response: None or not a dictionary")
            return None
        
        # Check for MAX_TOKENS or other finish reasons that indicate incomplete responses
        candidates = vertex_response.get('candidates', [])
        if not candidates:
            logging.error("❌ No candidates found in Vertex AI response")
            return None
            
        # Check finish reason
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

        logging.info(f"🔍 Extracted raw text length: {len(raw_text)} characters")

        # Remove markdown code block if present
        text = raw_text.strip()
        if text.startswith('```'):
            lines = text.splitlines()
            # Remove the first line if it's a code block marker
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remove the last line if it's a code block marker
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            text = '\n'.join(lines)
        else:
            text = raw_text

        # Attempt to parse JSON from cleaned text
        try:
            parsed = parse_llm_response(text)
            logging.info(f"🔍 Successfully parsed JSON response")
            return parsed
        except Exception as e:
            logging.warning(f"JSON parsing failed: {e}")
            # Return cleaned text as fallback
            return text
        
    except TokenLimitExceededException:
        # Re-raise TokenLimitExceededException so retry mechanism can catch it
        raise
    except Exception as e:
        logging.error(f"Error extracting Vertex AI response: {e}")
        return None


def parse_vertex_response(response: Dict[str, Any]) -> VertexResponse:
    """Parse and validate Vertex AI response using Pydantic model"""
    try:
        return VertexResponse.parse_obj(response)
    except ValidationError as e:
        logging.error(f"Failed to parse Vertex AI response: {e}")
        raise


def extract_function_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract function calls from Vertex AI response if present"""
    function_calls = []
    
    try:
        candidates = response.get('candidates', [])
        if not candidates:
            return function_calls
            
        content = candidates[0].get('content', {})
        parts = content.get('parts', [])
        
        for part in parts:
            if isinstance(part, dict) and 'functionCall' in part:
                function_calls.append(part['functionCall'])
                
        return function_calls
        
    except Exception as e:
        logging.error(f"Error extracting function calls: {e}")
        return function_calls


def validate_vertex_response(response: Dict[str, Any]) -> bool:
    """Validate that a Vertex AI response has the expected structure"""
    try:
        if not isinstance(response, dict):
            return False
            
        candidates = response.get('candidates')
        if not isinstance(candidates, list) or not candidates:
            return False
            
        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            return False
            
        content = first_candidate.get('content')
        if not isinstance(content, dict):
            return False
            
        parts = content.get('parts')
        if not isinstance(parts, list):
            return False
            
        return True
        
    except Exception as e:
        logging.error(f"Error validating Vertex AI response: {e}")
        return False