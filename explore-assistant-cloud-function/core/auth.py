"""
Authentication utilities for the Looker Explore Assistant

Handles JWT token parsing and user information extraction.
"""

import json
import base64
import logging
from typing import Dict, Optional


def get_response_headers() -> Dict[str, str]:
    """Get standard CORS response headers"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS, GET",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
        "Access-Control-Max-Age": "3600",
        "Access-Control-Allow-Credentials": "false"
    }


def extract_user_info_from_token(bearer_token: str) -> Dict[str, Optional[str]]:
    """Extract user information (email, sub, name, etc.) from JWT token without validation"""
    try:
        logging.info("Extracting user info from token")
        
        # Add proper null and type checks
        if not bearer_token or not isinstance(bearer_token, str):
            logging.error("Invalid bearer token: token is None or not a string")
            return {"email": None, "user_id": None, "name": None}
        
        # Remove 'Bearer ' prefix if present - with safe string operations
        bearer_token_lower = bearer_token.lower()
        if bearer_token_lower.startswith('bearer '):
            bearer_token = bearer_token[7:]
        
        # Remove any whitespace
        bearer_token = bearer_token.strip()
        
        # Check if token is empty after processing
        if not bearer_token:
            logging.error("Invalid bearer token: empty token after processing")
            return {"email": None, "user_id": None, "name": None}
        
        # Split JWT into parts
        token_parts = bearer_token.split('.')
        if len(token_parts) != 3:
            logging.error(f"Invalid JWT format: expected 3 parts, got {len(token_parts)}")
            return {"email": None, "user_id": None, "name": None}
        
        # Decode the payload (second part) to extract user info
        payload_data = token_parts[1]
        
        # Validate payload data exists
        if not payload_data:
            logging.error("Invalid JWT format: empty payload section")
            return {"email": None, "user_id": None, "name": None}
            
        # Add padding if needed for base64 decoding
        payload_data += '=' * (4 - len(payload_data) % 4)
        
        try:
            payload_json = base64.urlsafe_b64decode(payload_data).decode('utf-8')
            payload = json.loads(payload_json)
            
            # Ensure payload is a dictionary
            if not isinstance(payload, dict):
                logging.error("Invalid JWT payload: not a JSON object")
                return {"email": None, "user_id": None, "name": None}
            
            # Extract user information from various possible fields
            email = payload.get('email')
            user_id = payload.get('sub') or payload.get('user_id') or payload.get('id') or email
            name = payload.get('name') or payload.get('given_name') or payload.get('display_name')
            
            user_info = {
                "email": email if isinstance(email, str) else None,
                "user_id": user_id if isinstance(user_id, str) else None,
                "name": name if isinstance(name, str) else None,
                "raw_payload": payload  # For debugging
            }
            
            logging.info(f"Extracted user info - Email: {user_info['email']}, User ID: {user_info['user_id']}, Name: {user_info['name']}")
            return user_info
                
        except Exception as e:
            logging.error(f"Failed to decode JWT payload: {e}")
            return {"email": None, "user_id": None, "name": None}
        
    except Exception as e:
        logging.error(f"Failed to extract user info from token: {e}")
        return {"email": None, "user_id": None, "name": None}


def extract_user_email_from_token(bearer_token: str) -> Optional[str]:
    """Extract user email from JWT token without validation (infrastructure handles auth)"""
    user_info = extract_user_info_from_token(bearer_token)
    return user_info.get("email")