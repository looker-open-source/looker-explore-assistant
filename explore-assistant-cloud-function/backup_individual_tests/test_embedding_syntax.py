#!/usr/bin/env python3

import os
from google.cloud import bigquery

def test_embedding_syntax():
    """Test different BigQuery embedding syntax options"""
    
    project_id = os.environ.get("PROJECT", "ml-accelerator-dbarr")
    dataset_id = os.environ.get("BQ_DATASET_ID", "explore_assistant")
    
    client = bigquery.Client(project=project_id)
    
    # Test 1: Simple embedding test
    test_query = f"""
    SELECT 
        'test text' as input_text,
        ML.GENERATE_TEXT_EMBEDDING(
            MODEL 'text-embedding-004',
            'test text'
        ) AS embedding
    LIMIT 1
    """
    
    try:
        print("🧪 Testing basic embedding syntax...")
        job = client.query(test_query)
        result = job.result()
        
        for row in result:
            print(f"✅ Embedding generated successfully: {len(row.embedding)} dimensions")
            return True
            
    except Exception as e:
        print(f"❌ Basic embedding test failed: {e}")
        
        # Test 2: Try with different syntax
        test_query2 = f"""
        SELECT 
            'test text' as input_text,
            ML.GENERATE_TEXT_EMBEDDING(
                MODEL 'textembedding-gecko@003',
                'test text'
            ) AS embedding
        LIMIT 1
        """
        
        try:
            print("🧪 Testing gecko model embedding syntax...")
            job2 = client.query(test_query2)
            result2 = job2.result()
            
            for row in result2:
                print(f"✅ Gecko embedding generated successfully: {len(row.embedding)} dimensions")
                return True
                
        except Exception as e2:
            print(f"❌ Gecko embedding test failed: {e2}")
            
            # Test 3: Try with STRUCT parameters
            test_query3 = f"""
            SELECT 
                'test text' as input_text,
                ML.GENERATE_TEXT_EMBEDDING(
                    MODEL 'text-embedding-004',
                    'test text',
                    STRUCT('RETRIEVAL_DOCUMENT' AS task_type)
                ) AS embedding
            LIMIT 1
            """
            
            try:
                print("🧪 Testing embedding with STRUCT parameters...")
                job3 = client.query(test_query3)
                result3 = job3.result()
                
                for row in result3:
                    print(f"✅ STRUCT embedding generated successfully: {len(row.embedding)} dimensions")
                    return True
                    
            except Exception as e3:
                print(f"❌ STRUCT embedding test failed: {e3}")
                return False

if __name__ == "__main__":
    test_embedding_syntax()
