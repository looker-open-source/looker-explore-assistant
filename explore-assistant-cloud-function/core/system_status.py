"""
Shared System Status Service

Provides system health and status information that can be used by both
REST API endpoints and MCP tools. Centralizes the business logic for
checking Olympic tables, legacy tables, vector search, and component health.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class SystemStatusService:
    """
    Shared service for getting system status information
    
    This service can be used by both REST endpoints and MCP tools
    to provide consistent system status information.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str):
        """
        Initialize the system status service
        
        Args:
            bq_client: BigQuery client instance
            project_id: GCP project ID
            dataset_id: BigQuery dataset ID
        """
        self.bq_client = bq_client
        self.project_id = project_id  
        self.dataset_id = dataset_id
        
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status including all components
        
        Returns:
            Dictionary containing complete system status information
        """
        try:
            status = {
                "system_status": "operational",
                "timestamp": datetime.utcnow().isoformat(),
                "project_id": self.project_id,
                "dataset_id": self.dataset_id,
                "components": {
                    "bigquery": "operational",
                    "olympic_system": "unknown",
                    "vector_search": "unknown",
                    "legacy_tables": "unknown"
                }
            }
            
            # Check Olympic system status
            olympic_status = self._get_olympic_status()
            status.update(olympic_status)
            status["components"]["olympic_system"] = "operational" if olympic_status["olympic_available"] else "unavailable"
            
            # Check legacy tables status
            legacy_status = self._get_legacy_tables_status()
            status.update(legacy_status)
            status["components"]["legacy_tables"] = "operational" if legacy_status["legacy_tables"] else "unavailable"
            
            # Add recommendations
            status["recommendations"] = self._generate_recommendations(status)
            
            # Set overall system status
            component_statuses = list(status["components"].values())
            if "error" in component_statuses:
                status["system_status"] = "degraded"
            elif "unavailable" in component_statuses:
                status["system_status"] = "partial"
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting comprehensive system status: {e}")
            return {
                "system_status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "components": {
                    "bigquery": "error",
                    "olympic_system": "error", 
                    "vector_search": "error",
                    "legacy_tables": "error"
                }
            }
    
    def _get_olympic_status(self) -> Dict[str, Any]:
        """Get Olympic table status and statistics"""
        olympic_info = {
            "olympic_available": False,
            "olympic_table_exists": False,
            "olympic_record_count": 0,
            "olympic_records_by_rank": {},
            "olympic_explore_field": None
        }
        
        try:
            # Check if Olympic table exists
            olympic_ref = self.bq_client.dataset(self.dataset_id).table('olympic_queries')
            olympic_table = self.bq_client.get_table(olympic_ref)
            
            olympic_info.update({
                "olympic_available": True,
                "olympic_table_exists": True,
                "olympic_record_count": olympic_table.num_rows,
                "olympic_explore_field": self._detect_explore_field_mapping('olympic_queries')
            })
            
            # Get records by rank statistics
            try:
                rank_query = f"""
                SELECT 
                    rank,
                    COUNT(*) as count
                FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
                GROUP BY rank
                ORDER BY rank
                """
                
                rank_results = self.bq_client.query(rank_query).result()
                olympic_info["olympic_records_by_rank"] = {
                    row.rank: row.count for row in rank_results
                }
                
            except Exception as e:
                logger.warning(f"Failed to get Olympic rank statistics: {e}")
                
        except NotFound:
            logger.info("Olympic table not found")
        except Exception as e:
            logger.error(f"Error checking Olympic status: {e}")
            
        return olympic_info
    
    def _get_legacy_tables_status(self) -> Dict[str, Any]:
        """Get legacy tables status and information"""
        legacy_info = {
            "legacy_tables": {},
            "total_legacy_records": 0
        }
        
        legacy_table_names = ['bronze_queries', 'silver_queries', 'golden_queries']
        
        for table_name in legacy_table_names:
            try:
                table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
                table = self.bq_client.get_table(table_ref)
                
                table_info = {
                    "exists": True,
                    "record_count": table.num_rows,
                    "created": table.created.isoformat() if table.created else None,
                    "modified": table.modified.isoformat() if table.modified else None,
                    "explore_field": self._detect_explore_field_mapping(table_name)
                }
                
                legacy_info["legacy_tables"][table_name] = table_info
                legacy_info["total_legacy_records"] += table.num_rows
                
            except NotFound:
                legacy_info["legacy_tables"][table_name] = {"exists": False, "record_count": 0}
            except Exception as e:
                logger.warning(f"Error checking legacy table {table_name}: {e}")
                legacy_info["legacy_tables"][table_name] = {"exists": False, "error": str(e)}
        
        return legacy_info
    
    def _detect_explore_field_mapping(self, table_name: str) -> Optional[str]:
        """
        Detect the field name used for explore information in a table
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            Field name used for explore info, or None if not detectable
        """
        try:
            # Get table schema
            table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
            table = self.bq_client.get_table(table_ref)
            
            # Look for common explore field names
            field_names = [field.name.lower() for field in table.schema]
            
            explore_field_candidates = ['explore_id', 'explore_key', 'explore', 'model_explore']
            
            for candidate in explore_field_candidates:
                if candidate in field_names:
                    return candidate
                    
            return None
            
        except Exception as e:
            logger.warning(f"Could not detect explore field for {table_name}: {e}")
            return None
    
    def _generate_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """
        Generate system recommendations based on current status
        
        Args:
            status: Current system status dictionary
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Olympic system recommendations
        if not status.get("olympic_available", False):
            recommendations.append("Consider migrating to Olympic system for improved performance and centralized query management")
        elif status.get("olympic_record_count", 0) == 0:
            recommendations.append("Olympic table exists but is empty - consider importing existing queries")
        
        # Legacy table recommendations
        total_legacy = status.get("total_legacy_records", 0)
        if total_legacy > 0 and status.get("olympic_available", False):
            recommendations.append(f"Found {total_legacy} legacy records that could be migrated to Olympic system")
        elif total_legacy > 1000:
            recommendations.append("Large number of legacy records detected - consider archiving old entries")
        
        # Performance recommendations
        olympic_count = status.get("olympic_record_count", 0)
        if olympic_count > 10000:
            recommendations.append("Large Olympic table detected - consider implementing data retention policies")
        
        return recommendations
    
    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get specific migration status information
        
        Returns:
            Dictionary with migration-specific status
        """
        try:
            status = self.get_comprehensive_status()
            
            migration_info = {
                "migration_ready": False,
                "migration_required": False,
                "can_migrate": False,
                "obstacles": []
            }
            
            # Determine migration readiness
            has_olympic = status.get("olympic_available", False)
            has_legacy = status.get("total_legacy_records", 0) > 0
            
            if has_olympic and not has_legacy:
                migration_info.update({
                    "migration_ready": True,
                    "migration_required": False,
                    "status": "fully_migrated"
                })
            elif has_olympic and has_legacy:
                migration_info.update({
                    "migration_ready": True, 
                    "migration_required": True,
                    "can_migrate": True,
                    "status": "partial_migration",
                    "legacy_records_to_migrate": status.get("total_legacy_records", 0)
                })
            elif not has_olympic and has_legacy:
                migration_info.update({
                    "migration_ready": False,
                    "migration_required": True, 
                    "can_migrate": False,
                    "status": "needs_olympic_setup"
                })
                migration_info["obstacles"].append("Olympic table must be created before migration")
            else:
                migration_info.update({
                    "migration_ready": False,
                    "migration_required": False,
                    "status": "clean_start"
                })
            
            return migration_info
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return {
                "migration_ready": False,
                "migration_required": False,
                "can_migrate": False,
                "status": "error",
                "error": str(e)
            }
    
    def get_quick_health_check(self) -> Dict[str, Any]:
        """
        Get a quick health check (lighter weight than comprehensive status)
        
        Returns:
            Dictionary with basic health information
        """
        try:
            # Quick BigQuery connectivity check
            query = f"SELECT 1 as health_check LIMIT 1"
            list(self.bq_client.query(query).result())
            
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "bigquery_connection": "operational"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy", 
                "timestamp": datetime.utcnow().isoformat(),
                "bigquery_connection": "failed",
                "error": str(e)
            }