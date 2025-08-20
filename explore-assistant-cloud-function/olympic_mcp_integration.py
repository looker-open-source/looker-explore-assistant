"""
MCP Integration for Olympic Migration System

Provides MCP tools for migration management and graceful table operations.
Integrates with the looker_mcp_server.py to provide migration capabilities.
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
from google.cloud import bigquery
from olympic_migration_manager import OlympicMigrationManager
from olympic_query_manager import OlympicQueryManager
from graceful_table_manager import GracefulTableManager
from vector_table_manager import VectorTableManager

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
        self.olympic_manager = OlympicQueryManager(bq_client, project_id, dataset_id)
        self.table_manager = GracefulTableManager(bq_client, project_id, dataset_id)
        self.vector_manager = VectorTableManager()  # VectorTableManager has no params
    
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
                "tool": "promote_query_flexible", 
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    def _check_olympic_table_exists(self) -> bool:
        """Check if Olympic queries table exists."""
        try:
            self.bq_client.get_table(f"{self.project_id}.{self.dataset_id}.olympic_queries")
            return True
        except Exception:
            return False
    
    def _get_olympic_system_stats(self) -> Dict[str, Any]:
        """Get Olympic system statistics."""
        try:
            # Get total record count
            query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNTIF(rank = 'bronze') as bronze_count,
                COUNTIF(rank = 'silver') as silver_count, 
                COUNTIF(rank = 'gold') as gold_count
            FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
            """
            
            results = list(self.bq_client.query(query).result())
            if results:
                row = results[0]
                return {
                    'total_records': row.total_records,
                    'records_by_rank': {
                        'bronze': row.bronze_count,
                        'silver': row.silver_count,
                        'gold': row.gold_count
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get Olympic system stats: {e}")
        
        return {'total_records': 0, 'records_by_rank': {}}

    def _generate_status_summary(self, status: Dict[str, Any]) -> str:
        """Generate user-friendly summary of system status."""
        if status.get('olympic_table_exists', False):
            olympic_count = status.get('olympic_record_count', 0)
            legacy_count = len(status.get('legacy_tables', []))
            if legacy_count > 0:
                return f"✅ Olympic system active ({olympic_count} records) + {legacy_count} legacy tables"
            else:
                return f"✅ Olympic system active with {olympic_count} records"
        else:
            legacy_count = len(status.get('legacy_tables', []))
            if legacy_count > 0:
                total_records = status.get('estimated_record_count', 0)
                return f"🔄 Legacy system only: {legacy_count} tables with {total_records} records"
            else:
                return "ℹ️ No query system detected - will create Olympic table when first query is added"

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
        MCP tool to get current table system status using shared service.
        
        Args:
            arguments: Tool arguments (empty for this tool)
            
        Returns:
            dict: System status information in MCP format
        """
        try:
            logger.info("Getting system status via MCP using shared service")
            
            # Use shared system status service
            from core.system_status import SystemStatusService
            
            status_service = SystemStatusService(
                bq_client=self.bq_client,
                project_id=self.project_id,
                dataset_id=self.dataset_id
            )
            
            # Get comprehensive status from shared service
            status_data = status_service.get_comprehensive_status()
            
            return {
                "tool": "get_system_status",
                "status": "success",
                "result": status_data
            }
            
        except Exception as e:
            logger.error(f"System status check failed: {str(e)}")
            return {
                "tool": "get_system_status",
                "status": "error", 
                "error": str(e),
                "result": {
                    "system_status": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_message": str(e)
                }
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
    
    async def handle_get_queries_by_rank(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to get queries by rank (bronze, silver, gold).
        
        Args:
            arguments: Query parameters including rank, explore_id (optional), limit (optional)
            
        Returns:
            dict: Query results
        """
        try:
            # Validate required arguments
            if 'rank' not in arguments:
                return {
                    "tool": "get_queries_by_rank",
                    "status": "error", 
                    "error": "Missing required field: rank",
                    "result": None
                }
            
            rank_str = arguments['rank']
            explore_id = arguments.get('explore_id')
            limit = arguments.get('limit', 100)
            
            # Convert rank string to QueryRank enum
            from olympic_query_manager import QueryRank
            try:
                rank_enum = QueryRank(rank_str.lower())
            except ValueError:
                return {
                    "tool": "get_queries_by_rank",
                    "status": "error",
                    "error": f"Invalid rank: {rank_str}. Must be 'bronze', 'silver', or 'gold'",
                    "result": None
                }
            
            # Get queries by rank from the Olympic manager (not async)
            queries = self.olympic_manager.get_queries_by_rank(
                rank=rank_enum,
                explore_id=explore_id,
                limit=limit
            )
            
            return {
                "tool": "get_queries_by_rank",
                "status": "success",
                "result": {
                    "queries": queries,
                    "count": len(queries),
                    "rank": rank_str,
                    "explore_id": explore_id
                }
            }
            
        except Exception as e:
            logger.error(f"Get queries by rank failed: {str(e)}")
            return {
                "tool": "get_queries_by_rank",
                "status": "error",
                "error": str(e),
                "result": None
            }
    
    async def handle_add_feedback_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        MCP tool to add comprehensive feedback query with conversation history.
        Uses SILVER rank for positive feedback, DISQUALIFIED rank for negative feedback.
        
        Args:
            arguments: Feedback data including explore_id, original_prompt, generated_params,
                      share_url, feedback_type, user_id, conversation_context, user_comment,
                      suggested_improvements, issues, query_id
        
        Returns:
            dict: Addition result
        """
        try:
            # Log the BigQuery target information
            logger.info(f"add_feedback_query: Targeting BigQuery table {self.project_id}.{self.dataset_id}.olympic_queries")
            
            # Validate required arguments
            required_fields = ['explore_id', 'original_prompt', 'generated_params', 
                              'share_url', 'feedback_type', 'user_id']
            missing_fields = [field for field in required_fields if field not in arguments]
            
            if missing_fields:
                return {
                    "tool": "add_feedback_query",
                    "status": "error",
                    "error": f"Missing required fields: {missing_fields}",
                    "result": None
                }
            
            # Ensure Olympic table exists and has correct schema
            try:
                self.olympic_manager.ensure_table_exists()
                # Validate schema and fix if needed
                schema_fixed = self.olympic_manager.validate_and_fix_table_schema()
                if schema_fixed:
                    logger.info("Olympic table schema was updated for feedback queries")
            except Exception as schema_error:
                logger.error(f"Failed to validate Olympic table schema: {schema_error}")
                return {
                    "tool": "add_feedback_query",
                    "status": "error", 
                    "error": f"Table schema validation failed: {str(schema_error)}",
                    "result": None
                }
            
            # Add feedback query using Olympic manager
            query_id = self.olympic_manager.add_feedback_query(
                explore_id=arguments['explore_id'],
                original_prompt=arguments['original_prompt'],
                generated_params=arguments['generated_params'],
                share_url=arguments['share_url'],
                feedback_type=arguments['feedback_type'],
                user_id=arguments['user_id'],
                conversation_context=arguments.get('conversation_context'),
                user_comment=arguments.get('user_comment'),
                suggested_improvements=arguments.get('suggested_improvements'),
                issues=arguments.get('issues'),
                query_id=arguments.get('query_id')
            )
            
            # Determine final rank for response
            rank = "disqualified" if arguments['feedback_type'] == 'negative' else "silver"
            
            return {
                "tool": "add_feedback_query",
                "status": "success",
                "result": {
                    "query_id": query_id,
                    "rank": rank,
                    "feedback_type": arguments['feedback_type']
                }
            }
            
        except Exception as e:
            logger.error(f"Add feedback query failed: {str(e)}")
            return {
                "tool": "add_feedback_query",
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
    mcp_server.tools['add_feedback_query'] = olympic_integration.handle_add_feedback_query
    mcp_server.tools['get_golden_queries_flexible'] = olympic_integration.handle_get_golden_queries_flexible
    mcp_server.tools['get_queries_by_rank'] = olympic_integration.handle_get_queries_by_rank
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
    "add_feedback_query": {
        "description": "Add comprehensive feedback query combining conversation history with user feedback (SILVER for positive, DISQUALIFIED for negative)",
        "parameters": {
            "type": "object",
            "properties": {
                "explore_id": {"type": "string", "description": "Explore identifier"},
                "original_prompt": {"type": "string", "description": "User's original query prompt"},
                "generated_params": {"type": "object", "description": "AI-generated query parameters"},
                "share_url": {"type": "string", "description": "URL to shared query"},
                "feedback_type": {"type": "string", "description": "Type of feedback: positive, negative, refinement, alternative"},
                "user_id": {"type": "string", "description": "User who provided feedback"},
                "conversation_context": {"type": "string", "description": "Previous conversation history context"},
                "user_comment": {"type": "string", "description": "User's additional comments"},
                "suggested_improvements": {"type": "string", "description": "Specific improvement suggestions"},
                "issues": {"type": "array", "items": {"type": "string"}, "description": "List of issues for negative feedback"},
                "query_id": {"type": "string", "description": "Optional specific query ID to use"}
            },
            "required": ["explore_id", "original_prompt", "generated_params", "share_url", "feedback_type", "user_id"]
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
    "get_queries_by_rank": {
        "description": "Get queries filtered by rank (bronze, silver, gold) with flexible schema handling",
        "parameters": {
            "type": "object",
            "properties": {
                "rank": {"type": "string", "description": "Query rank to filter by (bronze, silver, gold)"},
                "explore_id": {"type": "string", "description": "Filter by explore ID (optional)"},
                "limit": {"type": "integer", "description": "Maximum number of queries to return", "default": 100}
            },
            "required": ["rank"]
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
