#!/usr/bin/env python3
"""Debug the schema issue with the user_id field"""

import os
from google.cloud import bigquery
import json

def debug_schema_issue():
    """Debug the BigQuery schema issue"""
    
    # Initialize BigQuery client
    client = bigquery.Client()
    
    # Table details
    project_id = os.getenv('BQ_PROJECT_ID', 'ml-accelerator-dbarr')
    dataset_id = 'explore_assistant'
    table_id = 'olympic_queries'
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    
    print(f"Debugging schema for table: {full_table_id}")
    
    try:
        # Get table metadata
        table = client.get_table(full_table_id)
        
        print(f"\nTable exists: {table.table_id}")
        print(f"Created: {table.created}")
        print(f"Modified: {table.modified}")
        print(f"Num rows: {table.num_rows}")
        
        print(f"\nSchema fields ({len(table.schema)} total):")
        for field in table.schema:
            print(f"  - {field.name}: {field.field_type} ({'NULLABLE' if field.mode == 'NULLABLE' else field.mode})")
        
        # Check if user_id specifically exists
        user_id_fields = [f for f in table.schema if f.name == 'user_id']
        if user_id_fields:
            print(f"\n✅ user_id field found: {user_id_fields[0].name} ({user_id_fields[0].field_type})")
        else:
            print(f"\n❌ user_id field NOT FOUND in schema")
        
        # Try a simple query to see what fields are actually queryable
        print(f"\nTesting actual queryable fields...")
        test_query = f"""
        SELECT column_name, data_type
        FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name = '{table_id}'
        ORDER BY ordinal_position
        """
        
        query_job = client.query(test_query)
        results = list(query_job.result())
        
        print(f"Queryable columns from INFORMATION_SCHEMA ({len(results)} total):")
        user_id_found = False
        for row in results:
            if row.column_name == 'user_id':
                user_id_found = True
                print(f"  ✅ {row.column_name}: {row.data_type}")
            else:
                print(f"  - {row.column_name}: {row.data_type}")
        
        if not user_id_found:
            print(f"\n❌ user_id NOT FOUND in INFORMATION_SCHEMA")
        
        # Try to insert a minimal test row
        print(f"\nTesting minimal insert...")
        test_row = {
            "id": "test-schema-debug",
            "explore_id": "test:explore",
            "input": "test input",
            "output": "test output",
            "link": "test link",
            "rank": "bronze",
            "created_at": "2025-01-01T00:00:00",
        }
        
        print(f"Test row keys: {list(test_row.keys())}")
        
        # Try insert without user_id first
        try:
            errors = client.insert_rows_json(table, [test_row])
            if errors:
                print(f"❌ Minimal insert failed: {errors}")
            else:
                print(f"✅ Minimal insert succeeded")
                # Clean up
                cleanup_query = f"DELETE FROM `{full_table_id}` WHERE id = 'test-schema-debug'"
                client.query(cleanup_query).result()
        except Exception as e:
            print(f"❌ Minimal insert exception: {e}")
        
        # Now try with user_id
        test_row_with_user_id = test_row.copy()
        test_row_with_user_id["user_id"] = "test-user-123"
        
        print(f"\nTesting insert with user_id...")
        print(f"Test row keys: {list(test_row_with_user_id.keys())}")
        
        try:
            errors = client.insert_rows_json(table, [test_row_with_user_id])
            if errors:
                print(f"❌ Insert with user_id failed: {errors}")
            else:
                print(f"✅ Insert with user_id succeeded")
                # Clean up
                cleanup_query = f"DELETE FROM `{full_table_id}` WHERE id = 'test-schema-debug'"
                client.query(cleanup_query).result()
        except Exception as e:
            print(f"❌ Insert with user_id exception: {e}")
            
    except Exception as e:
        print(f"❌ Error debugging schema: {e}")
        
if __name__ == "__main__":
    debug_schema_issue()
