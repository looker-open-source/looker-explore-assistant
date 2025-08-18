"""
Vector Search MCP Integration

Provides MCP tools for vector search database management including setup, 
population, and maintenance operations. Keeps vector search concerns 
separate from Olympic query management.
"""

import logging
from typing import Dict, Any, List
from google.cloud import bigquery
from vector_table_manager import VectorTableManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorSearchMCPIntegration:
    """
    MCP integration layer for vector search system management.
    Provides tools for vector database setup, population, and maintenance.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str = "explore_assistant"):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.vector_manager = VectorTableManager(bq_client, project_id, dataset_id)
    
    async def handle_check_vector_search_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to check vector search system status.
        
        Args:
            arguments: Tool arguments (empty for this tool)
            
        Returns:
            dict: Vector search system status
        """
        try:
            logger.info("Checking vector search status via MCP")
            
            # Check if vector tables exist
            vector_status = {
                'vector_tables_exist': False,
                'field_values_table_records': 0,
                'embedding_model_exists': False,
                'indexed_explores': [],
                'last_update': None,
                'system_ready': False,
                'recommendations': []
            }
            
            # Check field values table
            try:
                table_ref = self.bq_client.dataset(self.dataset_id).table('field_values_for_vectorization')
                table = self.bq_client.get_table(table_ref)
                vector_status['vector_tables_exist'] = True
                vector_status['field_values_table_records'] = table.num_rows
                vector_status['last_update'] = table.modified.isoformat() if table.modified else None
                
                # Get indexed explores
                explore_query = f"""
                SELECT DISTINCT CONCAT(model_name, ':', explore_name) as explore_id, COUNT(*) as field_count
                FROM `{self.project_id}.{self.dataset_id}.field_values_for_vectorization`
                GROUP BY model_name, explore_name
                ORDER BY field_count DESC
                """
                
                results = self.bq_client.query(explore_query).result()
                vector_status['indexed_explores'] = [
                    {'explore_id': row.explore_id, 'field_count': row.field_count} 
                    for row in results
                ]
                
            except Exception as e:
                logger.warning(f"Field values table not found: {str(e)}")
                vector_status['recommendations'].append("Vector search tables need to be created")
            
            # Check embedding model
            try:
                model_query = f"""
                SELECT * FROM ML.MODELS 
                WHERE model_name = 'text_embedding_model'
                """
                results = list(self.bq_client.query(model_query).result())
                vector_status['embedding_model_exists'] = len(results) > 0
                
            except Exception as e:
                logger.warning(f"Could not check embedding model: {str(e)}")
                vector_status['recommendations'].append("Text embedding model needs to be created")
            
            # Determine system readiness
            vector_status['system_ready'] = (
                vector_status['vector_tables_exist'] and 
                vector_status['embedding_model_exists'] and
                vector_status['field_values_table_records'] > 0
            )
            
            if vector_status['system_ready']:
                vector_status['recommendations'].append("✅ Vector search system is ready for use")
            else:
                vector_status['recommendations'].append("🔧 Vector search system needs setup")
            
            return {
                "tool": "check_vector_search_status",
                "status": "success",
                "result": vector_status
            }
            
        except Exception as e:
            logger.error(f"Vector search status check failed: {str(e)}")
            return {
                "tool": "check_vector_search_status",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_setup_vector_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to setup vector search system.
        
        Args:
            arguments: Setup options including force_refresh flag
            
        Returns:
            dict: Setup results
        """
        force_refresh = arguments.get('force_refresh', False)
        
        try:
            logger.info(f"Setting up vector search system via MCP (force_refresh={force_refresh})")
            
            setup_log = {
                'started_at': None,
                'steps_completed': [],
                'tables_created': [],
                'models_created': [],
                'records_processed': 0,
                'errors': [],
                'success': False
            }
            
            # Use vector table manager to perform setup
            if hasattr(self.vector_manager, 'setup_vector_tables'):
                setup_result = self.vector_manager.setup_vector_tables(force_refresh=force_refresh)
                setup_log.update(setup_result)
            else:
                # Fallback to manual setup steps
                setup_log = await self._manual_vector_setup(force_refresh)
            
            return {
                "tool": "setup_vector_search",
                "status": "success" if setup_log['success'] else "error",
                "result": setup_log
            }
            
        except Exception as e:
            logger.error(f"Vector search setup failed: {str(e)}")
            return {
                "tool": "setup_vector_search",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_populate_vector_data(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to populate vector search data from Looker explores.
        
        Args:
            arguments: Population options including explore_ids and batch_size
            
        Returns:
            dict: Population results
        """
        explore_ids = arguments.get('explore_ids', [])  # Empty means all restricted explores
        batch_size = arguments.get('batch_size', 1000)
        
        try:
            logger.info(f"Populating vector search data via MCP (explores={len(explore_ids)})")
            
            population_log = {
                'started_at': None,
                'explores_processed': [],
                'total_records_added': 0,
                'batch_size': batch_size,
                'errors': [],
                'success': False
            }
            
            # Use vector table manager for population
            if hasattr(self.vector_manager, 'populate_from_explores'):
                result = self.vector_manager.populate_from_explores(
                    explore_ids=explore_ids,
                    batch_size=batch_size
                )
                population_log.update(result)
            else:
                # Fallback implementation
                population_log = await self._manual_populate_vectors(explore_ids, batch_size)
            
            return {
                "tool": "populate_vector_data", 
                "status": "success" if population_log['success'] else "error",
                "result": population_log
            }
            
        except Exception as e:
            logger.error(f"Vector data population failed: {str(e)}")
            return {
                "tool": "populate_vector_data",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_test_vector_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to test vector search functionality.
        
        Args:
            arguments: Test parameters including search_terms
            
        Returns:
            dict: Test results
        """
        search_terms = arguments.get('search_terms', ['nike', 'product', 'sales'])
        limit = arguments.get('limit', 5)
        
        try:
            logger.info(f"Testing vector search via MCP (terms={search_terms})")
            
            test_results = {
                'search_terms_tested': search_terms,
                'results_per_term': {},
                'total_results': 0,
                'search_successful': False,
                'performance_ms': None
            }
            
            import time
            start_time = time.time()
            
            # Test semantic field search
            for term in search_terms:
                search_query = f"""
                WITH search_embedding AS (
                    SELECT ml_generate_text_embedding_result as search_vector
                    FROM ML.GENERATE_TEXT_EMBEDDING(
                        MODEL `{self.project_id}.{self.dataset_id}.text_embedding_model`,
                        (SELECT @search_term as content)
                    )
                )
                SELECT 
                    model_name,
                    explore_name,
                    field_name,
                    field_value,
                    value_frequency,
                    ML.DISTANCE(search_vector, ml_generate_embedding_result, 'COSINE') as similarity_score
                FROM `{self.project_id}.{self.dataset_id}.field_values_for_vectorization`, search_embedding
                WHERE ML.DISTANCE(search_vector, ml_generate_embedding_result, 'COSINE') < 0.7
                ORDER BY similarity_score ASC
                LIMIT @limit
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("search_term", "STRING", term),
                        bigquery.ScalarQueryParameter("limit", "INT64", limit)
                    ]
                )
                
                results = self.bq_client.query(search_query, job_config=job_config).result()
                term_results = [dict(row) for row in results]
                
                test_results['results_per_term'][term] = term_results
                test_results['total_results'] += len(term_results)
            
            test_results['performance_ms'] = (time.time() - start_time) * 1000
            test_results['search_successful'] = test_results['total_results'] > 0
            
            return {
                "tool": "test_vector_search",
                "status": "success",
                "result": test_results
            }
            
        except Exception as e:
            logger.error(f"Vector search test failed: {str(e)}")
            return {
                "tool": "test_vector_search",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_refresh_vector_embeddings(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to refresh vector embeddings for existing field data.
        
        Args:
            arguments: Refresh options including explore_ids filter
            
        Returns:
            dict: Refresh results
        """
        explore_ids = arguments.get('explore_ids', [])
        
        try:
            logger.info(f"Refreshing vector embeddings via MCP (explores={len(explore_ids)})")
            
            # Build refresh query
            base_query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.field_values_for_vectorization`
            SET ml_generate_embedding_result = (
                SELECT ml_generate_text_embedding_result
                FROM ML.GENERATE_TEXT_EMBEDDING(
                    MODEL `{self.project_id}.{self.dataset_id}.text_embedding_model`,
                    (SELECT searchable_text as content)
                )
            )
            WHERE ml_generate_embedding_result IS NULL
            """
            
            # Add explore filter if specified
            if explore_ids:
                explore_conditions = []
                for explore_id in explore_ids:
                    if ':' in explore_id:
                        model_name, explore_name = explore_id.split(':', 1)
                        explore_conditions.append(f"(model_name = '{model_name}' AND explore_name = '{explore_name}')")
                
                if explore_conditions:
                    base_query += f" AND ({' OR '.join(explore_conditions)})"
            
            result = self.bq_client.query(base_query).result()
            
            refresh_log = {
                'embeddings_updated': result.total_rows if result.total_rows else 0,
                'explores_filtered': explore_ids,
                'success': True
            }
            
            return {
                "tool": "refresh_vector_embeddings",
                "status": "success",
                "result": refresh_log
            }
            
        except Exception as e:
            logger.error(f"Vector embeddings refresh failed: {str(e)}")
            return {
                "tool": "refresh_vector_embeddings",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def _manual_vector_setup(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Manual vector setup implementation if vector manager doesn't have the method."""
        # This would contain manual setup logic if needed
        # For now, return a basic structure
        return {
            'started_at': None,
            'steps_completed': ['manual_setup_placeholder'],
            'success': False,
            'errors': ['Manual setup not implemented - use vector_table_manager directly']
        }
    
    async def _manual_populate_vectors(self, explore_ids: List[str], batch_size: int) -> Dict[str, Any]:
        """Manual vector population if vector manager doesn't have the method."""
        # This would contain manual population logic if needed
        return {
            'started_at': None,
            'explores_processed': [],
            'total_records_added': 0,
            'success': False,
            'errors': ['Manual population not implemented - use vector_table_manager directly']
        }


def add_vector_search_mcp_tools(
    tools_dict,
    bq_client=None,
    project_id=None,
    dataset_id="explore_assistant"
):
    """
    Register vector search management tools into a global tools dict.
    Args:
        tools_dict: The global tools dictionary
        bq_client: BigQuery client (optional, will create if None)
        project_id: GCP project id
        dataset_id: BigQuery dataset id (default: 'explore_assistant')
    """
    if bq_client is None:
        from google.cloud import bigquery as bq_mod
        bq_client = bq_mod.Client(project=project_id)
    vector_integration = VectorSearchMCPIntegration(
        bq_client=bq_client,
        project_id=project_id,
        dataset_id=dataset_id
    )
    tools_dict['check_vector_search_status'] = vector_integration.handle_check_vector_search_status
    tools_dict['setup_vector_search'] = vector_integration.handle_setup_vector_search
    tools_dict['populate_vector_data'] = vector_integration.handle_populate_vector_data
    tools_dict['test_vector_search'] = vector_integration.handle_test_vector_search
    tools_dict['refresh_vector_embeddings'] = vector_integration.handle_refresh_vector_embeddings
    logger.info("Vector search MCP tools added to global tools dict")


# Tool descriptions for MCP server registration
VECTOR_SEARCH_MCP_TOOLS = {
    "check_vector_search_status": {
        "description": "Check the status of the vector search system including tables, models, and data",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "setup_vector_search": {
        "description": "Setup the vector search system by creating tables and embedding models",
        "parameters": {
            "type": "object",
            "properties": {
                "force_refresh": {
                    "type": "boolean",
                    "description": "Whether to force refresh existing tables and models",
                    "default": False
                }
            },
            "required": []
        }
    },
    "populate_vector_data": {
        "description": "Populate vector search database with field values from Looker explores",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of explore IDs to index (empty means all restricted explores)"
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Number of records to process in each batch",
                    "default": 1000
                }
            },
            "required": []
        }
    },
    "test_vector_search": {
        "description": "Test vector search functionality with sample search terms",
        "parameters": {
            "type": "object",
            "properties": {
                "search_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search terms to test",
                    "default": ["nike", "product", "sales"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results per search term",
                    "default": 5
                }
            },
            "required": []
        }
    },
    "refresh_vector_embeddings": {
        "description": "Refresh vector embeddings for existing field data",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter refresh to specific explores (empty means all)"
                }
            },
            "required": []
        }
    }
}
