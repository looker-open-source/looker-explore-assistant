#!/usr/bin/env python3
"""
Test script to verify bronze table has id field
"""
import os
import logging
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_bronze_table_schema():
    """Test that the bronze table has the id field"""
    try:
        # BigQuery configuration
        bq_project_id = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
        bq_dataset_id = os.environ.get("BQ_DATASET_ID", "explore_assistant")
        
        client = bigquery.Client(project=bq_project_id)
        bronze_table_id = f"{bq_project_id}.{bq_dataset_id}.bronze_queries"
        
        print(f"Checking bronze table: {bronze_table_id}")
        
        try:
            table = client.get_table(bronze_table_id)
            print(f"Table exists! Schema fields:")
            for field in table.schema:
                print(f"  - {field.name}: {field.field_type} ({field.mode})")
            
            # Check if id field exists
            id_field = next((f for f in table.schema if f.name == 'id'), None)
            if id_field:
                print(f"✅ ID field found: {id_field.name} ({id_field.field_type}, {id_field.mode})")
            else:
                print("❌ ID field not found")
                
        except Exception as e:
            print(f"Table doesn't exist or error accessing it: {e}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bronze_table_schema()
