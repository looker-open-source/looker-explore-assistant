#!/usr/bin/env python3
"""
Test Vector Search Functionality

This script demonstrates the semantic field discovery system by running
queries against the vector-enabled BigQuery table.
"""

import os
import json
from google.cloud import bigquery
from typing import List, Dict, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
except ImportError:
    pass

BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"

def test_vector_search(query_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Test the vector search functionality"""
    client = bigquery.Client(project=BQ_PROJECT_ID)
    
    # Use VECTOR_SEARCH function for semantic similarity
    search_query = f"""
    SELECT 
        model_name,
        explore_name,
        view_name,
        field_name,
        field_type,
        field_description,
        field_value,
        searchable_text,
        distance
    FROM VECTOR_SEARCH(
        TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
        'ml_generate_embedding_result',
        (
            SELECT ml_generate_embedding_result
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`,
                (SELECT '{query_text}' AS content),
                STRUCT(TRUE AS flatten_json_output)
            )
        ),
        top_k => {top_k},
        distance_type => 'COSINE'
    )
    ORDER BY distance ASC
    """
    
    print(f"🔍 Searching for: '{query_text}'")
    print(f"📊 Query: {search_query}")
    
    try:
        job = client.query(search_query)
        results = job.result()
        
        matches = []
        for row in results:
            match = {
                "model": row.model_name,
                "explore": row.explore_name,
                "view": row.view_name,
                "field": row.field_name,
                "type": row.field_type,
                "description": row.field_description or "No description",
                "value": row.field_value,
                "searchable_text": row.searchable_text,
                "distance": float(row.distance)
            }
            matches.append(match)
        
        return matches
        
    except Exception as e:
        print(f"❌ Vector search failed: {e}")
        return []

def test_table_contents():
    """Test basic table contents and structure"""
    client = bigquery.Client(project=BQ_PROJECT_ID)
    
    # Get basic stats
    stats_query = f"""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT CONCAT(model_name, ':', explore_name)) as unique_explores,
        COUNT(DISTINCT field_name) as unique_fields,
        COUNT(DISTINCT field_type) as unique_types
    FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
    """
    
    print("📊 Table Statistics:")
    try:
        job = client.query(stats_query)
        results = job.result()
        stats = next(results)
        
        print(f"   Total rows: {stats.total_rows}")
        print(f"   Unique explores: {stats.unique_explores}")
        print(f"   Unique fields: {stats.unique_fields}")
        print(f"   Unique types: {stats.unique_types}")
        
    except Exception as e:
        print(f"❌ Stats query failed: {e}")
        return
    
    # Get sample entries
    sample_query = f"""
    SELECT 
        model_name,
        explore_name,
        field_name,
        field_type,
        field_value,
        LEFT(searchable_text, 100) as preview_text
    FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
    ORDER BY field_name
    LIMIT 10
    """
    
    print("\n🔍 Sample Entries:")
    try:
        job = client.query(sample_query)
        results = job.result()
        
        for i, row in enumerate(results, 1):
            print(f"   {i}. {row.model_name}:{row.explore_name}.{row.field_name} ({row.field_type})")
            print(f"      Value: '{row.field_value}'")
            print(f"      Preview: {row.preview_text}...")
            print()
            
    except Exception as e:
        print(f"❌ Sample query failed: {e}")

def main():
    """Main test function"""
    print("🚀 Testing Vector Search System")
    print("=" * 50)
    
    # Test 1: Table contents and structure
    test_table_contents()
    
    # Test 2: Semantic search queries
    test_queries = [
        "product brand name",
        "customer information",
        "sales revenue",
        "order date",
        "inventory count"
    ]
    
    print("\n🔍 Testing Semantic Searches:")
    print("=" * 50)
    
    for query in test_queries:
        print(f"\n🎯 Query: '{query}'")
        matches = test_vector_search(query, top_k=5)
        
        if matches:
            print(f"   Found {len(matches)} matches:")
            for i, match in enumerate(matches, 1):
                field_path = f"{match['model']}:{match['explore']}.{match['view']}.{match['field']}"
                print(f"   {i}. {field_path} ({match['type']}) - Distance: {match['distance']:.4f}")
                print(f"      Value: '{match['value']}'")
                if match['description'] != "No description":
                    print(f"      Description: {match['description']}")
                print()
        else:
            print("   ❌ No matches found")
        
        print("-" * 30)

if __name__ == "__main__":
    main()
