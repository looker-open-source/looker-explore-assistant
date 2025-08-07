#!/usr/bin/env python3
"""
Olympic Query Management for Looker Explore Assistant

Manages the three-tier query progression system using a single table:
- Bronze: Raw query patterns with usage tracking
- Silver: Queries with user feedback and conversation context  
- Golden: Curated training data for LLM prompts

Uses consistent explore_id naming and simplified single-table architecture.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

# Load environment variables
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
        logging.info("Loaded environment variables from .env file")
except ImportError:
    logging.info("python-dotenv not available, relying on system environment variables")

from google.cloud import bigquery
from google.auth import default

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration  
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
OLYMPIC_QUERIES_TABLE = "olympic_queries"

class QueryRank(Enum):
    """Query ranking system"""
    BRONZE = "bronze"
    SILVER = "silver" 
    GOLD = "gold"
    

@dataclass
class OlympicQuery:
    """Represents a query in the Olympic system"""
    id: str
    explore_id: str  # Using explore_id per coding instructions
    input: str
    output: Dict[str, Any]
    rank: QueryRank
    created_at: datetime
    updated_at: datetime
    link: Optional[str] = None
    promoted_by: Optional[str] = None
    promoted_at: Optional[datetime] = None
    promotion_reason: Optional[str] = None
    
    # Bronze-specific fields
    user_email: Optional[str] = None
    query_run_count: Optional[int] = None
    session_id: Optional[str] = None
    
    # Silver-specific fields
    user_id: Optional[str] = None
    feedback_type: Optional[str] = None
    feedback_score: Optional[int] = None
    conversation_history: Optional[List[Dict]] = None
    user_corrections: Optional[Dict] = None
    
    # Gold-specific fields
    training_weight: Optional[float] = None
    validation_status: Optional[str] = None
    example_category: Optional[str] = None

class OlympicQueryManager:
    """Manages the Olympic Query progression system"""
    
    # Core fields that migrate through all ranks
    CORE_FIELDS = [
        "id", "explore_id", "input", "output", "link", 
        "promoted_by", "promoted_at", "promotion_reason"
    ]
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
        self.table_ref = self.bq_client.dataset(DATASET_ID).table(OLYMPIC_QUERIES_TABLE)
        
    def _get_table_schema(self) -> List[bigquery.SchemaField]:
        """Get the complete table schema for olympic_queries"""
        return [
            # Core fields (always present)
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("explore_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("input", "STRING", mode="REQUIRED"), 
            bigquery.SchemaField("output", "JSON", mode="REQUIRED"),
            bigquery.SchemaField("rank", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("link", "STRING"),
            
            # Promotion tracking
            bigquery.SchemaField("promoted_by", "STRING"),
            bigquery.SchemaField("promoted_at", "TIMESTAMP"),
            bigquery.SchemaField("promotion_reason", "STRING"),
            
            # Bronze-specific fields (nullable)
            bigquery.SchemaField("user_email", "STRING"),
            bigquery.SchemaField("query_run_count", "INTEGER"),
            bigquery.SchemaField("session_id", "STRING"),
            
            # Silver-specific fields (nullable)
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("feedback_type", "STRING"),
            bigquery.SchemaField("feedback_score", "INTEGER"),
            bigquery.SchemaField("conversation_history", "JSON"),
            bigquery.SchemaField("user_corrections", "JSON"),
            
            # Gold-specific fields (nullable)
            bigquery.SchemaField("training_weight", "FLOAT"),
            bigquery.SchemaField("validation_status", "STRING"),
            bigquery.SchemaField("example_category", "STRING"),
        ]
    
    def ensure_table_exists(self) -> bool:
        """Ensure the olympic_queries table exists with proper schema"""
        try:
            # Try to get existing table
            try:
                table = self.bq_client.get_table(self.table_ref)
                logger.info(f"Olympic queries table already exists: {OLYMPIC_QUERIES_TABLE}")
                
                # Check if schema needs updating (add missing columns only)
                current_fields = {field.name for field in table.schema}
                required_fields = {field.name for field in self._get_table_schema()}
                missing_fields = required_fields - current_fields
                
                if missing_fields:
                    logger.info(f"Adding missing columns to olympic_queries: {missing_fields}")
                    new_schema = list(table.schema)
                    
                    # Add missing fields
                    for field in self._get_table_schema():
                        if field.name in missing_fields:
                            new_schema.append(field)
                    
                    # Update table schema (BigQuery allows adding columns)
                    table.schema = new_schema
                    table = self.bq_client.update_table(table, ["schema"])
                    logger.info("Successfully updated olympic_queries table schema")
                
                return True
                
            except Exception as e:
                if "Not found" in str(e):
                    # Table doesn't exist, create it
                    logger.info(f"Creating olympic_queries table: {OLYMPIC_QUERIES_TABLE}")
                    
                    table = bigquery.Table(self.table_ref, schema=self._get_table_schema())
                    table = self.bq_client.create_table(table)
                    
                    logger.info(f"Successfully created olympic_queries table")
                    return True
                else:
                    raise e
                    
        except Exception as e:
            logger.error(f"Failed to ensure olympic_queries table exists: {e}")
            return False
    
    def insert_bronze_query(
        self,
        explore_id: str,
        input_text: str,
        output_params: Dict[str, Any],
        user_email: Optional[str] = None,
        session_id: Optional[str] = None,
        link: Optional[str] = None
    ) -> Optional[str]:
        """Insert a new bronze query"""
        try:
            if not self.ensure_table_exists():
                return None
                
            query_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Check if similar query exists and increment run count
            existing_query = self._find_similar_query(explore_id, input_text, QueryRank.BRONZE)
            if existing_query:
                # Increment existing query run count
                update_query = f"""
                UPDATE `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
                SET query_run_count = COALESCE(query_run_count, 0) + 1,
                    updated_at = @updated_at
                WHERE id = @query_id
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", current_time),
                        bigquery.ScalarQueryParameter("query_id", "STRING", existing_query["id"])
                    ]
                )
                
                job = self.bq_client.query(update_query, job_config=job_config)
                job.result()
                
                logger.info(f"Incremented run count for existing bronze query: {existing_query['id']}")
                return existing_query["id"]
            
            # Insert new bronze query
            insert_query = f"""
            INSERT INTO `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            (id, explore_id, input, output, rank, created_at, updated_at, link, user_email, query_run_count, session_id)
            VALUES (@id, @explore_id, @input, @output, @rank, @created_at, @updated_at, @link, @user_email, @query_run_count, @session_id)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("id", "STRING", query_id),
                    bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id),
                    bigquery.ScalarQueryParameter("input", "STRING", input_text),
                    bigquery.ScalarQueryParameter("output", "JSON", json.dumps(output_params)),
                    bigquery.ScalarQueryParameter("rank", "STRING", QueryRank.BRONZE.value),
                    bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("link", "STRING", link),
                    bigquery.ScalarQueryParameter("user_email", "STRING", user_email),
                    bigquery.ScalarQueryParameter("query_run_count", "INT64", 1),
                    bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
                ]
            )
            
            job = self.bq_client.query(insert_query, job_config=job_config)
            job.result()
            
            logger.info(f"Inserted new bronze query: {query_id}")
            return query_id
            
        except Exception as e:
            logger.error(f"Failed to insert bronze query: {e}")
            return None
    
    def promote_to_silver(
        self,
        query_id: str,
        user_id: str,
        feedback_type: str,
        feedback_score: Optional[int] = None,
        conversation_history: Optional[List[Dict]] = None,
        user_corrections: Optional[Dict] = None,
        promoted_by: str = "system",
        promotion_reason: str = "user_feedback"
    ) -> bool:
        """Promote a bronze query to silver with user feedback"""
        try:
            current_time = datetime.utcnow()
            
            update_query = f"""
            UPDATE `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            SET rank = @new_rank,
                promoted_by = @promoted_by,
                promoted_at = @promoted_at,
                promotion_reason = @promotion_reason,
                updated_at = @updated_at,
                user_id = @user_id,
                feedback_type = @feedback_type,
                feedback_score = @feedback_score,
                conversation_history = @conversation_history,
                user_corrections = @user_corrections
            WHERE id = @query_id AND rank = @current_rank
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id),
                    bigquery.ScalarQueryParameter("current_rank", "STRING", QueryRank.BRONZE.value),
                    bigquery.ScalarQueryParameter("new_rank", "STRING", QueryRank.SILVER.value),
                    bigquery.ScalarQueryParameter("promoted_by", "STRING", promoted_by),
                    bigquery.ScalarQueryParameter("promoted_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("promotion_reason", "STRING", promotion_reason),
                    bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("feedback_type", "STRING", feedback_type),
                    bigquery.ScalarQueryParameter("feedback_score", "INT64", feedback_score),
                    bigquery.ScalarQueryParameter("conversation_history", "JSON", 
                                                 json.dumps(conversation_history) if conversation_history else None),
                    bigquery.ScalarQueryParameter("user_corrections", "JSON",
                                                 json.dumps(user_corrections) if user_corrections else None),
                ]
            )
            
            job = self.bq_client.query(update_query, job_config=job_config)
            result = job.result()
            
            # Check if any rows were updated
            if job.num_dml_affected_rows == 0:
                logger.warning(f"No bronze query found with id: {query_id}")
                return False
            
            logger.info(f"Promoted query {query_id} to silver rank")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote query to silver: {e}")
            return False
    
    def promote_to_gold(
        self,
        query_id: str,
        training_weight: float = 1.0,
        validation_status: str = "pending",
        example_category: Optional[str] = None,
        promoted_by: str = "curator",
        promotion_reason: str = "training_data_curation"
    ) -> bool:
        """Promote a silver query to gold for training data"""
        try:
            current_time = datetime.utcnow()
            
            update_query = f"""
            UPDATE `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            SET rank = @new_rank,
                promoted_by = @promoted_by,
                promoted_at = @promoted_at,
                promotion_reason = @promotion_reason,
                updated_at = @updated_at,
                training_weight = @training_weight,
                validation_status = @validation_status,
                example_category = @example_category
            WHERE id = @query_id AND rank = @current_rank
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id),
                    bigquery.ScalarQueryParameter("current_rank", "STRING", QueryRank.SILVER.value),
                    bigquery.ScalarQueryParameter("new_rank", "STRING", QueryRank.GOLD.value),
                    bigquery.ScalarQueryParameter("promoted_by", "STRING", promoted_by),
                    bigquery.ScalarQueryParameter("promoted_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("promotion_reason", "STRING", promotion_reason),
                    bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", current_time),
                    bigquery.ScalarQueryParameter("training_weight", "FLOAT64", training_weight),
                    bigquery.ScalarQueryParameter("validation_status", "STRING", validation_status),
                    bigquery.ScalarQueryParameter("example_category", "STRING", example_category),
                ]
            )
            
            job = self.bq_client.query(update_query, job_config=job_config)
            result = job.result()
            
            if job.num_dml_affected_rows == 0:
                logger.warning(f"No silver query found with id: {query_id}")
                return False
            
            logger.info(f"Promoted query {query_id} to gold rank")
            return True
            
        except Exception as e:
            logger.error(f"Failed to promote query to gold: {e}")
            return False
    
    def get_golden_queries_for_training(
        self,
        explore_id: Optional[str] = None,
        limit: int = 50,
        example_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get golden queries for LLM training prompts"""
        try:
            # Build WHERE conditions
            where_conditions = ["rank = @rank"]
            query_params = [
                bigquery.ScalarQueryParameter("rank", "STRING", QueryRank.GOLD.value),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            if explore_id:
                where_conditions.append("explore_id = @explore_id")
                query_params.append(bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id))
            
            if example_category:
                where_conditions.append("example_category = @example_category")
                query_params.append(bigquery.ScalarQueryParameter("example_category", "STRING", example_category))
            
            where_clause = " AND ".join(where_conditions)
            
            query = f"""
            SELECT 
                id, explore_id, input, output, training_weight,
                example_category, validation_status, created_at
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            WHERE {where_clause}
            ORDER BY training_weight DESC, created_at DESC
            LIMIT @limit
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            job = self.bq_client.query(query, job_config=job_config)
            results = job.result()
            
            golden_queries = []
            for row in results:
                golden_queries.append({
                    "id": row.id,
                    "explore_id": row.explore_id,
                    "input": row.input,
                    "output": json.loads(row.output) if row.output else {},
                    "training_weight": row.training_weight,
                    "example_category": row.example_category,
                    "validation_status": row.validation_status,
                    "created_at": row.created_at
                })
            
            logger.info(f"Retrieved {len(golden_queries)} golden queries for training")
            return golden_queries
            
        except Exception as e:
            logger.error(f"Failed to get golden queries: {e}")
            return []
    
    def get_query_progression_stats(self) -> Dict[str, Any]:
        """Get statistics about query progression through the Olympic system"""
        try:
            stats_query = f"""
            SELECT 
                rank,
                COUNT(*) as query_count,
                COUNT(DISTINCT explore_id) as unique_explores,
                AVG(CASE WHEN feedback_score IS NOT NULL THEN feedback_score END) as avg_feedback_score,
                COUNT(CASE WHEN promoted_at IS NOT NULL THEN 1 END) as promoted_count
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            GROUP BY rank
            ORDER BY 
                CASE rank 
                    WHEN 'bronze' THEN 1 
                    WHEN 'silver' THEN 2 
                    WHEN 'gold' THEN 3 
                END
            """
            
            job = self.bq_client.query(stats_query)
            results = job.result()
            
            stats = {
                "by_rank": {},
                "total_queries": 0,
                "total_explores": 0,
                "table_name": OLYMPIC_QUERIES_TABLE
            }
            
            unique_explores = set()
            
            for row in results:
                stats["by_rank"][row.rank] = {
                    "query_count": row.query_count,
                    "unique_explores": row.unique_explores,
                    "avg_feedback_score": float(row.avg_feedback_score) if row.avg_feedback_score else None,
                    "promoted_count": row.promoted_count
                }
                stats["total_queries"] += row.query_count
                unique_explores.add(row.unique_explores)
            
            stats["total_explores"] = len(unique_explores)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get progression stats: {e}")
            return {"error": str(e)}
    
    def _find_similar_query(self, explore_id: str, input_text: str, rank: QueryRank) -> Optional[Dict]:
        """Find similar existing query to avoid duplicates"""
        try:
            # Simple similarity check - can be enhanced with semantic similarity
            search_query = f"""
            SELECT id, input, query_run_count
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{OLYMPIC_QUERIES_TABLE}`
            WHERE explore_id = @explore_id 
            AND rank = @rank
            AND LOWER(input) = LOWER(@input_text)
            LIMIT 1
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id),
                    bigquery.ScalarQueryParameter("rank", "STRING", rank.value),
                    bigquery.ScalarQueryParameter("input_text", "STRING", input_text),
                ]
            )
            
            job = self.bq_client.query(search_query, job_config=job_config)
            results = job.result()
            
            for row in results:
                return {
                    "id": row.id,
                    "input": row.input,
                    "query_run_count": row.query_run_count or 0
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find similar query: {e}")
            return None

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage Olympic Query progression system")
    parser.add_argument("--action", choices=["setup", "stats", "golden"], required=True,
                       help="Action to perform")
    parser.add_argument("--explore-id", type=str,
                       help="Explore ID for filtering")
    parser.add_argument("--limit", type=int, default=50,
                       help="Limit for golden queries")
    
    args = parser.parse_args()
    
    manager = OlympicQueryManager()
    
    if args.action == "setup":
        success = manager.ensure_table_exists()
        if success:
            print("✅ Olympic queries table setup complete")
        else:
            print("❌ Failed to setup Olympic queries table")
            sys.exit(1)
    
    elif args.action == "stats":
        stats = manager.get_query_progression_stats()
        print(json.dumps(stats, indent=2, default=str))
    
    elif args.action == "golden":
        queries = manager.get_golden_queries_for_training(
            explore_id=args.explore_id,
            limit=args.limit
        )
        print(json.dumps(queries, indent=2, default=str))

if __name__ == "__main__":
    main()