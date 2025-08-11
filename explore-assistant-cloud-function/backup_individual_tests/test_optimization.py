#!/usr/bin/env python3
"""
Test script to demonstrate the optimization of context for parameter generation
Shows how filtering works at different stages of the pipeline
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from mcp_server import filter_golden_queries_by_explores, filter_semantic_models_by_explores

def test_parameter_generation_optimization():
    print("=== Testing Parameter Generation Context Optimization ===")
    
    # Mock full dataset (what comes from frontend)
    full_golden_queries = {
        'exploreGenerationExamples': {
            'ecommerce:order_items': [
                {'input': 'Show me total sales by month', 'output': 'ecommerce_params'},
                {'input': 'Customer orders analysis', 'output': 'ecommerce_params2'}
            ],
            'finance:transactions': [
                {'input': 'Monthly revenue breakdown', 'output': 'finance_params'}
            ],
            'marketing:campaigns': [
                {'input': 'Campaign performance metrics', 'output': 'marketing_params'}
            ],
            'hr:employees': [
                {'input': 'Employee headcount by department', 'output': 'hr_params'}
            ]
        },
        'exploreRefinementExamples': {
            'ecommerce:order_items': [{'input': 'refine sales', 'output': 'refine1'}],
            'finance:transactions': [{'input': 'refine revenue', 'output': 'refine2'}]
        }
    }
    
    full_semantic_models = {
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
        },
        'hr:employees': {
            'dimensions': [{'name': 'department'}],
            'measures': [{'name': 'headcount'}]
        }
    }
    
    print(f"📊 Original dataset:")
    print(f"   Golden queries explores: {list(full_golden_queries['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(full_semantic_models.keys())}")
    
    # Scenario 1: Area restriction to "Sales & Finance" area
    print(f"\n🎯 Scenario 1: Area restriction to 'Sales & Finance'")
    area_explores = ['ecommerce:order_items', 'finance:transactions']
    
    # Step 1: Filter to area explores (what happens early in process_explore_assistant_request)
    area_filtered_gq = filter_golden_queries_by_explores(full_golden_queries, area_explores)
    area_filtered_sm = filter_semantic_models_by_explores(full_semantic_models, area_explores)
    
    print(f"   After area filtering:")
    print(f"   Golden queries explores: {list(area_filtered_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(area_filtered_sm.keys())}")
    
    # Step 2: AI determines best explore (simulate choosing ecommerce:order_items)
    determined_explore = 'ecommerce:order_items'
    print(f"   AI determined explore: {determined_explore}")
    
    # Step 3: Optimize context for parameter generation (NEW OPTIMIZATION)
    param_gen_gq = filter_golden_queries_by_explores(area_filtered_gq, [determined_explore])
    param_gen_sm = filter_semantic_models_by_explores(area_filtered_sm, [determined_explore])
    
    print(f"   After parameter generation optimization:")
    print(f"   Golden queries explores: {list(param_gen_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(param_gen_sm.keys())}")
    
    # Verify only the chosen explore remains
    assert len(param_gen_gq['exploreGenerationExamples']) == 1
    assert len(param_gen_sm) == 1
    assert 'ecommerce:order_items' in param_gen_gq['exploreGenerationExamples']
    assert 'ecommerce:order_items' in param_gen_sm
    
    print(f"   ✅ Only chosen explore's context sent to LLM for parameter generation")
    
    # Scenario 2: Single explore restriction (bypass optimization)
    print(f"\n🎯 Scenario 2: Single explore restriction")
    single_explore = ['marketing:campaigns']
    
    # Step 1: Filter to single explore
    single_filtered_gq = filter_golden_queries_by_explores(full_golden_queries, single_explore)
    single_filtered_sm = filter_semantic_models_by_explores(full_semantic_models, single_explore)
    
    print(f"   After single explore filtering:")
    print(f"   Golden queries explores: {list(single_filtered_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(single_filtered_sm.keys())}")
    
    # Step 2: AI selection bypassed (determined_explore = single_explore[0])
    determined_explore = single_explore[0]
    print(f"   Determined explore (no AI needed): {determined_explore}")
    
    # Step 3: Optimize context (should be same as input since already single explore)
    param_gen_gq = filter_golden_queries_by_explores(single_filtered_gq, [determined_explore])
    param_gen_sm = filter_semantic_models_by_explores(single_filtered_sm, [determined_explore])
    
    print(f"   After parameter generation optimization:")
    print(f"   Golden queries explores: {list(param_gen_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(param_gen_sm.keys())}")
    
    # Verify single explore maintained
    assert len(param_gen_gq['exploreGenerationExamples']) == 1
    assert len(param_gen_sm) == 1
    assert 'marketing:campaigns' in param_gen_gq['exploreGenerationExamples']
    
    print(f"   ✅ Single explore context optimally maintained")
    
    # Scenario 3: No restrictions (full dataset)
    print(f"\n🎯 Scenario 3: No restrictions")
    
    # Step 1: No filtering (use full dataset)
    no_filter_gq = full_golden_queries
    no_filter_sm = full_semantic_models
    
    print(f"   No area filtering:")
    print(f"   Golden queries explores: {list(no_filter_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(no_filter_sm.keys())}")
    
    # Step 2: AI determines best explore from all available
    determined_explore = 'hr:employees'  # Simulate AI choosing HR explore
    print(f"   AI determined explore: {determined_explore}")
    
    # Step 3: Optimize context for parameter generation (CRITICAL for large datasets)
    param_gen_gq = filter_golden_queries_by_explores(no_filter_gq, [determined_explore])
    param_gen_sm = filter_semantic_models_by_explores(no_filter_sm, [determined_explore])
    
    print(f"   After parameter generation optimization:")
    print(f"   Golden queries explores: {list(param_gen_gq['exploreGenerationExamples'].keys())}")
    print(f"   Semantic models explores: {list(param_gen_sm.keys())}")
    
    # Verify massive reduction
    assert len(param_gen_gq['exploreGenerationExamples']) == 1
    assert len(param_gen_sm) == 1
    assert 'hr:employees' in param_gen_gq['exploreGenerationExamples']
    
    print(f"   ✅ Massive context reduction from 4 explores to 1 for parameter generation")
    
    print(f"\n🎉 All optimization scenarios validated!")
    print(f"\n📈 Benefits Summary:")
    print(f"   - Token usage minimized for parameter generation LLM calls")
    print(f"   - Context focused on only relevant explore")
    print(f"   - Consistent behavior across all restriction scenarios")
    print(f"   - API costs reduced through targeted context")

if __name__ == "__main__":
    test_parameter_generation_optimization()
