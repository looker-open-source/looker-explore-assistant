"""
MCP Integration for Olympic Migration System

Provides MCP tools for migration management and graceful table operations.
Integrates with the looker_mcp_server.py to provide migration capabilities.
"""

from typing import Dict, Any, List
import logging
from google.cloud import bigquery
from .olympic_migration_manager import OlympicMigrationManager
from .graceful_table_manager import GracefulTableManager
from .vector_table_manager import VectorTableManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OlympicMCPIntegration:
    """
    MCP integration layer for Olympic migration system.
    Provides tools for migration management and graceful table operations.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str = "explore_assistant"):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.migration_manager = OlympicMigrationManager(bq_client, project_id, dataset_id)
        self.table_manager = GracefulTableManager(bq_client, project_id, dataset_id)
        self.vector_manager = VectorTableManager(bq_client, project_id, dataset_id)
    
    async def handle_check_migration_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to check if migration to Olympic system is needed.
        
        Args:
            arguments: Tool arguments (empty for this tool)
            
        Returns:
            dict: Migration status information
        """
        try:
            logger.info("Checking Olympic migration status via MCP")
            status = self.migration_manager.check_migration_status()
            
            # Add user-friendly summary
            status['summary'] = self._generate_status_summary(status)
            
            return {
                "tool": "check_migration_status",
                "status": "success",
                "result": status
            }
            
        except Exception as e:
            logger.error(f"Migration status check failed: {str(e)}")
            return {
                "tool": "check_migration_status", 
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_migrate_to_olympic_system(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to perform migration to Olympic system.
        
        Args:
            arguments: Tool arguments including preserve_data and verify_migration flags
            
        Returns:
            dict: Migration results
        """
        preserve_data = arguments.get('preserve_data', True)
        verify_migration = arguments.get('verify_migration', True)
        
        try:
            logger.info(f"Starting Olympic migration via MCP (preserve_data={preserve_data}, verify={verify_migration})")
            
            # Pre-migration validation
            status = self.migration_manager.check_migration_status()
            if not status['can_migrate_safely']:
                return {
                    "tool": "migrate_to_olympic_system",
                    "status": "error", 
                    "error": "Migration cannot proceed safely due to schema issues",
                    "details": status['schema_issues'],
                    "result": None
                }
            
            # Perform migration
            migration_result = self.migration_manager.migrate_to_olympic_system(
                preserve_data=preserve_data,
                verify_migration=verify_migration
            )
            
            # Add user-friendly summary
            migration_result['summary'] = self._generate_migration_summary(migration_result)
            
            return {
                "tool": "migrate_to_olympic_system",
                "status": "success" if migration_result['success'] else "error",
                "result": migration_result
            }
            
        except Exception as e:
            logger.error(f"Olympic migration failed: {str(e)}")
            return {
                "tool": "migrate_to_olympic_system",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_get_system_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to get current table system status.
        
        Args:
            arguments: Tool arguments (empty for this tool)
            
        Returns:
            dict: System status information
        """
        try:
            logger.info("Getting system status via MCP")
            status = self.table_manager.get_system_status()
            
            # Add migration recommendation
            status['migration_recommendation'] = self._generate_migration_recommendation(status)
            
            return {
                "tool": "get_system_status",
                "status": "success",
                "result": status
            }
            
        except Exception as e:
            logger.error(f"System status check failed: {str(e)}")
            return {
                "tool": "get_system_status",
                "status": "error", 
                "error": str(e),
                "result": None
            }
    
    async def handle_add_bronze_query_flexible(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to add bronze query with flexible schema handling.
        
        Args:
            arguments: Query data including explore_id, input_text, output_data, link, user_email
            
        Returns:
            dict: Addition result
        """
        try:
            # Validate required arguments
            required_fields = ['explore_id', 'input_text', 'output_data', 'link', 'user_email']
            missing_fields = [field for field in required_fields if field not in arguments]
            
            if missing_fields:
                return {
                    "tool": "add_bronze_query_flexible",
                    "status": "error",
                    "error": f"Missing required fields: {missing_fields}",
                    "result": None
                }
            
            # Prepare data for insertion
            data = {
                'explore_id': arguments['explore_id'],
                'input': arguments['input_text'],
                'output': arguments['output_data'],
                'link': arguments['link'],
                'user_email': arguments['user_email']
            }
            
            # Try Olympic system first
            try:
                result = await self.table_manager.add_olympic_query_flexible(data, rank='bronze')
                return {
                    "tool": "add_bronze_query_flexible",
                    "status": "success",
                    "result": result
                }
            except Exception as olympic_error:
                logger.warning(f"Olympic system failed, trying legacy: {str(olympic_error)}")
                
                # Fallback to legacy bronze table
                legacy_result = await self.table_manager.add_legacy_query_flexible('bronze_queries', data)
                return {
                    "tool": "add_bronze_query_flexible",
                    "status": "success",
                    "result": legacy_result,
                    "fallback_used": True
                }
                
        except Exception as e:
            logger.error(f"Add bronze query failed: {str(e)}")
            return {
                "tool": "add_bronze_query_flexible",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_get_golden_queries_flexible(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to get golden queries with flexible schema handling.
        
        Args:
            arguments: Filter criteria including optional explore_id
            
        Returns:
            dict: Query results
        """
        explore_id = arguments.get('explore_id')
        limit = arguments.get('limit', 100)
        
        try:
            logger.info(f"Getting golden queries via MCP (explore_id={explore_id}, limit={limit})")
            
            # Try Olympic system first
            olympic_queries = await self.table_manager.get_queries_flexible(
                'olympic_queries', explore_id, rank='gold', limit=limit
            )
            
            if olympic_queries:
                return {
                    "tool": "get_golden_queries_flexible",
                    "status": "success",
                    "result": {
                        "queries": olympic_queries,
                        "source": "olympic_system",
                        "count": len(olympic_queries)
                    }
                }
            
            # Fallback to legacy golden table
            legacy_queries = await self.table_manager.get_queries_flexible(
                'golden_queries', explore_id, limit=limit
            )
            
            return {
                "tool": "get_golden_queries_flexible",
                "status": "success", 
                "result": {
                    "queries": legacy_queries,
                    "source": "legacy_system",
                    "count": len(legacy_queries)
                },
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Get golden queries failed: {str(e)}")
            return {
                "tool": "get_golden_queries_flexible",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_promote_query_flexible(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to promote query between ranks with flexible handling.
        
        Args:
            arguments: Promotion data including query_id, from_rank, to_rank, promoted_by
            
        Returns:
            dict: Promotion result
        """
        try:
            # Validate required arguments
            required_fields = ['query_id', 'from_rank', 'to_rank', 'promoted_by']
            missing_fields = [field for field in required_fields if field not in arguments]
            
            if missing_fields:
                return {
                    "tool": "promote_query_flexible",
                    "status": "error",
                    "error": f"Missing required fields: {missing_fields}",
                    "result": None
                }
            
            result = await self.table_manager.promote_query_flexible(
                query_id=arguments['query_id'],
                from_rank=arguments['from_rank'],
                to_rank=arguments['to_rank'],
                promoted_by=arguments['promoted_by']
            )
            
            return {
                "tool": "promote_query_flexible",
                "status": "success",
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Promote query failed: {str(e)}")
            return {
                "tool": "promote_query_flexible",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    def _generate_status_summary(self, status: Dict[str, Any]) -> str:
        """Generate user-friendly summary of migration status."""
        if not status['migration_needed']:
            if status['olympic_table_exists']:
                return "✅ Olympic system is active and ready"
            else:
                return "ℹ️ No migration needed - system is properly configured"
        
        legacy_count = len(status['legacy_tables_exist'])
        total_records = status['estimated_record_count']
        
        summary = f"🔄 Migration available: {legacy_count} legacy tables with {total_records} total records"
        
        if not status['can_migrate_safely']:
            summary += " ⚠️ Manual intervention required for schema issues"
        else:
            summary += " ✅ Safe to migrate automatically"
            
        return summary
    
    def _generate_migration_summary(self, migration_result: Dict[str, Any]) -> str:
        """Generate user-friendly summary of migration results."""
        if migration_result['success']:
            records = migration_result['records_migrated']
            steps = len(migration_result['steps_completed'])
            return f"✅ Migration completed: {records} records migrated in {steps} steps"
        else:
            errors = len(migration_result['errors'])
            return f"❌ Migration failed with {errors} error(s)"
    
    def _generate_migration_recommendation(self, status: Dict[str, Any]) -> str:
        """Generate migration recommendation based on system status."""
        if not status['olympic_available'] and status['legacy_tables']:
            return "🔄 Recommend migrating to Olympic system for better performance and unified management"
        elif status['olympic_available'] and status['legacy_tables']:
            return "🧹 Consider cleaning up legacy tables after verifying Olympic system is working properly"
        elif status['olympic_available']:
            return "✅ Olympic system is active - no migration needed"
        else:
            return "ℹ️ No query data found - system will create Olympic table when first query is added"


def add_olympic_mcp_tools(mcp_server):
    """
    Add Olympic migration tools to an existing MCP server.
    
    Args:
        mcp_server: The MCP server instance to add tools to
    """
    
    # Initialize Olympic MCP integration
    olympic_integration = OlympicMCPIntegration(
        bq_client=mcp_server.bq_client,
        project_id=mcp_server.project_id,
        dataset_id=mcp_server.dataset_id
    )
    
    # Add migration management tools
    mcp_server.tools['check_migration_status'] = olympic_integration.handle_check_migration_status
    mcp_server.tools['migrate_to_olympic_system'] = olympic_integration.handle_migrate_to_olympic_system
    mcp_server.tools['get_system_status'] = olympic_integration.handle_get_system_status
    
    # Add flexible query management tools
    mcp_server.tools['add_bronze_query_flexible'] = olympic_integration.handle_add_bronze_query_flexible
    mcp_server.tools['get_golden_queries_flexible'] = olympic_integration.handle_get_golden_queries_flexible
    mcp_server.tools['promote_query_flexible'] = olympic_integration.handle_promote_query_flexible
    
    logger.info("Olympic MCP tools added to server")


# Tool descriptions for MCP server registration
OLYMPIC_MCP_TOOLS = {
    "check_migration_status": {
        "description": "Check if migration from legacy three-table system to Olympic system is needed",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "migrate_to_olympic_system": {
        "description": "Migrate from legacy Bronze/Silver/Golden tables to unified Olympic table system",
        "parameters": {
            "type": "object", 
            "properties": {
                "preserve_data": {
                    "type": "boolean",
                    "description": "Whether to preserve data during migration",
                    "default": True
                },
                "verify_migration": {
                    "type": "boolean", 
                    "description": "Whether to verify migration completed successfully",
                    "default": True
                }
            },
            "required": []
        }
    },
    "get_system_status": {
        "description": "Get current table system status including Olympic and legacy table information",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "add_bronze_query_flexible": {
        "description": "Add bronze query with flexible schema handling (works with both Olympic and legacy systems)",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_id": {"type": "string", "description": "Explore identifier"},
                "input_text": {"type": "string", "description": "User input query text"},
                "output_data": {"type": "string", "description": "Generated query output"},
                "link": {"type": "string", "description": "Link to query results"},
                "user_email": {"type": "string", "description": "Email of user who created query"}
            },
            "required": ["explore_id", "input_text", "output_data", "link", "user_email"]
        }
    },
    "get_golden_queries_flexible": {
        "description": "Get golden queries with flexible schema handling",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_id": {"type": "string", "description": "Filter by explore ID (optional)"},
                "limit": {"type": "integer", "description": "Maximum number of queries to return", "default": 100}
            },
            "required": []
        }
    },
    "promote_query_flexible": {
        "description": "Promote query between ranks (bronze → silver → gold) with flexible handling",
        "parameters": {
            "type": "object",
            "properties": {
                "query_id": {"type": "string", "description": "ID of query to promote"},
                "from_rank": {"type": "string", "description": "Current rank (bronze, silver, gold)"},
                "to_rank": {"type": "string", "description": "Target rank (bronze, silver, gold)"},
                "promoted_by": {"type": "string", "description": "User performing the promotion"}
            },
            "required": ["query_id", "from_rank", "to_rank", "promoted_by"]
        }
    }
}
