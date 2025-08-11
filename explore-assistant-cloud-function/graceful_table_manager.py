"""
Graceful Table Manager - Runtime table management with flexible schema handling.

Provides graceful fallback between Olympic and legacy table systems during normal operations.
Handles schema detection and automatic migration triggers without impacting performance.
"""

from typing import Dict, List, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GracefulTableManager:
    """
    Manages table operations with graceful fallback between Olympic and legacy systems.
    Provides runtime schema detection and handles both explore_key and explore_id fields.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str = "explore_assistant"):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self._olympic_verified = False
        self._field_mappings = {}  # Cache field mappings for performance
        self._table_schemas = {}   # Cache table schemas
        
    def _detect_explore_field_mapping(self, table_name: str) -> Optional[str]:
        """
        Detect and cache the explore field mapping for a table.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            str: 'explore_id', 'explore_key', or None if neither exists
        """
        if table_name in self._field_mappings:
            return self._field_mappings[table_name]
            
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
            table = self.bq_client.get_table(table_ref)
            available_fields = [field.name for field in table.schema]
            
            # Cache the full schema for later use
            self._table_schemas[table_name] = {
                'fields': available_fields,
                'record_count': table.num_rows,
                'last_checked': datetime.now()
            }
            
            if 'explore_id' in available_fields:
                mapping = 'explore_id'
            elif 'explore_key' in available_fields:
                mapping = 'explore_key'  # Will map to explore_id in queries
            else:
                mapping = None
                
            self._field_mappings[table_name] = mapping
            logger.debug(f"Cached field mapping for {table_name}: {mapping}")
            return mapping
            
        except NotFound:
            self._field_mappings[table_name] = None
            return None
        except Exception as e:
            logger.warning(f"Error detecting field mapping for {table_name}: {str(e)}")
            return None
    
    def _get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get cached table schema information.
        
        Args:
            table_name: Name of the table
            
        Returns:
            dict: Schema information including available fields
        """
        # Refresh schema if not cached or if explore field detection was called
        if (table_name not in self._table_schemas or 
            table_name not in self._field_mappings):
            self._detect_explore_field_mapping(table_name)
            
        return self._table_schemas.get(table_name, {
            'fields': [],
            'record_count': 0,
            'last_checked': None
        })
    
    async def ensure_olympic_system(self, auto_migrate: bool = False) -> bool:
        """
        Ensure Olympic system is available, optionally auto-migrate.
        
        Args:
            auto_migrate: Whether to automatically migrate legacy system if found
            
        Returns:
            bool: True if Olympic system is available, False otherwise
        """
        
        if self._olympic_verified:
            return True
            
        try:
            # Try to access Olympic table
            olympic_ref = self.bq_client.dataset(self.dataset_id).table('olympic_queries')
            table = self.bq_client.get_table(olympic_ref)
            
            # Verify it has records or is properly structured
            if table.num_rows >= 0:  # Even empty table is valid
                self._olympic_verified = True
                logger.info("Olympic system verified and available")
                return True
                
        except NotFound:
            logger.info("Olympic table doesn't exist")
            
            # Olympic table doesn't exist, check for legacy system
            if auto_migrate:
                logger.info("Checking for legacy system to auto-migrate")
                from .olympic_migration_manager import OlympicMigrationManager
                
                migration_manager = OlympicMigrationManager(
                    bq_client=self.bq_client,
                    project_id=self.project_id,
                    dataset_id=self.dataset_id
                )
                
                status = migration_manager.check_migration_status()
                if status['migration_needed'] and status['can_migrate_safely']:
                    logger.info("Auto-migrating legacy system to Olympic...")
                    try:
                        migration_result = migration_manager.migrate_to_olympic_system()
                        if migration_result['success']:
                            self._olympic_verified = True
                            logger.info("Auto-migration completed successfully")
                            return True
                        else:
                            logger.error("Auto-migration failed")
                    except Exception as e:
                        logger.error(f"Auto-migration error: {str(e)}")
                        
            return False
        except Exception as e:
            logger.error(f"Error checking Olympic system: {str(e)}")
            return False
    
    def _build_flexible_insert_query(self, table_name: str, data: Dict[str, Any], 
                                   additional_fields: Dict[str, Any] = None) -> tuple:
        """
        Build an insert query that works with flexible schema.
        
        Args:
            table_name: Target table name
            data: Data to insert
            additional_fields: Additional fields to include in insert
            
        Returns:
            tuple: (query_string, job_config)
        """
        explore_field = self._detect_explore_field_mapping(table_name)
        table_schema = self._get_table_schema(table_name)
        available_fields = table_schema.get('fields', [])
        
        if explore_field is None and table_name != 'olympic_queries':
            raise Exception(f"Table {table_name} has no explore field (explore_id or explore_key)")
        
        # Use appropriate field name in query
        explore_column = 'explore_id' if explore_field == 'explore_id' else 'explore_key'
        
        # Build field list and parameter list
        insert_fields = ['id', explore_column]
        parameters = [
            bigquery.ScalarQueryParameter("id", "STRING", data.get('id', str(uuid.uuid4()))),
            bigquery.ScalarQueryParameter("explore_value", "STRING", data.get('explore_id', ''))
        ]
        
        # Add core fields that exist in target table
        core_field_mappings = {
            'input': ('input', 'STRING'),
            'output': ('output', 'STRING'), 
            'link': ('link', 'STRING'),
            'user_email': ('user_email', 'STRING'),
            'created_at': ('created_at', 'TIMESTAMP'),
            'updated_at': ('updated_at', 'TIMESTAMP')
        }
        
        for data_key, (field_name, field_type) in core_field_mappings.items():
            if field_name in available_fields:
                insert_fields.append(field_name)
                if data_key == 'created_at' and data_key not in data:
                    parameters.append(bigquery.ScalarQueryParameter(f"param_{field_name}", field_type, 'CURRENT_TIMESTAMP()'))
                elif data_key == 'updated_at':
                    parameters.append(bigquery.ScalarQueryParameter(f"param_{field_name}", field_type, 'CURRENT_TIMESTAMP()'))
                else:
                    parameters.append(bigquery.ScalarQueryParameter(f"param_{field_name}", field_type, data.get(data_key)))
        
        # Add Olympic-specific fields if table supports them
        if table_name == 'olympic_queries':
            olympic_fields = {
                'rank': ('rank', 'STRING', additional_fields.get('rank', 'bronze')),
                'query_run_count': ('query_run_count', 'INT64', additional_fields.get('query_run_count', 1)),
                'feedback_type': ('feedback_type', 'STRING', additional_fields.get('feedback_type')),
                'promoted_by': ('promoted_by', 'STRING', additional_fields.get('promoted_by')),
                'promoted_at': ('promoted_at', 'TIMESTAMP', additional_fields.get('promoted_at'))
            }
            
            for field_key, (field_name, field_type, field_value) in olympic_fields.items():
                if field_name in available_fields and field_value is not None:
                    insert_fields.append(field_name)
                    parameters.append(bigquery.ScalarQueryParameter(f"param_{field_name}", field_type, field_value))
        
        # Build parameter placeholders
        param_placeholders = ['@id', '@explore_value']
        for field in insert_fields[2:]:  # Skip id and explore field
            param_placeholders.append(f"@param_{field}")
        
        # Handle timestamp fields specially  
        final_placeholders = []
        for i, field in enumerate(insert_fields):
            if i < 2:  # id and explore field
                final_placeholders.append(param_placeholders[i])
            elif field in ['created_at', 'updated_at'] and f'param_{field}' not in [p.name for p in parameters]:
                final_placeholders.append('CURRENT_TIMESTAMP()')
            else:
                final_placeholders.append(param_placeholders[i])
        
        query = f"""
        INSERT INTO `{self.project_id}.{self.dataset_id}.{table_name}`
        ({', '.join(insert_fields)})
        VALUES ({', '.join(final_placeholders)})
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=parameters)
        return query, job_config
    
    async def add_olympic_query_flexible(self, data: Dict[str, Any], rank: str = 'bronze') -> Dict[str, Any]:
        """
        Add query to Olympic system with flexible schema handling.
        
        Args:
            data: Query data to insert
            rank: Query rank (bronze, silver, gold)
            
        Returns:
            dict: Operation result with status information
        """
        
        # Ensure Olympic system is available
        olympic_available = await self.ensure_olympic_system(auto_migrate=False)
        
        if not olympic_available:
            raise Exception("Olympic system not available and auto-migration disabled")
        
        try:
            additional_fields = {'rank': rank, 'query_run_count': 1}
            query, job_config = self._build_flexible_insert_query('olympic_queries', data, additional_fields)
            
            logger.debug(f"Executing Olympic insert query: {query}")
            self.bq_client.query(query, job_config=job_config).result()
            
            return {
                "status": "success", 
                "table": "olympic_queries",
                "rank": rank,
                "system": "olympic",
                "explore_field_used": self._detect_explore_field_mapping('olympic_queries')
            }
            
        except Exception as e:
            logger.error(f"Failed to add Olympic query: {str(e)}")
            raise Exception(f"Olympic query insertion failed: {str(e)}")
    
    async def add_legacy_query_flexible(self, table_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add query to legacy table with flexible schema handling.
        
        Args:
            table_name: Legacy table name (bronze_queries, silver_queries, golden_queries)
            data: Query data to insert
            
        Returns:
            dict: Operation result with status information
        """
        
        try:
            query, job_config = self._build_flexible_insert_query(table_name, data)
            
            logger.debug(f"Executing legacy insert query for {table_name}: {query}")
            self.bq_client.query(query, job_config=job_config).result()
            
            return {
                "status": "success", 
                "table": table_name,
                "system": "legacy",
                "explore_field_used": self._detect_explore_field_mapping(table_name)
            }
            
        except Exception as e:
            logger.error(f"Failed to add query to {table_name}: {str(e)}")
            raise Exception(f"Legacy query insertion failed: {str(e)}")
    
    async def get_queries_flexible(self, table_name: str, explore_id: str = None, 
                                 rank: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get queries with flexible schema handling.
        
        Args:
            table_name: Table to query
            explore_id: Filter by explore ID
            rank: Filter by rank (Olympic table only)
            limit: Maximum number of results
            
        Returns:
            list: Query results with normalized field names
        """
        
        # Detect schema
        explore_field = self._detect_explore_field_mapping(table_name)
        
        if explore_field is None:
            logger.warning(f"Table {table_name} has no explore field")
            return []
        
        try:
            # Build query with appropriate field name, normalizing output to explore_id
            base_query = f"""
            SELECT 
                id, 
                {explore_field} as explore_id, 
                input, 
                output, 
                link,
                created_at
            """
            
            # Add table-specific fields
            table_schema = self._get_table_schema(table_name)
            available_fields = table_schema.get('fields', [])
            
            if 'promoted_by' in available_fields:
                base_query += ", promoted_by"
            if 'promoted_at' in available_fields:  
                base_query += ", promoted_at"
            if 'rank' in available_fields:
                base_query += ", rank"
            if 'user_email' in available_fields:
                base_query += ", user_email"
            if 'query_run_count' in available_fields:
                base_query += ", query_run_count"
            
            base_query += f"""
            FROM `{self.project_id}.{self.dataset_id}.{table_name}`
            """
            
            # Build WHERE conditions
            conditions = []
            parameters = []
            
            if explore_id:
                conditions.append(f"{explore_field} = @explore_id")
                parameters.append(bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id))
                
            if rank and table_name == 'olympic_queries':
                conditions.append("rank = @rank")
                parameters.append(bigquery.ScalarQueryParameter("rank", "STRING", rank))
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
                
            base_query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            job_config = bigquery.QueryJobConfig(query_parameters=parameters)
            results = self.bq_client.query(base_query, job_config=job_config)
            
            queries = [dict(row) for row in results]
            logger.debug(f"Retrieved {len(queries)} queries from {table_name}")
            return queries
            
        except Exception as e:
            logger.error(f"Failed to retrieve queries from {table_name}: {str(e)}")
            return []
    
    async def promote_query_flexible(self, query_id: str, from_rank: str, to_rank: str, 
                                   promoted_by: str) -> Dict[str, Any]:
        """
        Promote query between ranks with flexible schema handling.
        
        Args:
            query_id: ID of query to promote
            from_rank: Source rank
            to_rank: Target rank  
            promoted_by: User performing promotion
            
        Returns:
            dict: Promotion result
        """
        
        # Check if Olympic system is available
        olympic_available = await self.ensure_olympic_system()
        
        if olympic_available:
            # Use Olympic system promotion
            try:
                promote_query = f"""
                UPDATE `{self.project_id}.{self.dataset_id}.olympic_queries`
                SET 
                    rank = @to_rank,
                    promoted_by = @promoted_by,
                    promoted_at = CURRENT_TIMESTAMP(),
                    updated_at = CURRENT_TIMESTAMP()
                WHERE id = @query_id AND rank = @from_rank
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("query_id", "STRING", query_id),
                        bigquery.ScalarQueryParameter("from_rank", "STRING", from_rank),
                        bigquery.ScalarQueryParameter("to_rank", "STRING", to_rank),
                        bigquery.ScalarQueryParameter("promoted_by", "STRING", promoted_by),
                    ]
                )
                
                result = self.bq_client.query(promote_query, job_config=job_config).result()
                
                return {
                    "status": "promoted",
                    "system": "olympic", 
                    "from": from_rank,
                    "to": to_rank,
                    "query_id": query_id
                }
                
            except Exception as e:
                logger.error(f"Olympic promotion failed: {str(e)}")
                raise Exception(f"Query promotion failed: {str(e)}")
        else:
            # Fallback to legacy system promotion (copy between tables)
            logger.info("Using legacy system for query promotion")
            raise Exception("Legacy system promotion not implemented - migrate to Olympic system")
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status including available tables and schemas.
        
        Returns:
            dict: System status information
        """
        status = {
            'olympic_available': False,
            'legacy_tables': {},
            'field_mappings': self._field_mappings.copy(),
            'recommendations': []
        }
        
        # Check Olympic system
        try:
            olympic_ref = self.bq_client.dataset(self.dataset_id).table('olympic_queries')
            olympic_table = self.bq_client.get_table(olympic_ref)
            status['olympic_available'] = True
            status['olympic_records'] = olympic_table.num_rows
            status['olympic_explore_field'] = self._detect_explore_field_mapping('olympic_queries')
        except NotFound:
            status['recommendations'].append("Consider migrating to Olympic system for improved performance")
        
        # Check legacy tables
        legacy_tables = ['bronze_queries', 'silver_queries', 'golden_queries']
        for table_name in legacy_tables:
            try:
                table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
                table = self.bq_client.get_table(table_ref)
                status['legacy_tables'][table_name] = {
                    'records': table.num_rows,
                    'explore_field': self._detect_explore_field_mapping(table_name)
                }
            except NotFound:
                continue
        
        # Add recommendations
        if status['legacy_tables'] and not status['olympic_available']:
            status['recommendations'].append("Legacy tables found - migration to Olympic system recommended")
        elif status['legacy_tables'] and status['olympic_available']:
            status['recommendations'].append("Both systems present - consider cleaning up legacy tables")
        
        return status
