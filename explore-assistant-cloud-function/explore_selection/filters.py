"""
Explore filtering utilities

Provides utilities for filtering golden queries and semantic models
by allowed explore keys.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def filter_golden_queries_by_explores(golden_queries: Dict[str, Any], allowed_explore_keys: List[str]) -> Dict[str, Any]:
    """
    Filter golden queries to only include data for allowed explore keys
    
    Args:
        golden_queries: Dictionary of golden query data
        allowed_explore_keys: List of explore keys to keep (format: 'model:explore')
        
    Returns:
        Filtered golden queries dictionary
    """
    if not allowed_explore_keys:
        return golden_queries
    
    logger.info(f"Filtering golden queries for explores: {allowed_explore_keys}")
    
    filtered = {}
    
    for key, value in golden_queries.items():
        if key == 'exploreEntries':
            # Filter explore entries
            if isinstance(value, list):
                filtered_entries = [
                    entry for entry in value 
                    if isinstance(entry, dict) and 
                    (entry.get('golden_queries.explore_id') in allowed_explore_keys or 
                     entry.get('explore_id') in allowed_explore_keys)
                ]
                filtered[key] = filtered_entries
                logger.info(f"Filtered {key}: {len(filtered_entries)}/{len(value)} entries kept")
            else:
                filtered[key] = value
                
        elif key in ['exploreGenerationExamples', 'exploreRefinementExamples', 'exploreSamples']:
            # Filter explore-based examples
            if isinstance(value, dict):
                filtered_examples = {
                    explore_key: examples for explore_key, examples in value.items()
                    if explore_key in allowed_explore_keys
                }
                filtered[key] = filtered_examples
                logger.info(f"Filtered {key}: {len(filtered_examples)}/{len(value)} explores kept")
            else:
                filtered[key] = value
                
        else:
            # Keep other keys as-is
            filtered[key] = value
            logger.info(f"Kept {key} unchanged")
    
    return filtered


def filter_semantic_models_by_explores(semantic_models: Dict[str, Any], allowed_explore_keys: List[str]) -> Dict[str, Any]:
    """
    Filter semantic models to only include data for allowed explore keys
    
    Args:
        semantic_models: Dictionary of semantic model data
        allowed_explore_keys: List of explore keys to keep
        
    Returns:
        Filtered semantic models dictionary
    """
    if not allowed_explore_keys:
        return semantic_models
    
    logger.info(f"Filtering semantic models for explores: {allowed_explore_keys}")
    
    filtered = {
        explore_key: model_data for explore_key, model_data in semantic_models.items()
        if explore_key in allowed_explore_keys
    }
    
    logger.info(f"Filtered semantic models: {len(filtered)}/{len(semantic_models)} models kept")
    
    return filtered


def extract_explore_keys_from_golden_queries(golden_queries: Dict[str, Any]) -> List[str]:
    """
    Extract all unique explore keys from golden queries
    
    Args:
        golden_queries: Dictionary of golden query data
        
    Returns:
        List of unique explore keys found
    """
    explore_keys = set()
    
    # Extract from exploreEntries
    if 'exploreEntries' in golden_queries:
        entries = golden_queries['exploreEntries']
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    explore_id = (entry.get('golden_queries.explore_id') or 
                                entry.get('explore_id'))
                    if explore_id:
                        explore_keys.add(explore_id)
    
    # Extract from example sections
    for key in ['exploreGenerationExamples', 'exploreRefinementExamples', 'exploreSamples']:
        if key in golden_queries and isinstance(golden_queries[key], dict):
            explore_keys.update(golden_queries[key].keys())
    
    return list(explore_keys)


def validate_explore_keys_format(explore_keys: List[str]) -> List[str]:
    """
    Validate and normalize explore key formats
    
    Args:
        explore_keys: List of explore keys to validate
        
    Returns:
        List of valid explore keys in 'model:explore' format
    """
    valid_keys = []
    
    for key in explore_keys:
        if not isinstance(key, str):
            logger.warning(f"Invalid explore key type: {type(key)} - {key}")
            continue
        
        if ':' not in key:
            logger.warning(f"Invalid explore key format (missing ':'): {key}")
            continue
        
        parts = key.split(':')
        if len(parts) != 2:
            logger.warning(f"Invalid explore key format (too many parts): {key}")
            continue
        
        model_name, explore_name = parts
        if not model_name.strip() or not explore_name.strip():
            logger.warning(f"Invalid explore key format (empty parts): {key}")
            continue
        
        valid_keys.append(key.strip())
    
    return valid_keys


def get_explore_statistics(golden_queries: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get statistics about explores in golden queries
    
    Args:
        golden_queries: Dictionary of golden query data
        
    Returns:
        Dictionary containing explore statistics
    """
    stats = {
        "total_explores": 0,
        "explores_with_examples": 0,
        "total_examples": 0,
        "explore_breakdown": {}
    }
    
    explore_keys = extract_explore_keys_from_golden_queries(golden_queries)
    stats["total_explores"] = len(explore_keys)
    
    # Count examples per explore
    for key in ['exploreGenerationExamples', 'exploreRefinementExamples', 'exploreSamples']:
        if key in golden_queries and isinstance(golden_queries[key], dict):
            for explore_key, examples in golden_queries[key].items():
                if explore_key not in stats["explore_breakdown"]:
                    stats["explore_breakdown"][explore_key] = 0
                
                example_count = len(examples) if isinstance(examples, (list, dict)) else 1
                stats["explore_breakdown"][explore_key] += example_count
                stats["total_examples"] += example_count
    
    stats["explores_with_examples"] = len(stats["explore_breakdown"])
    
    return stats