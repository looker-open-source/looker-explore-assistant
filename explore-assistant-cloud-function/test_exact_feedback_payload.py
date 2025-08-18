#!/usr/bin/env python3
"""Test the exact same payload that add_feedback_query uses"""

import os
import json
from datetime import datetime
from google.cloud import bigquery

def test_feedback_query_payload():
    """Test the exact payload used by add_feedback_query"""
    
    client = bigquery.Client()
    
    # Table details
    project_id = os.getenv('BQ_PROJECT_ID', 'ml-accelerator-dbarr')
    dataset_id = 'explore_assistant'
    table_id = 'olympic_queries'
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    
    print(f"Testing exact feedback query payload for table: {full_table_id}")
    
    # Create the exact same payload that add_feedback_query creates
    feedback_id = "test-feedback-debug-123"
    explore_id = "ecommerce:order_items"
    original_prompt = "test prompt"
    generated_params = {"test": "data"}
    share_url = "https://test.com"
    feedback_type = "negative"
    user_id = "test-user-456"
    conversation_context = "test context"
    
    # This mirrors the exact logic from add_feedback_query
    combined_history = {
        "conversation_context": conversation_context or "",
        "feedback_details": {
            "feedback_type": feedback_type,
            "user_comment": None,
            "suggested_improvements": None,
            "issues": None,
            "timestamp": datetime.utcnow().isoformat()
        },
        "query_metadata": {
            "original_prompt": original_prompt,
            "query_id": feedback_id
        }
    }
    
    # This mirrors the exact row_data from _insert_query
    row_data = {
        "id": feedback_id,
        "explore_id": explore_id,
        "input": original_prompt,
        "output": json.dumps(generated_params),
        "link": share_url,
        "rank": "disqualified",  # DISQUALIFIED rank for negative feedback
        "created_at": datetime.utcnow().isoformat(),
        "promoted_by": None,
        "promoted_at": None,
        "user_email": None,
        "query_run_count": None,
        "user_id": user_id,
        "feedback_type": feedback_type,
        "conversation_history": json.dumps(combined_history)
    }
    
    # Remove None values (as done in _insert_query)
    row_data = {k: v for k, v in row_data.items() if v is not None}
    
    print(f"\nRow data keys: {list(row_data.keys())}")
    print(f"Row data values:")
    for k, v in row_data.items():
        if k == "conversation_history":
            print(f"  {k}: {v[:100]}..." if len(str(v)) > 100 else f"  {k}: {v}")
        else:
            print(f"  {k}: {v}")
    
    try:
        table = client.get_table(full_table_id)
        print(f"\nAttempting insert...")
        
        errors = client.insert_rows_json(table, [row_data])
        
        if errors:
            print(f"❌ Insert failed with errors: {errors}")
            
            # Check each error in detail
            for i, error_group in enumerate(errors):
                print(f"\nError group {i}: {error_group}")
                if 'errors' in error_group:
                    for j, error in enumerate(error_group['errors']):
                        print(f"  Error {j}:")
                        print(f"    reason: {error.get('reason', 'N/A')}")
                        print(f"    location: {error.get('location', 'N/A')}")
                        print(f"    message: {error.get('message', 'N/A')}")
                        
        else:
            print(f"✅ Insert succeeded!")
            
            # Query to verify the data was inserted
            verify_query = f"""
            SELECT id, user_id, feedback_type, rank
            FROM `{full_table_id}`
            WHERE id = '{feedback_id}'
            """
            
            query_job = client.query(verify_query)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                print(f"✅ Verified inserted data:")
                print(f"  ID: {row.id}")
                print(f"  User ID: {row.user_id}")
                print(f"  Feedback Type: {row.feedback_type}")
                print(f"  Rank: {row.rank}")
            else:
                print(f"❌ Data not found after insert")
            
    except Exception as e:
        print(f"❌ Exception during insert: {e}")
        
if __name__ == "__main__":
    test_feedback_query_payload()
