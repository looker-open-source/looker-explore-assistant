#!/usr/bin/env python3
"""
Field Value Lookup Service for Looker Explore Assistant

A simple semantic search service that finds Looker fields and dimension values
based on string similarity. This service takes specific strings (not natural language phrases)
and returns matching field locations and values.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from google.cloud import bigquery
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

class FieldMatch(BaseModel):
    """A single field match from vector search"""
    field_location: str = Field(description="Full field path: model.explore.view.field")
    model_name: str
    explore_name: str
    view_name: str
    field_name: str
    field_type: str
    field_description: Optional[str]
    search_term: str
    similarity: float
    matching_values: List[Dict[str, Any]] = Field(description="List of matching field values")

class FieldValueLookupService:
    """Simple service for looking up field values by string matching"""
    
    def __init__(self):
        self.bq_client = None
    
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
            logger.info(f"Initialized BigQuery client for project: {BQ_PROJECT_ID}")
    
    async def semantic_field_search(
        self,
        search_terms: List[str], 
        explore_ids: Optional[List[str]] = None,
        limit_per_term: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[FieldMatch]:
        """
        Find Looker fields that semantically match the search terms
        
        Args:
            search_terms: List of specific strings to search for (e.g., ["brand", "customer", "revenue"])
            explore_ids: Optional list of explores to filter (model:explore format)
            limit_per_term: Max results per search term
            similarity_threshold: Minimum cosine similarity
        
        Returns:
            List of FieldMatch objects with similarity scores and matching values
        """
        if not search_terms:
            return []
        
        await self._ensure_bigquery_client()
        all_results = []
        
        for term in search_terms:
            try:
                # Use BigQuery VECTOR_SEARCH to find similar fields
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
                    base.field_location,
                    distance,
                    (1 - distance) as similarity
                FROM VECTOR_SEARCH(
                    TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
                    'ml_generate_embedding_result',
                    (
                        SELECT ml_generate_embedding_result 
                        FROM ML.GENERATE_EMBEDDING(
                            MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.{EMBEDDING_MODEL}`,
                            (SELECT @search_term as content),
                            STRUCT(TRUE AS flatten_json_output)
                        )
                    ),
                    top_k => @limit_per_term
                )
                WHERE (1 - distance) >= @similarity_threshold
                """
                
                query_params = [
                    bigquery.ScalarQueryParameter("search_term", "STRING", term),
                    bigquery.ScalarQueryParameter("limit_per_term", "INT64", limit_per_term),
                    bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold)
                ]
                
                # Add explore filtering if specified
                if explore_ids:
                    explore_conditions = []
                    for i, explore_id in enumerate(explore_ids):
                        model_name, explore_name = explore_id.split(':')
                        model_param = f"model_name_{i}"
                        explore_param = f"explore_name_{i}"
                        explore_conditions.append(f"(model_name = @{model_param} AND explore_name = @{explore_param})")
                        query_params.extend([
                            bigquery.ScalarQueryParameter(model_param, "STRING", model_name),
                            bigquery.ScalarQueryParameter(explore_param, "STRING", explore_name)
                        ])
                    search_query += f" AND ({' OR '.join(explore_conditions)})"
                
                search_query += " ORDER BY similarity DESC"
                
                job_config = bigquery.QueryJobConfig(query_parameters=query_params)
                results = self.bq_client.query(search_query, job_config=job_config).result()
                
                # Group results by field and collect matching values
                field_matches = {}
                for row in results:
                    field_location = row.field_location
                    
                    if field_location not in field_matches:
                        field_matches[field_location] = FieldMatch(
                            field_location=field_location,
                            model_name=row.model_name,
                            explore_name=row.explore_name,
                            view_name=row.view_name,
                            field_name=row.field_name,
                            field_type=row.field_type,
                            field_description=row.field_description,
                            search_term=term,
                            similarity=float(row.similarity),
                            matching_values=[]
                        )
                    
                    # Add this value to the matching values
                    field_matches[field_location].matching_values.append({
                        "value": row.field_value,
                        "similarity": float(row.similarity),
                        "frequency": int(row.value_frequency)
                    })
                    
                    # Update best similarity for this field
                    if float(row.similarity) > field_matches[field_location].similarity:
                        field_matches[field_location].similarity = float(row.similarity)
                
                all_results.extend(field_matches.values())
                
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {e}")
                continue
        
        # Remove duplicates and sort by similarity
        unique_results = {}
        for result in all_results:
            key = result.field_location
            if key not in unique_results or result.similarity > unique_results[key].similarity:
                unique_results[key] = result
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x.similarity, reverse=True)
        
        logger.info(f"Found {len(sorted_results)} unique field matches for terms: {search_terms}")
        return sorted_results
    
    async def field_value_lookup(
        self, 
        search_string: str,
        field_location: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find dimension values that contain a specific string
        
        Args:
            search_string: Specific string to find in dimension values
            field_location: Optional specific field to search within
            limit: Maximum number of matching values to return
        
        Returns:
            List of matching field values with metadata
        """
        await self._ensure_bigquery_client()
        
        try:
            # Build query to find dimension values containing the search string
            base_query = f"""
            SELECT 
                field_location,
                model_name,
                explore_name,
                view_name,
                field_name,
                field_type,
                field_value,
                value_frequency
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            WHERE LOWER(field_value) LIKE LOWER(@search_pattern)
            """
            
            query_params = [
                bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_string}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            # Add field location filter if specified
            if field_location:
                base_query += " AND field_location = @field_location"
                query_params.append(
                    bigquery.ScalarQueryParameter("field_location", "STRING", field_location)
                )
            
            base_query += " ORDER BY value_frequency DESC, field_value LIMIT @limit"
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            results = self.bq_client.query(base_query, job_config=job_config).result()
            
            matching_values = []
            for row in results:
                matching_values.append({
                    "field_location": row.field_location,
                    "model_name": row.model_name,
                    "explore_name": row.explore_name,
                    "view_name": row.view_name,
                    "field_name": row.field_name,
                    "field_type": row.field_type,
                    "field_value": row.field_value,
                    "value_frequency": int(row.value_frequency)
                })
            
            logger.info(f"Found {len(matching_values)} matching values for '{search_string}'")
            return matching_values
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            raise

# Example usage functions
async def test_field_search():
    """Test the field search functionality"""
    service = FieldValueLookupService()
    
    # Test semantic field search
    print("🔍 Testing semantic field search...")
    search_terms = ["brand", "customer", "revenue", "inventory"]
    results = await service.semantic_field_search(search_terms, limit_per_term=3)
    
    for result in results:
        print(f"  Field: {result.field_location} ({result.field_type})")
        print(f"  Search term: {result.search_term}")
        print(f"  Similarity: {result.similarity:.3f}")
        print(f"  Sample values: {[v['value'] for v in result.matching_values[:3]]}")
        print()
    
    # Test field value lookup
    print("🔍 Testing field value lookup...")
    value_results = await service.field_value_lookup("nike", limit=5)
    
    for result in value_results:
        print(f"  {result['field_location']}: {result['field_value']}")
    
    print(f"\nCompleted tests!")

async def main():
    """Main entry point for testing"""
    await test_field_search()

if __name__ == "__main__":
    asyncio.run(main())
