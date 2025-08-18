#!/usr/bin/env python3
"""
Olympic Query Management System

A unified approach to query storage and promotion with a single table design:
- Bronze: Raw queries with run counts
- Silver: Queries with user feedback
- Gold: Promoted training examples

Single table with rank-specific nullable columns for simplified management.
"""

import logging
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from google.cloud import bigquery
from google.cloud.bigquery import Table, SchemaField

logger = logging.getLogger(__name__)


class QueryRank(Enum):
    """Query ranks in the Olympic system"""
    BRONZE = "bronze"
    SILVER = "silver" 
    GOLD = "gold"
    DISQUALIFIED = "disqualified"  # For negative feedback and problematic queries


@dataclass
class OlympicQuery:
    """Represents a query in the Olympic system"""
    id: str
    explore_id: str
    input: str
    output: str
    link: str
    rank: QueryRank
    created_at: datetime
    promoted_by: Optional[str] = None
    promoted_at: Optional[datetime] = None
    
    # Bronze-specific fields
    user_email: Optional[str] = None
    query_run_count: Optional[int] = None
    
    # Silver-specific fields  
    user_id: Optional[str] = None
    feedback_type: Optional[str] = None
    conversation_history: Optional[str] = None


class OlympicQueryManager:
    """Manages queries across Bronze, Silver, and Gold ranks in a single table"""
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str = "explore_assistant"):
        self.client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = "olympic_queries"
        self.full_table_id = f"{project_id}.{dataset_id}.{self.table_id}"
        
    def ensure_table_exists(self) -> None:
        """Create the Olympic queries table if it doesn't exist"""
        try:
            self.client.get_table(self.full_table_id)
            logger.info(f"Olympic queries table already exists: {self.full_table_id}")
            return
        except Exception:
            logger.info(f"Creating Olympic queries table: {self.full_table_id}")
            
        # Single table schema with rank-specific nullable columns
        schema = [
            # Core fields (shared across all ranks)
            SchemaField("id", "STRING", mode="REQUIRED"),
            SchemaField("explore_id", "STRING", mode="REQUIRED"),
            SchemaField("input", "STRING", mode="REQUIRED"),
            SchemaField("output", "STRING", mode="REQUIRED"), 
            SchemaField("link", "STRING", mode="REQUIRED"),
            SchemaField("rank", "STRING", mode="REQUIRED"),
            SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            SchemaField("promoted_by", "STRING", mode="NULLABLE"),
            SchemaField("promoted_at", "TIMESTAMP", mode="NULLABLE"),
            
            # Bronze-specific fields (nullable)
            SchemaField("user_email", "STRING", mode="NULLABLE"),
            SchemaField("query_run_count", "INTEGER", mode="NULLABLE"),
            
            # Silver-specific fields (nullable)
            SchemaField("user_id", "STRING", mode="NULLABLE"),
            SchemaField("feedback_type", "STRING", mode="NULLABLE"),
            SchemaField("conversation_history", "STRING", mode="NULLABLE"),
        ]
        
        table = Table(self.full_table_id, schema=schema)
        table.description = "Olympic query management system with bronze/silver/gold ranks"
        
        self.client.create_table(table)
        logger.info(f"Created Olympic queries table: {self.full_table_id}")

    def validate_and_fix_table_schema(self) -> bool:
        """Check if table has correct schema and add missing columns or recreate if needed"""
        try:
            table = self.client.get_table(self.full_table_id)
            existing_fields = [field.name for field in table.schema]
            
            # Required fields for silver queries
            required_fields = ['user_id', 'feedback_type', 'conversation_history']
            missing_fields = [field for field in required_fields if field not in existing_fields]
            
            if missing_fields:
                logger.warning(f"Table {self.full_table_id} missing fields: {missing_fields}")
                
                # Try to add missing columns instead of recreating table
                try:
                    self._add_missing_columns(missing_fields)
                    logger.info(f"Successfully added missing columns: {missing_fields}")
                    return True
                except Exception as alter_error:
                    logger.warning(f"Failed to add columns, recreating table: {alter_error}")
                    
                    # Fallback: recreate table (this will lose data)
                    logger.info(f"Recreating table with correct schema...")
                    self.client.delete_table(self.full_table_id)
                    logger.info(f"Deleted existing table: {self.full_table_id}")
                    
                    # Recreate with correct schema
                    self.ensure_table_exists()
                    logger.info(f"Recreated table with correct schema: {self.full_table_id}")
                    return True
            else:
                logger.info(f"Table {self.full_table_id} has correct schema")
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate table schema: {e}")
            return False

    def _add_missing_columns(self, missing_fields: List[str]) -> None:
        """Add missing columns to the existing table"""
        # Define the schema for missing fields
        field_definitions = {
            'user_id': SchemaField("user_id", "STRING", mode="NULLABLE"),
            'feedback_type': SchemaField("feedback_type", "STRING", mode="NULLABLE"),
            'conversation_history': SchemaField("conversation_history", "STRING", mode="NULLABLE")
        }
        
        # Get current table
        table = self.client.get_table(self.full_table_id)
        
        # Add missing fields to schema
        new_schema = list(table.schema)
        for field_name in missing_fields:
            if field_name in field_definitions:
                new_schema.append(field_definitions[field_name])
                logger.info(f"Adding column {field_name} to table schema")
        
        # Update table schema
        table.schema = new_schema
        updated_table = self.client.update_table(table, ["schema"])
        logger.info(f"Updated table schema with {len(missing_fields)} new columns")
    
    def add_bronze_query(self, explore_id: str, input_text: str, output: str, 
                        link: str, user_email: str, query_run_count: int = 1) -> str:
        """Add a new bronze query"""
        query_id = str(uuid.uuid4())
        
        query = OlympicQuery(
            id=query_id,
            explore_id=explore_id,
            input=input_text,
            output=output,
            link=link,
            rank=QueryRank.BRONZE,
            created_at=datetime.utcnow(),
            user_email=user_email,
            query_run_count=query_run_count
        )
        
        self._insert_query(query)
        logger.info(f"Added bronze query {query_id} for explore {explore_id}")
        return query_id
    
    def add_silver_query(self, explore_id: str, input_text: str, output: str,
                        link: str, user_id: str, feedback_type: str, 
                        conversation_history: str = None) -> str:
        """Add a new silver query with feedback"""
        query_id = str(uuid.uuid4())
        
        query = OlympicQuery(
            id=query_id,
            explore_id=explore_id,
            input=input_text,
            output=output,
            link=link,
            rank=QueryRank.SILVER,
            created_at=datetime.utcnow(),
            user_id=user_id,
            feedback_type=feedback_type,
            conversation_history=conversation_history
        )
        
        self._insert_query(query)
        logger.info(f"Added silver query {query_id} for explore {explore_id}")
        return query_id

    def add_feedback_query(self, explore_id: str, original_prompt: str, generated_params: dict,
                          share_url: str, feedback_type: str, user_id: str, 
                          conversation_context: str = None, user_comment: str = None, 
                          suggested_improvements: str = None, issues: list = None, 
                          query_id: str = None) -> str:
        """
        Add a comprehensive feedback query combining conversation history with user feedback.
        Uses SILVER rank for positive feedback, DISQUALIFIED rank for negative feedback.
        
        Args:
            explore_id: The explore this feedback applies to
            original_prompt: The user's original query
            generated_params: The AI-generated query parameters
            share_url: Link to the query
            feedback_type: 'positive', 'negative', 'refinement', 'alternative'
            user_id: User who provided feedback
            conversation_context: Previous conversation history context
            user_comment: User's additional comments
            suggested_improvements: Specific improvement suggestions
            issues: List of issues (for negative feedback)
            query_id: Optional specific ID to use
        
        Returns:
            str: The query ID
        """
        
        feedback_id = query_id or str(uuid.uuid4())
        
        # Determine rank based on feedback type
        if feedback_type == 'negative':
            rank = QueryRank.DISQUALIFIED
        else:
            rank = QueryRank.SILVER
        
        # Structure: conversation context first, then feedback details
        combined_history = {
            "conversation_context": conversation_context or "",
            "feedback_details": {
                "feedback_type": feedback_type,
                "user_comment": user_comment,
                "suggested_improvements": suggested_improvements,
                "issues": issues,
                "timestamp": datetime.utcnow().isoformat()
            },
            "query_metadata": {
                "original_prompt": original_prompt,
                "query_id": feedback_id
            }
        }
        
        query = OlympicQuery(
            id=feedback_id,
            explore_id=explore_id,
            input=original_prompt,
            output=json.dumps(generated_params),
            link=share_url,
            rank=rank,
            created_at=datetime.utcnow(),
            user_id=user_id,
            feedback_type=feedback_type,
            conversation_history=json.dumps(combined_history)
        )
        
        self._insert_query(query)
        logger.info(f"Added {rank.value} feedback query {feedback_id} with type {feedback_type} to table {self.full_table_id}")
        return feedback_id
    
    def add_disqualified_query(self, explore_id: str, input_text: str, output: str,
                              link: str, user_id: str, feedback_type: str,
                              conversation_history: str = None) -> str:
        """Add a disqualified query (negative feedback)"""
        query_id = str(uuid.uuid4())
        
        query = OlympicQuery(
            id=query_id,
            explore_id=explore_id,
            input=input_text,
            output=output,
            link=link,
            rank=QueryRank.DISQUALIFIED,
            created_at=datetime.utcnow(),
            user_id=user_id,
            feedback_type=feedback_type,
            conversation_history=conversation_history
        )
        
        self._insert_query(query)
        logger.info(f"Added disqualified query {query_id} for explore {explore_id}")
        return query_id
    
    def promote_to_gold(self, query_id: str, promoted_by: str) -> bool:
        """Promote a bronze or silver query to gold status"""
        try:
            # Update the query rank and promotion metadata
            update_query = f"""
            UPDATE `{self.full_table_id}`
            SET 
                rank = 'gold',
                promoted_by = @promoted_by,
                promoted_at = CURRENT_TIMESTAMP()
            WHERE id = @query_id
            AND rank IN ('bronze', 'silver')
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id),
                    bigquery.ScalarQueryParameter("promoted_by", "STRING", promoted_by)
                ]
            )
            
            query_job = self.client.query(update_query, job_config=job_config)
            query_job.result()
            
            if query_job.num_dml_affected_rows > 0:
                logger.info(f"Promoted query {query_id} to gold by {promoted_by}")
                return True
            else:
                logger.warning(f"No query found to promote with ID: {query_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to promote query {query_id}: {e}")
            return False
    
    def get_queries_by_rank(self, rank: QueryRank, explore_id: str = None, 
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get queries filtered by rank and optionally by explore"""
        query = f"""
        SELECT *
        FROM `{self.full_table_id}`
        WHERE rank = @rank
        """
        
        query_params = [
            bigquery.ScalarQueryParameter("rank", "STRING", rank.value)
        ]
        
        if explore_id:
            query += " AND explore_id = @explore_id"
            query_params.append(
                bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)
            )
        
        query += " ORDER BY created_at DESC LIMIT @limit"
        query_params.append(
            bigquery.ScalarQueryParameter("limit", "INT64", limit)
        )
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        results = self.client.query(query, job_config=job_config).result()
        
        return [dict(row) for row in results]
    
    def get_gold_queries_for_training(self, explore_id: str = None) -> List[Dict[str, Any]]:
        """Get gold queries suitable for LLM training"""
        return self.get_queries_by_rank(QueryRank.GOLD, explore_id)
    
    def update_bronze_run_count(self, query_id: str) -> bool:
        """Increment the run count for a bronze query"""
        try:
            update_query = f"""
            UPDATE `{self.full_table_id}`
            SET query_run_count = COALESCE(query_run_count, 0) + 1
            WHERE id = @query_id
            AND rank = 'bronze'
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id)
                ]
            )
            
            query_job = self.client.query(update_query, job_config=job_config)
            query_job.result()
            
            return query_job.num_dml_affected_rows > 0
            
        except Exception as e:
            logger.error(f"Failed to update run count for query {query_id}: {e}")
            return False
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get statistics about queries by rank"""
        stats_query = f"""
        SELECT 
            rank,
            COUNT(*) as count,
            MIN(created_at) as earliest,
            MAX(created_at) as latest
        FROM `{self.full_table_id}`
        GROUP BY rank
        ORDER BY 
            CASE rank
                WHEN 'bronze' THEN 1
                WHEN 'silver' THEN 2  
                WHEN 'gold' THEN 3
                ELSE 4
            END
        """
        
        results = self.client.query(stats_query).result()
        
        stats = {}
        for row in results:
            stats[row.rank] = {
                "count": row.count,
                "earliest": row.earliest.isoformat() if row.earliest else None,
                "latest": row.latest.isoformat() if row.latest else None
            }
        
        return stats
    
    def _insert_query(self, query: OlympicQuery) -> None:
        """Insert a query into the table"""
        logger.info(f"Inserting query {query.id} with rank {query.rank.value} into table {self.full_table_id}")
        
        # DIAGNOSTIC: Check table schema right before insertion
        try:
            table_ref = self.client.get_table(self.full_table_id)
            current_schema_fields = [f.name for f in table_ref.schema]
            logger.info(f"DIAGNOSTIC: Current table schema fields: {current_schema_fields}")
            logger.info(f"DIAGNOSTIC: user_id in schema: {'user_id' in current_schema_fields}")
            logger.info(f"DIAGNOSTIC: feedback_type in schema: {'feedback_type' in current_schema_fields}")
        except Exception as schema_check_error:
            logger.error(f"DIAGNOSTIC: Failed to check table schema: {schema_check_error}")
        
        row_data = {
            "id": query.id,
            "explore_id": query.explore_id,
            "input": query.input,
            "output": query.output,
            "link": query.link,
            "rank": query.rank.value,
            "created_at": query.created_at.isoformat(),
            "promoted_by": query.promoted_by,
            "promoted_at": query.promoted_at.isoformat() if query.promoted_at else None,
            "user_email": query.user_email,
            "query_run_count": query.query_run_count,
            "user_id": query.user_id,
            "feedback_type": query.feedback_type,
            "conversation_history": query.conversation_history
        }
        
        # Remove None values to avoid insertion issues
        row_data = {k: v for k, v in row_data.items() if v is not None}
        logger.info(f"Row data keys: {list(row_data.keys())}")
        logger.info(f"DIAGNOSTIC: user_id value: {row_data.get('user_id', 'NOT_PRESENT')}")
        logger.info(f"DIAGNOSTIC: feedback_type value: {row_data.get('feedback_type', 'NOT_PRESENT')}")
        logger.info(f"Inserting into BigQuery table: {self.full_table_id}")
        
        # DIAGNOSTIC: Get fresh table reference right before insert
        try:
            fresh_table = self.client.get_table(self.full_table_id)
            logger.info(f"DIAGNOSTIC: Fresh table retrieved, num_rows={fresh_table.num_rows}")
        except Exception as fresh_table_error:
            logger.error(f"DIAGNOSTIC: Failed to get fresh table reference: {fresh_table_error}")
            fresh_table = None
        
        try:
            errors = self.client.insert_rows_json(
                fresh_table or self.client.get_table(self.full_table_id), 
                [row_data]
            )
            
            if errors:
                logger.error(f"BigQuery insert failed for table {self.full_table_id}: {errors}")
                # DIAGNOSTIC: Log detailed error information
                for i, error_group in enumerate(errors):
                    logger.error(f"DIAGNOSTIC: Error group {i}: {error_group}")
                    if isinstance(error_group, dict) and 'errors' in error_group:
                        for j, error in enumerate(error_group['errors']):
                            logger.error(f"DIAGNOSTIC: Error {j}: reason={error.get('reason', 'N/A')}, location={error.get('location', 'N/A')}, message={error.get('message', 'N/A')}")
                raise Exception(f"Failed to insert query: {errors}")
            else:
                logger.info(f"Successfully inserted query {query.id} into {self.full_table_id}")
                
        except Exception as insert_exception:
            logger.error(f"DIAGNOSTIC: Insert exception: {insert_exception}")
            raise
    
    def delete_query(self, query_id: str) -> bool:
        """Delete a query by ID"""
        try:
            delete_query = f"""
            DELETE FROM `{self.full_table_id}`
            WHERE id = @query_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id)
                ]
            )
            
            query_job = self.client.query(delete_query, job_config=job_config)
            query_job.result()
            
            return query_job.num_dml_affected_rows > 0
            
        except Exception as e:
            logger.error(f"Failed to delete query {query_id}: {e}")
            return False
