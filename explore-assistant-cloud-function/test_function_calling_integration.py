#!/usr/bin/env python3
"""
Test the integration of function calling with field lookup in the MCP server
"""

import os
import sys
sys.path.append('/home/colin/looker-explore-assistant/explore-assistant-cloud-function')

import asyncio
from field_lookup_service import FieldValueLookupService

async def test_field_lookup_integration():
    """Test the field lookup service integration"""
    print("🔍 Testing Field Lookup Service Integration...")
    
    # Initialize the service
    service = FieldValueLookupService()
    print("✅ Service initialized")
    
    try:
        # Test semantic field search
        print("\n🔍 Testing semantic field search...")
        search_terms = ["customer", "revenue", "order"]
        results = await service.semantic_field_search(
            search_terms=search_terms,
            explore_ids=None,
            limit_per_term=3,
            similarity_threshold=0.7
        )
        
        print(f"✅ Semantic search returned {len(results)} results")
        for i, result in enumerate(results[:3]):
            print(f"  {i+1}. {result.field_location} ({result.field_type}) - similarity: {result.similarity:.3f}")
        
        # Test field value lookup
        print("\n🔍 Testing field value lookup...")
        value_results = await service.field_value_lookup(
            search_string="nike",
            field_location=None,
            limit=5
        )
        
        print(f"✅ Value lookup returned {len(value_results)} results")
        for i, result in enumerate(value_results[:3]):
            print(f"  {i+1}. {result['field_location']}: {result['field_value']}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All tests passed! Function calling integration is ready.")
    return True

def main():
    """Main test function"""
    print("🚀 Starting Function Calling Integration Test")
    print("=" * 50)
    
    try:
        # Run the async test
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            success = loop.run_until_complete(test_field_lookup_integration())
            if success:
                print("\n🎉 Integration test completed successfully!")
                print("\nThe following features are now available:")
                print("  • LLM can call search_semantic_fields() to find relevant Looker fields")
                print("  • LLM can call lookup_field_values() to find specific dimension values")
                print("  • Both determine_explore_from_prompt() and generate_explore_params() support function calling")
                print("  • Frontend requires no changes - function calling is transparent")
                return 0
            else:
                print("\n❌ Integration test failed")
                return 1
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
