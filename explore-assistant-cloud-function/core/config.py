"""
Configuration management for Looker Explore Assistant

Centralizes environment variables, model limits, and default settings.
"""

import os
from typing import Dict, Any


# Environment Configuration
PROJECT = os.environ.get("PROJECT")
REGION = os.environ.get("REGION", "us-central1")
VERTEX_MODEL = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash-001")

# BigQuery Configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
BQ_DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
BQ_SUGGESTED_TABLE = os.environ.get("BQ_SUGGESTED_TABLE", "silver_queries")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

# Looker Configuration
LOOKER_BASE_URL = os.environ.get("LOOKERSDK_BASE_URL", "https://bytecodeef.looker.com")
LOOKER_CLIENT_ID = os.environ.get("LOOKERSDK_CLIENT_ID", "")
LOOKER_CLIENT_SECRET = os.environ.get("LOOKERSDK_CLIENT_SECRET", "")

# Model token limits
MODEL_LIMITS = {
    # Gemini 2.5 Models
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
    
    # Legacy models
    "gemini-1.0-pro": {"input": 32760, "output": 2048},
    "gemini-pro": {"input": 32760, "output": 2048}
}


def get_max_tokens_for_model(model_name: str) -> Dict[str, int]:
    """Get maximum input and output tokens for the specified model"""
    # Extract base model name from full model string
    for model_key in MODEL_LIMITS.keys():
        if model_key in model_name:
            return MODEL_LIMITS[model_key]
    
    # Default fallback
    return {"input": 32760, "output": 3048}


def get_model_generation_defaults(model_name: str) -> Dict[str, Any]:
    """Get default generation parameters for the specified model"""
    return {
        "temperature": 0.2,
        "topP": 0.95,
        "topK": 20,
        "maxOutputTokens": get_max_tokens_for_model(model_name)["output"]
    }


def update_token_warning_thresholds(model_name: str) -> Dict[str, int]:
    """Get token warning thresholds for the specified model"""
    limits = get_max_tokens_for_model(model_name)
    return {
        "warning_threshold": int(limits["input"] * 0.8),  # 80% of input limit
        "critical_threshold": int(limits["input"] * 0.9)  # 90% of input limit
    }


def get_environment_config() -> Dict[str, Any]:
    """Get Flask configuration based on environment"""
    config = {
        # Basic Flask settings
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production"),
        "DEBUG": os.environ.get("FLASK_ENV") == "development",
        "TESTING": False,
        
        # Application settings
        "PROJECT": PROJECT,
        "REGION": REGION,
        "VERTEX_MODEL": VERTEX_MODEL,
        
        # BigQuery settings
        "BQ_PROJECT_ID": BQ_PROJECT_ID,
        "BQ_DATASET_ID": BQ_DATASET_ID,
        "BQ_SUGGESTED_TABLE": BQ_SUGGESTED_TABLE,
        "FIELD_VALUES_TABLE": FIELD_VALUES_TABLE,
        "EMBEDDING_MODEL": EMBEDDING_MODEL,
        
        # Looker settings
        "LOOKER_BASE_URL": LOOKER_BASE_URL,
        "LOOKER_CLIENT_ID": LOOKER_CLIENT_ID,
        "LOOKER_CLIENT_SECRET": LOOKER_CLIENT_SECRET,
        
        # Request settings
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max request size
        "REQUEST_TIMEOUT": 300,  # 5 minutes for AI operations
        
        # JSON settings
        "JSONIFY_PRETTYPRINT_REGULAR": True,
        "JSON_SORT_KEYS": True
    }
    
    # Environment specific overrides
    env = os.environ.get("FLASK_ENV", "production")
    if env == "development":
        config.update({
            "DEBUG": True,
            "JSONIFY_PRETTYPRINT_REGULAR": True
        })
    elif env == "testing":
        config.update({
            "TESTING": True,
            "DEBUG": True,
            "WTF_CSRF_ENABLED": False
        })
    
    return config


def calculate_max_output_tokens(system_prompt: str, model_name: str, task_type: str = "general") -> int:
    """Calculate appropriate output tokens based on task type and model capacity"""
    import logging
    
    model_limits = get_max_tokens_for_model(model_name)
    max_output = model_limits["output"]
    max_input = model_limits["input"]
    
    # Check if this is a thinking model that needs extra buffer
    is_thinking_model = "thinking" in model_name.lower() or "2.5" in model_name.lower()
    
    # Task-specific token limits with thinking model adjustments
    if is_thinking_model:
        # Thinking models need more tokens due to internal reasoning
        task_limits = {
            "explore_selection": 600,      # Extra buffer for thinking process
            "synthesis": 800,              # More room for reasoning
            "explore_params": 6000,        # Increased for complex JSON responses
            "general": max_output // 3     # Conservative but not too restrictive
        }
        logging.info(f"🧠 Using thinking model limits for {model_name}")
    else:
        # Standard models - more generous limits for quality
        task_limits = {
            "explore_selection": 250,      # Just need the explore key
            "synthesis": 500,              # Synthesized query should be concise  
            "explore_params": 6000,        # Increased for complex JSON responses
            "general": max_output // 4     # Conservative default for other tasks
        }
        logging.info(f"📝 Using standard model limits for {model_name}")
    
    # Use task-specific limit, capped by model maximum
    recommended_tokens = min(task_limits.get(task_type, task_limits["general"]), max_output)
    
    # Rough estimate: 1 token ≈ 4 characters for English text
    estimated_prompt_tokens = len(system_prompt) // 4
    
    logging.info(f"📊 Model: {model_name}, Task: {task_type}")
    logging.info(f"📊 Max input tokens: {max_input:,}")
    logging.info(f"📊 Max output tokens: {max_output:,}")
    logging.info(f"📊 Estimated prompt tokens: {estimated_prompt_tokens:,}")
    
    # Only reduce output if prompt is extremely large (>90% of input limit)
    if estimated_prompt_tokens > max_input * 0.9:
        logging.warning(f"⚠️ Prompt approaching input token limit ({estimated_prompt_tokens:,} / {max_input:,})")
        minimum_safe = 300 if is_thinking_model else 150
        return max(recommended_tokens // 4, minimum_safe)  # Emergency fallback
    else:
        # Use task-appropriate tokens instead of maximum
        logging.info(f"📊 Using task-appropriate tokens: {recommended_tokens:,} (task: {task_type})")
        return recommended_tokens