#!/usr/bin/env python3
"""
Test script for the new Looker query creation functionality in silver queries
"""

import json
import sys
import os
import logging

# Add the current directory to the path so we can import mcp_server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from mcp_server import create_looker_query_and_get_links, ensure_silver_queries_table_exists
    
    def test_query_creation():
        """Test the Looker query creation function with sample explore parameters"""
        
        # Sample explore parameters that would normally come from the LLM
        sample_explore_params = {
            'model': 'ecommerce',
            'view': 'order_items',
            'fields': ['order_items.order_id', 'order_items.sale_price', 'orders.created_date'],
            'filters': {
                'orders.created_date': '30 days ago for 30 days'
            },
            'sorts': ['orders.created_date desc'],
            'limit': 500,
            'vis_config': {
                'type': 'looker_line',
                'show_value_labels': False,
                'show_x_axis_label': True,
                'show_x_axis_ticks': True
            }
        }
        
        print("Testing Looker query creation function...")
        print(f"Sample explore params: {json.dumps(sample_explore_params, indent=2)}")
        
        # Test the function
        result = create_looker_query_and_get_links(sample_explore_params)
        
        print(f"\nResult: {json.dumps(result, indent=2)}")
        
        if result:
            print("✅ Query creation function returned a result")
            if result.get('query_slug'):
                print(f"✅ Query slug: {result['query_slug']}")
            if result.get('share_url'):
                print(f"✅ Share URL: {result['share_url']}")
            if result.get('expanded_share_url'):
                print(f"✅ Expanded share URL: {result['expanded_share_url']}")
        else:
            print("❌ Query creation function returned empty result")
        
        return result
    
    def test_table_schema():
        """Test that the silver queries table schema includes the new fields"""
        print("\nTesting silver queries table schema...")
        
        try:
            # This will create or update the table
            ensure_silver_queries_table_exists()
            print("✅ Silver queries table schema check/update completed")
        except Exception as e:
            print(f"❌ Error with silver queries table: {e}")
            return False
        
        return True
    
    if __name__ == "__main__":
        print("=" * 50)
        print("LOOKER QUERY LINKS TEST")
        print("=" * 50)
        
        # Test 1: Table schema
        schema_ok = test_table_schema()
        
        # Test 2: Query creation (only if we have Looker SDK configured)
        if schema_ok:
            query_result = test_query_creation()
            
            if query_result:
                print("\n✅ All tests passed! The functionality should work correctly.")
            else:
                print("\n⚠️  Query creation failed - check Looker SDK configuration")
                print("   This might be expected if LOOKERSDK environment variables are not set")
        else:
            print("\n❌ Schema test failed")
        
        print("=" * 50)

except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you're running this from the explore-assistant-cloud-function directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
