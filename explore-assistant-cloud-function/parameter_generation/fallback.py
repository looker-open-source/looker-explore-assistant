"""
Fallback parameter generation

Provides fallback strategies when AI-powered parameter generation fails.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def create_context_aware_fallback(prompt: str, explore_key: str, conversation_context: str, 
                                 semantic_models: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create context-aware fallback parameters when AI generation fails
    
    Args:
        prompt: User's original prompt
        explore_key: Target explore key
        conversation_context: Conversation context
        semantic_models: Available semantic models
        
    Returns:
        Fallback parameter dictionary
    """
    logger.info(f"🔄 Creating context-aware fallback for {explore_key}")
    
    # Extract model and explore names
    if ':' in explore_key:
        model_name, explore_name = explore_key.split(':', 1)
    else:
        model_name = "unknown"
        explore_name = explore_key
    
    # Get semantic model for field suggestions
    semantic_model = semantic_models.get(explore_key, {})
    
    # Build basic fallback parameters
    fallback_params = {
        "model": model_name,
        "view": explore_name,
        "fields": _suggest_basic_fields(semantic_model, prompt),
        "filters": _suggest_basic_filters(semantic_model, prompt, conversation_context),
        "sorts": _suggest_basic_sorts(semantic_model),
        "pivots": [],
        "limit": 500
    }
    
    logger.info(f"✅ Created fallback with {len(fallback_params['fields'])} fields, {len(fallback_params['filters'])} filters")
    
    return fallback_params


def _suggest_basic_fields(semantic_model: Dict[str, Any], prompt: str) -> List[str]:
    """Suggest basic fields based on semantic model and prompt"""
    
    suggested_fields = []
    
    if not semantic_model:
        logger.warning("No semantic model available, using generic fallback fields")
        return ["*"]  # Generic fallback
    
    dimensions = semantic_model.get('dimensions', [])
    measures = semantic_model.get('measures', [])
    
    # Always include some basic dimensions if available
    basic_dimension_patterns = ['name', 'id', 'date', 'time', 'status', 'type', 'category']
    
    for dim in dimensions[:5]:  # Top 5 dimensions
        dim_name = dim.get('name', '').lower()
        for pattern in basic_dimension_patterns:
            if pattern in dim_name:
                suggested_fields.append(dim.get('name', ''))
                break
    
    # Include measures that seem relevant to the prompt
    prompt_lower = prompt.lower()
    measure_keywords = {
        'count': ['count', 'total', 'number'],
        'sum': ['sum', 'total', 'amount'],
        'avg': ['average', 'avg', 'mean'],
        'revenue': ['revenue', 'sales', 'income'],
        'profit': ['profit', 'margin'],
        'cost': ['cost', 'expense']
    }
    
    for measure in measures[:3]:  # Top 3 measures
        measure_name = measure.get('name', '').lower()
        for keyword_type, keywords in measure_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                if keyword_type in measure_name or any(kw in measure_name for kw in keywords):
                    suggested_fields.append(measure.get('name', ''))
                    break
    
    # If no fields suggested, use first few available
    if not suggested_fields:
        for dim in dimensions[:3]:
            if dim.get('name'):
                suggested_fields.append(dim.get('name'))
        
        for measure in measures[:2]:
            if measure.get('name'):
                suggested_fields.append(measure.get('name'))
    
    return suggested_fields[:10]  # Limit to 10 fields


def _suggest_basic_filters(semantic_model: Dict[str, Any], prompt: str, 
                          conversation_context: str) -> Dict[str, str]:
    """Suggest basic filters based on context"""
    
    filters = {}
    
    if not semantic_model:
        return filters
    
    # Look for common filter patterns in prompt and context
    full_context = f"{prompt} {conversation_context}".lower()
    
    # Common date filters
    if any(term in full_context for term in ['last year', '2024', '2023', 'this year']):
        # Find date fields
        dimensions = semantic_model.get('dimensions', [])
        for dim in dimensions:
            dim_name = dim.get('name', '').lower()
            if 'date' in dim_name or 'time' in dim_name:
                if 'last year' in full_context:
                    filters[dim.get('name', '')] = "1 year ago for 1 year"
                elif '2024' in full_context:
                    filters[dim.get('name', '')] = "2024"
                elif '2023' in full_context:
                    filters[dim.get('name', '')] = "2023"
                break
    
    # Look for status filters
    if any(term in full_context for term in ['active', 'pending', 'complete', 'cancelled']):
        dimensions = semantic_model.get('dimensions', [])
        for dim in dimensions:
            dim_name = dim.get('name', '').lower()
            if 'status' in dim_name or 'state' in dim_name:
                if 'active' in full_context:
                    filters[dim.get('name', '')] = "active"
                elif 'pending' in full_context:
                    filters[dim.get('name', '')] = "pending"
                break
    
    return filters


def _suggest_basic_sorts(semantic_model: Dict[str, Any]) -> List[str]:
    """Suggest basic sorting based on common patterns"""
    
    sorts = []
    
    if not semantic_model:
        return sorts
    
    dimensions = semantic_model.get('dimensions', [])
    measures = semantic_model.get('measures', [])
    
    # Look for date fields to sort by (most recent first)
    for dim in dimensions:
        dim_name = dim.get('name', '').lower()
        if 'date' in dim_name or 'time' in dim_name:
            sorts.append(f"{dim.get('name', '')} desc")
            break
    
    # Look for measures to sort by (highest first)
    for measure in measures[:1]:  # Just one measure sort
        if measure.get('name'):
            sorts.append(f"{measure.get('name')} desc")
            break
    
    return sorts


def create_minimal_fallback(explore_key: str) -> Dict[str, Any]:
    """
    Create minimal fallback when no context is available
    
    Args:
        explore_key: Target explore key
        
    Returns:
        Minimal parameter dictionary
    """
    logger.info(f"🔄 Creating minimal fallback for {explore_key}")
    
    # Extract model and explore names
    if ':' in explore_key:
        model_name, explore_name = explore_key.split(':', 1)
    else:
        model_name = "unknown"
        explore_name = explore_key
    
    return {
        "model": model_name,
        "view": explore_name,
        "fields": [],  # No fields - will need to be filled in
        "filters": {},
        "sorts": [],
        "pivots": [],
        "limit": 500
    }


def enhance_fallback_with_common_patterns(params: Dict[str, Any], explore_key: str) -> Dict[str, Any]:
    """
    Enhance fallback parameters with common query patterns
    
    Args:
        params: Basic fallback parameters
        explore_key: Target explore key
        
    Returns:
        Enhanced parameter dictionary
    """
    enhanced = params.copy()
    
    # Add common fields based on explore name patterns
    explore_name = explore_key.split(':')[-1].lower() if ':' in explore_key else explore_key.lower()
    
    common_fields = []
    
    # E-commerce patterns
    if any(term in explore_name for term in ['order', 'sale', 'purchase', 'transaction']):
        common_fields.extend(['order_items.created_date', 'order_items.sale_price', 'products.brand'])
    
    # User/customer patterns  
    elif any(term in explore_name for term in ['user', 'customer', 'account']):
        common_fields.extend(['users.created_date', 'users.email', 'users.state'])
    
    # Event patterns
    elif 'event' in explore_name:
        common_fields.extend(['events.created_date', 'events.event_type', 'events.user_id'])
    
    # If no fields suggested, add the common fields
    if not enhanced.get('fields'):
        enhanced['fields'] = common_fields[:5]  # Limit to 5
    
    # Add basic date filter if none present
    if not enhanced.get('filters') and common_fields:
        date_field = next((f for f in common_fields if 'date' in f.lower()), None)
        if date_field:
            enhanced['filters'] = {date_field: "30 days"}
    
    return enhanced


def generate_fallback_explanation(params: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """
    Generate explanation for why fallback was used
    
    Args:
        params: Fallback parameters
        reason: Reason for fallback
        
    Returns:
        Dictionary with explanation and suggestions
    """
    return {
        "fallback_used": True,
        "fallback_reason": reason,
        "parameters": params,
        "suggestions": [
            "Try rephrasing your query with more specific requirements",
            "Specify which fields or metrics you're interested in",
            "Add time ranges or filters to narrow your request",
            "Check if the explore name is correct"
        ],
        "next_steps": [
            "Review the generated parameters",
            "Modify fields and filters as needed",
            "Run the query to see initial results",
            "Refine based on the output"
        ]
    }