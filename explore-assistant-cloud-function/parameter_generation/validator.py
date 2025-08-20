"""
Parameter validation and formatting

Validates and formats explore parameters for Looker API compatibility.
"""

import logging
from typing import Dict, Any, List, Optional

from core.models import QueryParameters
from core.exceptions import ParameterGenerationError

logger = logging.getLogger(__name__)


def validate_explore_parameters(params: Dict[str, Any], explore_key: str) -> Dict[str, Any]:
    """
    Validate explore parameters for correctness and completeness
    
    Args:
        params: Raw parameters from AI generation
        explore_key: Target explore key for validation context
        
    Returns:
        Validated parameters dictionary
        
    Raises:
        ParameterGenerationError: If validation fails
    """
    try:
        logger.info(f"🔍 Validating parameters for {explore_key}")
        
        validated = {}
        
        # Extract model and explore names from key
        if ':' in explore_key:
            model_name, explore_name = explore_key.split(':', 1)
        else:
            model_name = "unknown"
            explore_name = explore_key
        
        # Validate and set required fields
        validated["model"] = params.get("model", model_name)
        validated["view"] = params.get("view", explore_name)
        
        # Validate fields array
        fields = params.get("fields", [])
        if not isinstance(fields, list):
            logger.warning(f"⚠️ Fields is not a list, converting: {type(fields)}")
            fields = [fields] if fields else []
        
        # Clean and validate field names
        validated_fields = []
        for field in fields:
            if isinstance(field, str) and field.strip():
                validated_fields.append(field.strip())
            else:
                logger.warning(f"⚠️ Invalid field skipped: {field}")
        
        validated["fields"] = validated_fields
        
        # Validate filters dictionary
        filters = params.get("filters", {})
        if not isinstance(filters, dict):
            logger.warning(f"⚠️ Filters is not a dict, converting: {type(filters)}")
            filters = {}
        
        # Clean filter values
        validated_filters = {}
        for key, value in filters.items():
            if isinstance(key, str) and key.strip():
                # Convert value to string for Looker API
                validated_filters[key.strip()] = str(value) if value is not None else ""
        
        validated["filters"] = validated_filters
        
        # Validate sorts array
        sorts = params.get("sorts", [])
        if not isinstance(sorts, list):
            logger.warning(f"⚠️ Sorts is not a list, converting: {type(sorts)}")
            sorts = [sorts] if sorts else []
        
        validated_sorts = []
        for sort in sorts:
            if isinstance(sort, str) and sort.strip():
                validated_sorts.append(sort.strip())
        
        validated["sorts"] = validated_sorts
        
        # Validate pivots array
        pivots = params.get("pivots", [])
        if not isinstance(pivots, list):
            pivots = [pivots] if pivots else []
        
        validated_pivots = []
        for pivot in pivots:
            if isinstance(pivot, str) and pivot.strip():
                validated_pivots.append(pivot.strip())
        
        validated["pivots"] = validated_pivots
        
        # Validate limit
        limit = params.get("limit", 500)
        try:
            limit = int(limit)
            if limit <= 0:
                limit = 500
            elif limit > 5000:  # Reasonable upper bound
                limit = 5000
        except (ValueError, TypeError):
            limit = 500
        
        validated["limit"] = limit
        
        # Validation checks
        validation_warnings = []
        
        if not validated_fields:
            validation_warnings.append("No fields specified - query may return no data")
        
        if len(validated_fields) > 20:
            validation_warnings.append(f"Many fields selected ({len(validated_fields)}) - query may be slow")
        
        if len(validated_filters) > 10:
            validation_warnings.append(f"Many filters applied ({len(validated_filters)}) - query may be overly restrictive")
        
        # Log validation results
        if validation_warnings:
            for warning in validation_warnings:
                logger.warning(f"⚠️ Validation: {warning}")
        
        logger.info(f"✅ Parameters validated: {len(validated_fields)} fields, {len(validated_filters)} filters")
        
        return validated
        
    except Exception as e:
        logger.error(f"Parameter validation failed: {e}")
        raise ParameterGenerationError(f"Parameter validation failed: {e}", explore_key)


def format_parameters_for_looker(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format parameters for Looker inline query API compatibility
    
    Args:
        params: Validated parameters
        
    Returns:
        Looker API compatible parameters
    """
    try:
        # Ensure all required fields are present
        formatted = {
            "model": params.get("model", ""),
            "view": params.get("view", ""),
            "fields": params.get("fields", []),
            "filters": params.get("filters", {}),
            "limit": params.get("limit", 500)
        }
        
        # Add optional fields only if they have values
        if params.get("sorts"):
            formatted["sorts"] = params["sorts"]
        
        if params.get("pivots"):
            formatted["pivots"] = params["pivots"]
        
        # Additional Looker API specific formatting
        if params.get("row_total"):
            formatted["row_total"] = bool(params["row_total"])
        
        if params.get("subtotals"):
            formatted["subtotals"] = params["subtotals"]
        
        if params.get("total"):
            formatted["total"] = bool(params["total"])
        
        return formatted
        
    except Exception as e:
        logger.error(f"Parameter formatting failed: {e}")
        raise ParameterGenerationError(f"Parameter formatting failed: {e}")


def create_query_parameters_model(params: Dict[str, Any]) -> QueryParameters:
    """
    Create QueryParameters model from parameter dictionary
    
    Args:
        params: Parameter dictionary
        
    Returns:
        QueryParameters model instance
    """
    try:
        return QueryParameters(
            model=params.get("model", ""),
            view=params.get("view", ""),
            fields=params.get("fields", []),
            filters=params.get("filters", {}),
            sorts=params.get("sorts", []),
            pivots=params.get("pivots", []),
            limit=params.get("limit", 500)
        )
    except Exception as e:
        logger.error(f"Failed to create QueryParameters model: {e}")
        raise ParameterGenerationError(f"Failed to create QueryParameters model: {e}")


def validate_field_references(fields: List[str], available_fields: List[Dict[str, Any]]) -> List[str]:
    """
    Validate that field references exist in available fields
    
    Args:
        fields: List of field references to validate
        available_fields: List of available field metadata
        
    Returns:
        List of valid field references
    """
    if not available_fields:
        return fields  # Skip validation if no field metadata available
    
    # Create lookup of available field names
    field_lookup = set()
    for field in available_fields:
        if isinstance(field, dict):
            name = field.get('name', '')
            if name:
                field_lookup.add(name)
                # Also add view.field format if view is available
                view = field.get('view', '')
                if view:
                    field_lookup.add(f"{view}.{name}")
    
    # Validate requested fields
    valid_fields = []
    for field in fields:
        if field in field_lookup:
            valid_fields.append(field)
        else:
            # Try partial matching
            found_match = False
            for available_field in field_lookup:
                if field.lower() in available_field.lower() or available_field.lower() in field.lower():
                    valid_fields.append(available_field)
                    logger.info(f"🔄 Field '{field}' matched to '{available_field}'")
                    found_match = True
                    break
            
            if not found_match:
                logger.warning(f"⚠️ Field '{field}' not found in available fields")
    
    return valid_fields


def estimate_query_complexity(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate query complexity for performance planning
    
    Args:
        params: Query parameters
        
    Returns:
        Dictionary with complexity metrics
    """
    complexity = {
        "score": 0,
        "level": "simple",
        "factors": [],
        "recommendations": []
    }
    
    # Field count factor
    field_count = len(params.get("fields", []))
    if field_count > 15:
        complexity["score"] += 3
        complexity["factors"].append(f"High field count: {field_count}")
    elif field_count > 8:
        complexity["score"] += 2
        complexity["factors"].append(f"Moderate field count: {field_count}")
    
    # Filter count factor
    filter_count = len(params.get("filters", {}))
    if filter_count > 5:
        complexity["score"] += 2
        complexity["factors"].append(f"Many filters: {filter_count}")
    
    # Pivot factor
    pivot_count = len(params.get("pivots", []))
    if pivot_count > 0:
        complexity["score"] += 3
        complexity["factors"].append(f"Pivots used: {pivot_count}")
    
    # Limit factor
    limit = params.get("limit", 500)
    if limit > 2000:
        complexity["score"] += 2
        complexity["factors"].append(f"Large limit: {limit}")
    
    # Determine complexity level
    if complexity["score"] >= 6:
        complexity["level"] = "complex"
        complexity["recommendations"].append("Consider reducing fields or adding more specific filters")
    elif complexity["score"] >= 3:
        complexity["level"] = "moderate"
        complexity["recommendations"].append("Query should perform reasonably well")
    else:
        complexity["level"] = "simple"
        complexity["recommendations"].append("Query should execute quickly")
    
    return complexity