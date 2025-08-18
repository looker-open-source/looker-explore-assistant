#!/usr/bin/env python3

"""
Debug field lookup service project configuration
"""

import os
import asyncio
from field_lookup_service import FieldValueLookupService

async def debug_project_config():
    """Debug project configuration for field lookup service."""
    
    print("🔍 Debugging Project Configuration")
    print("=" * 50)
    
    # Check environment variables
    print(f"BQ_PROJECT_ID env var: {os.environ.get('BQ_PROJECT_ID', 'NOT SET')}")
    print(f"PROJECT env var: {os.environ.get('PROJECT', 'NOT SET')}")
    print(f"GOOGLE_CLOUD_PROJECT env var: {os.environ.get('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
    
    # Check field lookup service configuration
    from field_lookup_service import BQ_PROJECT_ID, DATASET_ID, FIELD_VALUES_TABLE
    print(f"\nField Lookup Service Config:")
    print(f"  BQ_PROJECT_ID: {BQ_PROJECT_ID}")
    print(f"  DATASET_ID: {DATASET_ID}")
    print(f"  FIELD_VALUES_TABLE: {FIELD_VALUES_TABLE}")
    
    # Try to initialize the service
    print(f"\n🧪 Testing Field Lookup Service Initialization:")
    try:
        service = FieldValueLookupService()
        await service._ensure_bigquery_client()
        
        # Try a simple test query to see what project is actually being used
        print(f"✅ BigQuery client initialized")
        print(f"   Project: {service.bq_client.project}")
        
        # Check if the vector table exists
        dataset_ref = service.bq_client.dataset(DATASET_ID)
        table_ref = dataset_ref.table(FIELD_VALUES_TABLE)
        
        try:
            table = service.bq_client.get_table(table_ref)
            print(f"✅ Vector table exists: {table.full_table_id}")
            print(f"   Rows: {table.num_rows}")
        except Exception as table_error:
            print(f"❌ Vector table not found: {table_error}")
            
    except Exception as e:
        print(f"❌ Field lookup service error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_project_config())
