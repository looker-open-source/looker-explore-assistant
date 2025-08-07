#!/usr/bin/env python3

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment variables and basic imports"""
    print("🧪 Testing Environment...")
    
    # Check environment variables
    required_vars = [
        'PROJECT',
        'BQ_DATASET_ID', 
        'LOOKERSDK_BASE_URL',
        'LOOKERSDK_CLIENT_ID',
        'LOOKERSDK_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value[:20]}{'...' if len(value) > 20 else ''}")
        else:
            print(f"❌ {var}: Not set")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n❌ Missing required environment variables: {missing_vars}")
        return False
    
    # Test imports
    try:
        print("\n📦 Testing imports...")
        import looker_sdk
        print("✅ looker_sdk imported successfully")
        
        from google.cloud import bigquery
        print("✅ google.cloud.bigquery imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_looker_connection():
    """Test Looker SDK connection"""
    print("\n🔗 Testing Looker connection...")
    
    try:
        import looker_sdk
        sdk = looker_sdk.init40()
        
        # Test connection
        user = sdk.me()
        print(f"✅ Connected to Looker as: {user.email}")
        
        # Test getting models
        models = sdk.all_lookml_models(fields='name', limit=5)
        print(f"✅ Found {len(models)} models (first 5): {[m.name for m in models]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Looker connection failed: {e}")
        return False

def test_specific_explore():
    """Test the specific explore we're debugging"""
    print("\n🎯 Testing sales_demo_the_look:order_items explore...")
    
    try:
        import looker_sdk
        sdk = looker_sdk.init40()
        
        # Get specific explore detail
        explore_detail = sdk.lookml_model_explore(
            lookml_model_name="sales_demo_the_look",
            explore_name="order_items",
            fields='sets,fields'
        )
        
        print(f"✅ Explore loaded: has_sets={bool(explore_detail.sets)}, has_fields={bool(explore_detail.fields)}")
        
        # Check sets
        if explore_detail.sets:
            index_sets = []
            for set_info in explore_detail.sets:
                if set_info.name == 'index' or set_info.name.endswith('.index'):
                    index_sets.append(set_info)
                    print(f"✅ Found index set: {set_info.name} with {len(set_info.value) if set_info.value else 0} fields")
            
            if index_sets:
                print(f"✅ Total index sets found: {len(index_sets)}")
            else:
                print("❌ No index sets found")
        
        # Check fields
        if explore_detail.fields and explore_detail.fields.dimensions:
            print(f"✅ Found {len(explore_detail.fields.dimensions)} dimensions")
            # Show first 5 dimension field keys
            first_5_dims = []
            for i, dim in enumerate(explore_detail.fields.dimensions[:5]):
                field_key = f"{dim.view}.{dim.name}" if dim.view else dim.name
                first_5_dims.append(field_key)
            print(f"   First 5 dimension keys: {first_5_dims}")
        
        return True
        
    except Exception as e:
        print(f"❌ Explore test failed: {e}")
        import traceback
        print(f"   Detailed error: {traceback.format_exc()}")
        return False

def main():
    print("🚀 Running Debug Tests for Vector Table Manager\n")
    
    # Test 1: Environment
    if not test_environment():
        print("\n❌ Environment test failed - fix environment variables first")
        return False
    
    # Test 2: Looker connection
    if not test_looker_connection():
        print("\n❌ Looker connection test failed - check credentials")
        return False
    
    # Test 3: Specific explore
    if not test_specific_explore():
        print("\n❌ Specific explore test failed")
        return False
    
    print("\n✅ All tests passed! Ready to run vector table manager.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
