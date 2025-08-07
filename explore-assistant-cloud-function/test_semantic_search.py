#!/usr/bin/env python3
"""
Test script for semantic field discovery using BigQuery vector search

This script demonstrates the vector-based field discovery system by running
semantic searches directly against the BigQuery table with embeddings.
"""

import json
import logging
import os
from typing import List, Dict, Any

from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"

class SemanticFieldSearch:
    """Test class for semantic field discovery"""
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
    
    def search_fields(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for fields using semantic similarity
        
        Args:
            query: Natural language query
            limit: Number of results to return
            
        Returns:
            List of matching fields with similarity scores
        """
        try:
            # Use BigQuery's VECTOR_SEARCH function to find similar fields
            search_query = f"""
            SELECT 
                base.model_name,
                base.explore_name,
                base.view_name, 
                base.field_name,
                base.field_type,
                base.field_description,
                base.field_value,
                base.value_frequency,
                base.searchable_text,
                distance
            FROM VECTOR_SEARCH(
                TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
                'ml_generate_embedding_result',
                (
                    SELECT ml_generate_embedding_result 
                    FROM ML.GENERATE_EMBEDDING(
                        MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`,
                        (SELECT @query_text as content),
                        STRUCT(TRUE AS flatten_json_output)
                    )
                ),
                top_k => {limit}
            )
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_text", "STRING", query)
                ]
            )
            
            results = self.bq_client.query(search_query, job_config=job_config).result()
            
            fields = []
            for row in results:
                fields.append({
                    "field_location": f"{row.model_name}.{row.explore_name}.{row.view_name}.{row.field_name}",
                    "field_type": row.field_type,
                    "field_description": row.field_description,
                    "field_value": row.field_value,
                    "value_frequency": row.value_frequency,
                    "searchable_text": row.searchable_text,
                    "similarity_distance": float(row.distance),
                    "similarity_score": 1.0 - float(row.distance)  # Convert distance to similarity
                })
            
            return fields
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def test_multiple_queries(self):
        """Test the semantic search with various queries"""
        test_queries = [
            "customer name",
            "product brand",
            "order date",
            "sales revenue",
            "inventory count",
            "user demographics",
            "fashion clothing",
            "eyewear sunglasses"
        ]
        
        print("🔍 SEMANTIC FIELD DISCOVERY TEST")
        print("=" * 50)
        
        for query in test_queries:
            print(f"\n📝 Query: '{query}'")
            print("-" * 30)
            
            results = self.search_fields(query, limit=5)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"{i}. {result['field_location']} ({result['field_type']})")
                    print(f"   Value: {result['field_value']}")
                    print(f"   Similarity: {result['similarity_score']:.3f}")
                    if result['field_description']:
                        print(f"   Description: {result['field_description']}")
                    print()
            else:
                print("   No results found")
                print()

def main():
    """Main function"""
    searcher = SemanticFieldSearch()
    searcher.test_multiple_queries()

if __name__ == "__main__":
    main()
