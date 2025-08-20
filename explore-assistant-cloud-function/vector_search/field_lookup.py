"""
Field Value Lookup Service for semantic field discovery

A service that finds Looker fields and dimension values using vector search
and string similarity matching.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional

from google.cloud import bigquery

from core.config import BQ_PROJECT_ID, BQ_DATASET_ID, FIELD_VALUES_TABLE, EMBEDDING_MODEL
from core.models import FieldMatch
from core.exceptions import VectorSearchError

logger = logging.getLogger(__name__)


class FieldLookupService:
    """Service for looking up field values by string matching and vector search"""
    
    def __init__(self):
        self.bq_client = None
    
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client()
    
    async def search_semantic_fields(self, search_terms: List[str], explore_ids: Optional[List[str]] = None, 
                                   limit_per_term: int = 5) -> List[FieldMatch]:
        """
        Search for fields using semantic vector similarity
        
        Args:
            search_terms: List of terms to search for
            explore_ids: Optional list of explore IDs to filter by
            limit_per_term: Maximum results per search term
            
        Returns:
            List of FieldMatch objects
        """
        try:
            await self._ensure_bigquery_client()
            
            all_matches = []
            
            for term in search_terms:
                logger.info(f"🔍 Searching for semantic fields matching: '{term}'")
                
                # Build the vector search query
                query = self._build_semantic_search_query(term, explore_ids, limit_per_term)
                
                try:
                    results = list(self.bq_client.query(query))
                    logger.info(f"Found {len(results)} semantic matches for '{term}'")
                    
                    for row in results:
                        match = FieldMatch(
                            field_name=row.field_name,
                            field_location=row.field_location,
                            similarity_score=row.similarity,
                            description=row.field_description,
                            field_type=row.field_type
                        )
                        all_matches.append(match)
                        
                except Exception as e:
                    logger.error(f"Error searching for term '{term}': {e}")
                    continue
            
            return all_matches
            
        except Exception as e:
            logger.error(f"Semantic field search failed: {e}")
            raise VectorSearchError(f"Semantic field search failed: {e}", search_type="semantic")
    
    async def lookup_field_values(self, search_string: str, field_location: Optional[str] = None, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """
        Look up specific values in dimension fields
        
        Args:
            search_string: String to search for in field values
            field_location: Optional specific field to search in
            limit: Maximum number of results
            
        Returns:
            List of matching field values with metadata
        """
        try:
            await self._ensure_bigquery_client()
            
            logger.info(f"🔍 Looking up field values for: '{search_string}'")
            
            # Build the field value lookup query
            query = self._build_field_value_query(search_string, field_location, limit)
            
            results = list(self.bq_client.query(query))
            logger.info(f"Found {len(results)} field value matches")
            
            matches = []
            for row in results:
                match = {
                    "field_location": row.field_location,
                    "value": row.field_value,
                    "field_type": row.field_type,
                    "model_name": row.model_name,
                    "explore_name": row.explore_name,
                    "similarity": getattr(row, 'similarity', 1.0)
                }
                matches.append(match)
            
            return matches
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            raise VectorSearchError(f"Field value lookup failed: {e}", search_type="field_values")
    
    def _build_semantic_search_query(self, search_term: str, explore_ids: Optional[List[str]], 
                                   limit: int) -> str:
        """Build SQL query for semantic field search"""
        
        explore_filter = ""
        if explore_ids:
            formatted_ids = "', '".join(explore_ids)
            explore_filter = f"AND CONCAT(model_name, ':', explore_name) IN ('{formatted_ids}')"
        
        query = f"""
        WITH query_embedding AS (
          SELECT ML.GENERATE_TEXT_EMBEDDING(
            MODEL `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{EMBEDDING_MODEL}`,
            '{search_term}',
            STRUCT('SEMANTIC_SIMILARITY' as task_type)
          ).ml_generate_text_embedding_result AS query_vector
        ),
        similarities AS (
          SELECT 
            field_location,
            model_name,
            explore_name,
            view_name,
            field_name,
            field_type,
            field_description,
            ML.DISTANCE(field_embedding, query_vector) as distance
          FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}`,
               query_embedding
          WHERE field_embedding IS NOT NULL
            {explore_filter}
        )
        SELECT 
          field_location,
          model_name,
          explore_name,
          view_name,
          field_name,
          field_type,
          field_description,
          (1 - distance) as similarity
        FROM similarities
        WHERE (1 - distance) > 0.7
        ORDER BY similarity DESC
        LIMIT {limit}
        """
        
        return query
    
    def _build_field_value_query(self, search_string: str, field_location: Optional[str], 
                                limit: int) -> str:
        """Build SQL query for field value lookup"""
        
        field_filter = ""
        if field_location:
            field_filter = f"AND field_location = '{field_location}'"
        
        query = f"""
        SELECT DISTINCT
          field_location,
          field_value,
          field_type,
          model_name,
          explore_name
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}`
        WHERE field_value IS NOT NULL
          AND LOWER(CAST(field_value AS STRING)) LIKE LOWER('%{search_string}%')
          {field_filter}
        ORDER BY field_location, field_value
        LIMIT {limit}
        """
        
        return query
    
    async def get_field_statistics(self, explore_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get statistics about indexed fields"""
        try:
            await self._ensure_bigquery_client()
            
            explore_filter = ""
            if explore_ids:
                formatted_ids = "', '".join(explore_ids)
                explore_filter = f"WHERE CONCAT(model_name, ':', explore_name) IN ('{formatted_ids}')"
            
            query = f"""
            SELECT 
              COUNT(DISTINCT field_location) as total_fields,
              COUNT(DISTINCT CONCAT(model_name, ':', explore_name)) as total_explores,
              COUNT(DISTINCT model_name) as total_models,
              COUNT(*) as total_field_values
            FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{FIELD_VALUES_TABLE}`
            {explore_filter}
            """
            
            results = list(self.bq_client.query(query))
            if results:
                row = results[0]
                return {
                    "total_fields": row.total_fields,
                    "total_explores": row.total_explores,
                    "total_models": row.total_models,
                    "total_field_values": row.total_field_values
                }
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to get field statistics: {e}")
            return {}