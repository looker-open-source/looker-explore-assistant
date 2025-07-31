# Utility functions for robust parsing of LLM responses
import json5  # type: ignore
import json
import logging
import demjson3  # type: ignore
from pydantic import BaseModel, ValidationError
from typing import Any, Dict, List, Optional


def parse_llm_response(raw: Any) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse a raw LLM response which may be a string or dict,
    using json5 for flexible parsing, falling back to json.
    """
    if isinstance(raw, str):
        # First, try lenient decode with demjson3 (auto-repairs common JSON errors)
        try:
            decoded = demjson3.decode(raw)
            if isinstance(decoded, (dict, list)):
                return decoded
        except Exception as e:
            logging.warning(f"demjson3 decode failed: {e}")
        # Fallback: try flexible JSON parsing
        try:
            return json5.loads(raw)
        except Exception as e:
            logging.warning(f"json5 parsing failed, trying json.loads: {e}")
            try:
                return json.loads(raw)
            except Exception as err:
                logging.warning(f"json parsing failed: {err}")
                return None
    elif isinstance(raw, dict):
        return raw
    else:
        logging.warning(f"Unexpected LLM response type: {type(raw)}")
        return None


class VertexAIResponse(BaseModel):
    candidates: List[Dict[str, Any]]

    class Config:
        extra = 'ignore'  # ignore unexpected fields
