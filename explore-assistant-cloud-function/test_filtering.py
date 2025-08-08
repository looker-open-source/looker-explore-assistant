#!/usr/bin/env python3
"""
Test script for the golden queries and semantic models filtering functions
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mcp_server import filter_golden_queries_by_explores, filter_semantic_models_by_explores

def test_golden_queries_filtering():
    print("=== Testing Golden Queries Filtering ===")
    
    # Mock golden queries data
    golden_queries = {
        'exploreEntries': [
            {'explore_id': 'ecommerce:order_items'},
            {'explore_id': 'finance:transactions'},
            {'explore_id': 'marketing:campaigns'}
        ],
        'exploreGenerationExamples': {
            'ecommerce:order_items': [
                {'input': 'Show me orders', 'output': 'params1'},
                {'input': 'Total sales', 'output': 'params2'}
            ],
            'finance:transactions': [
                {'input': 'Monthly revenue', 'output': 'params3'}
            ],
            'marketing:campaigns': [
                {'input': 'Campaign performance', 'output': 'params4'}
            ]
        },
        'exploreRefinementExamples': {
            'ecommerce:order_items': [{'input': 'refine1', 'output': 'ref1'}],
            'finance:transactions': [{'input': 'refine2', 'output': 'ref2'}]
        },
        'exploreSamples': {
            'ecommerce:order_items': [{'sample': 'data1'}],
            'marketing:campaigns': [{'sample': 'data2'}]
        }
    }
    
    # Test filtering to just ecommerce
    restricted_keys = ['ecommerce:order_items']
    filtered = filter_golden_queries_by_explores(golden_queries, restricted_keys)
    
    print(f"Original exploreGenerationExamples keys: {list(golden_queries['exploreGenerationExamples'].keys())}")
    print(f"Filtered exploreGenerationExamples keys: {list(filtered['exploreGenerationExamples'].keys())}")
    
    # Verify filtering worked
    assert 'ecommerce:order_items' in filtered['exploreGenerationExamples']
    assert 'finance:transactions' not in filtered['exploreGenerationExamples']
    assert 'marketing:campaigns' not in filtered['exploreGenerationExamples']
    
    # Test with no restrictions
    unfiltered = filter_golden_queries_by_explores(golden_queries, [])
    assert len(unfiltered['exploreGenerationExamples']) == 3
    
    print("✅ Golden queries filtering tests passed!")

def test_semantic_models_filtering():
    print("\n=== Testing Semantic Models Filtering ===")
    
    # Mock semantic models data
    semantic_models = {
        'ecommerce:order_items': {
            'dimensions': [{'name': 'order_date'}, {'name': 'customer_id'}],
            'measures': [{'name': 'total_sales'}, {'name': 'order_count'}]
        },
        'finance:transactions': {
            'dimensions': [{'name': 'transaction_date'}],
            'measures': [{'name': 'revenue'}]
        },
        'marketing:campaigns': {
            'dimensions': [{'name': 'campaign_name'}],
            'measures': [{'name': 'impressions'}]
        }
    }
    
    # Test filtering to just ecommerce and marketing
    restricted_keys = ['ecommerce:order_items', 'marketing:campaigns']
    filtered = filter_semantic_models_by_explores(semantic_models, restricted_keys)
    
    print(f"Original semantic models keys: {list(semantic_models.keys())}")
    print(f"Filtered semantic models keys: {list(filtered.keys())}")
    
    # Verify filtering worked
    assert 'ecommerce:order_items' in filtered
    assert 'marketing:campaigns' in filtered
    assert 'finance:transactions' not in filtered
    
    # Test with no restrictions
    unfiltered = filter_semantic_models_by_explores(semantic_models, [])
    assert len(unfiltered) == 3
    
    print("✅ Semantic models filtering tests passed!")

def test_single_explore_scenario():
    print("\n=== Testing Single Explore Scenario ===")
    
    # Test what happens when only one explore is allowed
    golden_queries = {
        'exploreGenerationExamples': {
            'ecommerce:order_items': [{'input': 'test', 'output': 'test'}],
            'finance:transactions': [{'input': 'test2', 'output': 'test2'}]
        }
    }
    
    semantic_models = {
        'ecommerce:order_items': {'dimensions': [{'name': 'test'}]},
        'finance:transactions': {'dimensions': [{'name': 'test2'}]}
    }
    
    # Single explore restriction
    restricted_keys = ['ecommerce:order_items']
    
    filtered_golden = filter_golden_queries_by_explores(golden_queries, restricted_keys)
    filtered_semantic = filter_semantic_models_by_explores(semantic_models, restricted_keys)
    
    # Should only have the one allowed explore
    assert len(filtered_golden['exploreGenerationExamples']) == 1
    assert len(filtered_semantic) == 1
    assert 'ecommerce:order_items' in filtered_golden['exploreGenerationExamples']
    assert 'ecommerce:order_items' in filtered_semantic
    
    print("✅ Single explore scenario tests passed!")

if __name__ == "__main__":
    test_golden_queries_filtering()
    test_semantic_models_filtering() 
    test_single_explore_scenario()
    print("\n🎉 All filtering tests passed!")
