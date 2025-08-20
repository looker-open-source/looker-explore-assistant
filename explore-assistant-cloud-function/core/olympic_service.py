"""
Shared Olympic Operations Service

Provides centralized Olympic query management operations that can be used by both
REST API endpoints and MCP tools. This ensures consistent business logic while
allowing different interfaces.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class QueryRank(Enum):
    """Query ranking enumeration"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    DISQUALIFIED = "disqualified"


class OlympicOperationsService:
    """
    Shared service for Olympic query operations
    
    This service provides all Olympic query operations in a centralized way
    that can be used by both REST endpoints and MCP tools.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str):
        """
        Initialize the Olympic operations service
        
        Args:
            bq_client: BigQuery client instance
            project_id: GCP project ID
            dataset_id: BigQuery dataset ID
        """
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_name = "olympic_queries"
        
    def add_bronze_query(self, explore_id: str, input_text: str, output_data: Dict[str, Any], 
                        link: str, user_email: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a bronze query to the Olympic system
        
        Args:
            explore_id: Explore identifier
            input_text: User's input query text
            output_data: Generated parameters/output
            link: Link to the query results
            user_email: Email of the user who created the query
            session_id: Optional session identifier
            
        Returns:
            Dictionary with operation result
        """
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_name)
            
            # Create the record
            record = {
                "id": self._generate_query_id(),
                "explore_id": explore_id,
                "input": input_text,
                "output": output_data if isinstance(output_data, str) else str(output_data),
                "rank": QueryRank.BRONZE.value,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "link": link,
                "user_email": user_email,
                "session_id": session_id,
                "query_run_count": 1
            }
            
            # Insert the record
            errors = self.bq_client.insert_rows_json(table_ref, [record])
            
            if errors:
                raise Exception(f"Failed to insert bronze query: {errors}")
                
            logger.info(f"✅ Added bronze query {record['id']} for explore {explore_id}")
            
            return {
                "success": True,
                "query_id": record["id"],
                "rank": QueryRank.BRONZE.value,
                "message": "Bronze query added successfully"
            }
            
        except Exception as e:
            logger.error(f"Error adding bronze query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def add_silver_query(self, explore_id: str, input_text: str, output_data: Dict[str, Any],
                        link: str, user_id: str, feedback_type: str, 
                        conversation_history: Optional[str] = None) -> Dict[str, Any]:
        """
        Add a silver query to the Olympic system
        
        Args:
            explore_id: Explore identifier
            input_text: User's input query text
            output_data: Generated parameters/output
            link: Link to the query results
            user_id: ID of the user who created the query
            feedback_type: Type of feedback that promoted this to silver
            conversation_history: Optional conversation context
            
        Returns:
            Dictionary with operation result
        """
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_name)
            
            # Create the record
            record = {
                "id": self._generate_query_id(),
                "explore_id": explore_id,
                "input": input_text,
                "output": output_data if isinstance(output_data, str) else str(output_data),
                "rank": QueryRank.SILVER.value,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "link": link,
                "user_id": user_id,
                "feedback_type": feedback_type,
                "conversation_history": conversation_history
            }
            
            # Insert the record
            errors = self.bq_client.insert_rows_json(table_ref, [record])
            
            if errors:
                raise Exception(f"Failed to insert silver query: {errors}")
                
            logger.info(f"✅ Added silver query {record['id']} for explore {explore_id}")
            
            return {
                "success": True,
                "query_id": record["id"],
                "rank": QueryRank.SILVER.value,
                "message": "Silver query added successfully"
            }
            
        except Exception as e:
            logger.error(f"Error adding silver query: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def promote_query(self, query_id: str, target_rank: QueryRank, promoted_by: str,
                     promotion_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Promote a query to a higher rank
        
        Args:
            query_id: ID of the query to promote
            target_rank: Target rank to promote to
            promoted_by: User who is promoting the query
            promotion_reason: Optional reason for promotion
            
        Returns:
            Dictionary with operation result
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_name}"
            
            # Update the query with new rank and promotion info
            update_query = f"""
            UPDATE `{table_ref}`
            SET 
                rank = @target_rank,
                promoted_by = @promoted_by,
                promoted_at = @promoted_at,
                promotion_reason = @promotion_reason,
                updated_at = @updated_at
            WHERE id = @query_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("target_rank", "STRING", target_rank.value),
                    bigquery.ScalarQueryParameter("promoted_by", "STRING", promoted_by),
                    bigquery.ScalarQueryParameter("promoted_at", "STRING", datetime.utcnow().isoformat()),
                    bigquery.ScalarQueryParameter("promotion_reason", "STRING", promotion_reason),
                    bigquery.ScalarQueryParameter("updated_at", "STRING", datetime.utcnow().isoformat()),
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id)
                ]
            )
            
            query_job = self.bq_client.query(update_query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            if query_job.num_dml_affected_rows == 0:
                raise Exception(f"Query {query_id} not found")
                
            logger.info(f"✅ Promoted query {query_id} to {target_rank.value}")
            
            return {
                "success": True,
                "query_id": query_id,
                "new_rank": target_rank.value,
                "promoted_by": promoted_by,
                "promoted_at": datetime.utcnow().isoformat(),
                "message": f"Query promoted to {target_rank.value} successfully"
            }
            
        except Exception as e:
            logger.error(f"Error promoting query {query_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def delete_query(self, query_id: str, deleted_by: str) -> Dict[str, Any]:
        """
        Delete a query from the Olympic system
        
        Args:
            query_id: ID of the query to delete
            deleted_by: User who is deleting the query
            
        Returns:
            Dictionary with operation result
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_name}"
            
            # Delete the query
            delete_query = f"""
            DELETE FROM `{table_ref}`
            WHERE id = @query_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("query_id", "STRING", query_id)
                ]
            )
            
            query_job = self.bq_client.query(delete_query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            if query_job.num_dml_affected_rows == 0:
                raise Exception(f"Query {query_id} not found")
                
            logger.info(f"✅ Deleted query {query_id} by {deleted_by}")
            
            return {
                "success": True,
                "query_id": query_id,
                "deleted_by": deleted_by,
                "deleted_at": datetime.utcnow().isoformat(),
                "message": "Query deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting query {query_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_queries_by_rank(self, rank: QueryRank, explore_id: Optional[str] = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get queries by rank with optional filtering
        
        Args:
            rank: Rank to filter by
            explore_id: Optional explore ID to filter by
            limit: Maximum number of queries to return
            
        Returns:
            List of query dictionaries
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_name}"
            
            # Build query with optional explore filter
            where_clause = "WHERE rank = @rank"
            query_params = [
                bigquery.ScalarQueryParameter("rank", "STRING", rank.value),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            if explore_id:
                where_clause += " AND explore_id = @explore_id"
                query_params.append(
                    bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)
                )
            
            query = f"""
            SELECT *
            FROM `{table_ref}`
            {where_clause}
            ORDER BY created_at DESC
            LIMIT @limit
            """
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            query_job = self.bq_client.query(query, job_config=job_config)
            results = query_job.result()
            
            queries = []
            for row in results:
                queries.append(dict(row))
                
            logger.info(f"✅ Retrieved {len(queries)} {rank.value} queries")
            return queries
            
        except Exception as e:
            logger.error(f"Error getting {rank.value} queries: {e}")
            return []
    
    def get_query_stats(self) -> Dict[str, Any]:
        """
        Get statistics about queries in the Olympic system
        
        Returns:
            Dictionary with query statistics
        """
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_name}"
            
            # Get overall stats
            stats_query = f"""
            SELECT 
                rank,
                COUNT(*) as count,
                COUNT(DISTINCT explore_id) as unique_explores
            FROM `{table_ref}`
            GROUP BY rank
            """
            
            query_job = self.bq_client.query(stats_query)
            results = query_job.result()
            
            stats = {
                "total_queries": 0,
                "queries_by_rank": {},
                "unique_explores_by_rank": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            for row in results:
                rank = row.rank
                count = row.count
                unique_explores = row.unique_explores
                
                stats["queries_by_rank"][rank] = count
                stats["unique_explores_by_rank"][rank] = unique_explores
                stats["total_queries"] += count
            
            logger.info(f"✅ Retrieved query statistics: {stats['total_queries']} total queries")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting query stats: {e}")
            return {
                "total_queries": 0,
                "queries_by_rank": {},
                "unique_explores_by_rank": {},
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _generate_query_id(self) -> str:
        """Generate a unique query ID"""
        import uuid
        return f"query_{uuid.uuid4().hex[:12]}"
    
    def _check_table_exists(self) -> bool:
        """Check if the Olympic table exists"""
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_name)
            self.bq_client.get_table(table_ref)
            return True
        except NotFound:
            return False
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about the Olympic table"""
        try:
            if not self._check_table_exists():
                return {
                    "exists": False,
                    "record_count": 0
                }
                
            table_ref = self.bq_client.dataset(self.dataset_id).table(self.table_name)
            table = self.bq_client.get_table(table_ref)
            
            return {
                "exists": True,
                "record_count": table.num_rows,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "schema_fields": [field.name for field in table.schema]
            }
            
        except Exception as e:
            logger.error(f"Error getting table info: {e}")
            return {
                "exists": False,
                "record_count": 0,
                "error": str(e)
            }