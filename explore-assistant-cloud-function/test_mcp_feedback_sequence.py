#!/usr/bin/env python3
"""Test the exact sequence that MCP server goes through for add_feedback_query"""

import os
import json
from datetime import datetime
from google.cloud import bigquery
import sys
import asyncio

# Add the current directory to Python path so we can import modules
sys.path.append('.')

from olympic_query_manager import OlympicQueryManager
from olympic_mcp_integration import OlympicMCPIntegration

def test_mcp_feedback_sequence():
    """Test the exact sequence that the MCP server goes through"""
    
    print("Testing MCP feedback query sequence...")
    
    # Initialize BigQuery client
    client = bigquery.Client()
    
    # Configuration
    project_id = os.getenv('BQ_PROJECT_ID', 'ml-accelerator-dbarr')
    dataset_id = 'explore_assistant'
    
    print(f"Using project: {project_id}, dataset: {dataset_id}")
    
    # Create OlympicMCPIntegration (as done in mcp_server.py)
    olympic_integration = OlympicMCPIntegration(client, project_id, dataset_id)
    
    # Test arguments (matching what frontend sends)
    arguments = {
        'explore_id': 'ecommerce:order_items',
        'original_prompt': 'test MCP feedback prompt',
        'generated_params': {"dimensions": ["orders.created_date"], "measures": ["orders.count"]},
        'share_url': 'https://test-mcp-feedback.com',
        'feedback_type': 'negative',
        'user_id': 'test-mcp-user-789',
        'conversation_context': 'Previous conversation about order analysis',
        'user_comment': 'This query did not work as expected',
        'issues': ['incorrect_dimensions', 'missing_filters']
    }
    
    print(f"\nTest arguments:")
    for k, v in arguments.items():
        if k == 'generated_params':
            print(f"  {k}: {json.dumps(v)}")
        else:
            print(f"  {k}: {v}")
    
    async def run_test():
        try:
            print(f"\n--- Testing MCP handle_add_feedback_query ---")
            result = await olympic_integration.handle_add_feedback_query(arguments)
            
            print(f"\nMCP Result:")
            print(f"  Status: {result.get('status', 'unknown')}")
            if result.get('status') == 'success':
                print(f"  Query ID: {result.get('result', {}).get('query_id', 'N/A')}")
                print(f"  Rank: {result.get('result', {}).get('rank', 'N/A')}")
                print(f"  Table: {result.get('result', {}).get('table_id', 'N/A')}")
            else:
                print(f"  Error: {result.get('error', 'N/A')}")
                
            return result
            
        except Exception as e:
            print(f"❌ Exception in MCP test: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # Run the async test
    try:
        result = asyncio.run(run_test())
        
        if result and result.get('status') == 'success':
            print(f"\n✅ MCP feedback query test succeeded!")
            
            # Verify the data was actually inserted
            query_id = result.get('result', {}).get('query_id')
            if query_id:
                print(f"\n--- Verifying inserted data ---")
                verify_query = f"""
                SELECT id, explore_id, feedback_type, rank, user_id, created_at
                FROM `{project_id}.{dataset_id}.olympic_queries`
                WHERE id = '{query_id}'
                """
                
                query_job = client.query(verify_query)
                results = list(query_job.result())
                
                if results:
                    row = results[0]
                    print(f"✅ Verified data in BigQuery:")
                    print(f"  ID: {row.id}")
                    print(f"  Explore ID: {row.explore_id}")
                    print(f"  Feedback Type: {row.feedback_type}")
                    print(f"  Rank: {row.rank}")
                    print(f"  User ID: {row.user_id}")
                    print(f"  Created: {row.created_at}")
                else:
                    print(f"❌ No data found in BigQuery for query_id: {query_id}")
        else:
            print(f"\n❌ MCP feedback query test failed!")
            
    except Exception as e:
        print(f"❌ Failed to run async test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_feedback_sequence()
