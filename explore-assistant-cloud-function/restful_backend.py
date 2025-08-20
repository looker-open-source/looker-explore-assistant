#!/usr/bin/env python3
"""
Looker Explore Assistant REST API Backend

Production-ready REST API server using Flask + Gunicorn for the Looker Explore Assistant.
Replaces mcp_server.py with a modern, modular architecture and production-ready deployment.

Features:
- Production WSGI server support (Gunicorn)
- Modern modular architecture using new modules
- Clean REST API endpoints with consistent patterns
- Proper error handling and logging
- Cloud Run optimized configuration
"""

import os
import json
import logging
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple

from flask import Flask, request, Response, jsonify, Blueprint
from flask_cors import CORS
from google.cloud import bigquery
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import looker_sdk
from looker_sdk.rtl import api_settings

# Import from new modular architecture
from core.config import get_environment_config, VERTEX_MODEL
from core.auth import extract_user_info_from_token
from core.exceptions import ParameterGenerationError
from core.models import QueryParameters, GenerationResult
from vertex.client import call_vertex_ai_with_retry
from parameter_generation import generate_explore_params_from_query, validate_explore_parameters
from explore_selection import determine_explore_from_prompt
from vector_search.client import VectorSearchClient

# Import legacy utilities still needed
from llm_utils import parse_llm_response
from olympic_query_manager import OlympicQueryManager, QueryRank
from olympic_mcp_integration import OlympicMCPIntegration
from field_lookup_service import FieldValueLookupService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "bytecode-analysis")
BQ_DATASET_ID = os.environ.get("BQ_DATASET_ID", "looker_scratch")


class RestfulBackendError(Exception):
    """Custom exception for REST API errors"""
    def __init__(self, message: str, status_code: int = 500, details: Dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


def create_app() -> Flask:
    """
    Application factory for creating the Flask app.
    
    This pattern allows for better testing and configuration management.
    """
    app = Flask(__name__)
    
    # Load configuration
    config = get_environment_config()
    app.config.update(config)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Initialize services
    _initialize_services(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    logger.info("✅ Restful backend application created successfully")
    return app


def _initialize_services(app: Flask) -> None:
    """Initialize external services and store in app context"""
    try:
        # Initialize BigQuery client
        app.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
        logger.info("✅ BigQuery client initialized")
        
        # Initialize Olympic query manager
        app.olympic_manager = OlympicQueryManager(
            bq_client=app.bq_client,
            project_id=BQ_PROJECT_ID,
            dataset_id=BQ_DATASET_ID
        )
        logger.info("✅ Olympic query manager initialized")
        
        # Initialize field lookup service
        app.field_lookup = FieldValueLookupService()
        logger.info("✅ Field lookup service initialized")
        
        # Initialize vector search client
        app.vector_search = VectorSearchClient()
        logger.info("✅ Vector search client initialized")
        
        # Initialize Looker SDK
        _initialize_looker_sdk(app)
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise


def _initialize_looker_sdk(app: Flask) -> None:
    """Initialize Looker SDK with proper configuration"""
    try:
        # Get Looker configuration from environment
        looker_config = api_settings.ApiSettings(
            base_url=os.environ.get("LOOKER_BASE_URL"),
            client_id=os.environ.get("LOOKER_CLIENT_ID"),
            client_secret=os.environ.get("LOOKER_CLIENT_SECRET"),
            verify_ssl=True
        )
        
        app.looker_sdk = looker_sdk.init40(config_settings=looker_config)
        logger.info("✅ Looker SDK initialized")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize Looker SDK: {e}")
        app.looker_sdk = None


def _register_blueprints(app: Flask) -> None:
    """Register API blueprints"""
    
    # Main API blueprint
    api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
    
    @api_v1.route('/query', methods=['POST', 'OPTIONS'])
    def handle_query():
        """Main query processing endpoint"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            # Extract request data
            data = request.get_json()
            if not data:
                raise RestfulBackendError("No JSON data provided", 400)
            
            # Extract user info from auth header
            auth_header = request.headers.get('Authorization', '')
            user_info = extract_user_info_from_token(auth_header)
            
            # Process the query
            result = _process_query_request(data, auth_header, user_info)
            
            return jsonify({
                "success": True,
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Unexpected error in query endpoint: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Internal server error: {str(e)}", 500))
    
    @api_v1.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint for Cloud Run"""
        try:
            # Basic health checks
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "bigquery": "unknown",
                    "vertex_ai": "unknown",
                    "looker_sdk": "unknown"
                }
            }
            
            # Check BigQuery
            try:
                list(app.bq_client.query("SELECT 1").result())
                health_status["services"]["bigquery"] = "healthy"
            except Exception:
                health_status["services"]["bigquery"] = "unhealthy"
            
            # Check Looker SDK
            if app.looker_sdk:
                try:
                    app.looker_sdk.me()
                    health_status["services"]["looker_sdk"] = "healthy"
                except Exception:
                    health_status["services"]["looker_sdk"] = "unhealthy"
            
            return jsonify(health_status)
            
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @api_v1.route('/system-status', methods=['GET'])
    def system_status():
        """Get comprehensive system status"""
        try:
            # Initialize the system status service
            from core.system_status import SystemStatusService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            status_service = SystemStatusService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Get comprehensive status
            status_data = status_service.get_comprehensive_status()
            
            return jsonify({
                "success": True,
                "data": status_data
            })
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return jsonify({
                "success": False,
                "error": str(e),
                "data": {
                    "system_status": "error",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_message": str(e)
                }
            }), 500
    
    @api_v1.route('/system-status/migration', methods=['GET'])
    def system_migration_status():
        """Get migration-specific system status"""
        try:
            # Initialize the system status service
            from core.system_status import SystemStatusService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            status_service = SystemStatusService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Get migration status
            migration_data = status_service.get_migration_status()
            
            return jsonify({
                "success": True,
                "data": migration_data
            })
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @api_v1.route('/system-status/health', methods=['GET'])
    def quick_health_check():
        """Quick health check endpoint (lighter than full system status)"""
        try:
            from core.system_status import SystemStatusService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            status_service = SystemStatusService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Get quick health check
            health_data = status_service.get_quick_health_check()
            
            return jsonify({
                "success": True,
                "data": health_data
            })
            
        except Exception as e:
            logger.error(f"Error in quick health check: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @api_v1.route('/vertex-proxy', methods=['POST', 'OPTIONS'])
    def vertex_proxy():
        """Vertex AI API proxy endpoint"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            # Extract request data
            data = request.get_json()
            if not data:
                raise RestfulBackendError("No JSON data provided", 400)
            
            # Extract auth header
            auth_header = request.headers.get('Authorization', '')
            
            # Call Vertex AI
            result = call_vertex_ai_with_retry(
                data, 
                context="vertex_proxy",
                process_response=True
            )
            
            return jsonify({
                "success": True,
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Vertex proxy error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Vertex AI error: {str(e)}", 500))
    
    # Register the blueprint
    app.register_blueprint(api_v1)
    
    # Add admin endpoints
    _register_admin_endpoints(app)
    
    # Add legacy endpoints for compatibility
    _register_legacy_endpoints(app)


def _register_admin_endpoints(app: Flask) -> None:
    """Register admin endpoints"""
    
    admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1/admin')
    
    @admin_bp.route('/queries/<table_name>', methods=['GET', 'OPTIONS'])
    def get_queries(table_name: str):
        """Get queries from specified table"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            # Validate table name
            if table_name not in ['bronze', 'silver', 'gold']:
                raise RestfulBackendError(f"Invalid table name: {table_name}", 400)
            
            # Get queries using Olympic manager
            queries = app.olympic_manager.get_queries_by_rank(
                QueryRank[table_name.upper()]
            )
            
            return jsonify({
                "success": True,
                "data": queries,
                "table": table_name,
                "count": len(queries)
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Admin queries error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to get queries: {str(e)}", 500))
    
    @admin_bp.route('/promote', methods=['POST', 'OPTIONS'])
    def promote_query():
        """Promote a query to higher rank"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            data = request.get_json()
            if not data:
                raise RestfulBackendError("No JSON data provided", 400)

            query_id = data.get('query_id')
            target_rank = data.get('target_rank', '').upper()

            if not query_id:
                raise RestfulBackendError("query_id is required", 400)

            if target_rank not in ['BRONZE', 'SILVER', 'GOLD']:
                raise RestfulBackendError("target_rank must be BRONZE, SILVER, or GOLD", 400)

            # Initialize Olympic service
            from core.olympic_service import OlympicOperationsService, QueryRank
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID

            olympic_service = OlympicOperationsService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )

            # Only include promotion_reason if present and non-empty (not blank/whitespace)
            promote_kwargs = dict(
                query_id=query_id,
                target_rank=QueryRank[target_rank],
                promoted_by=data.get('promoted_by', 'unknown')
            )
            if (
                'promotion_reason' in data
                and data['promotion_reason']
                and str(data['promotion_reason']).strip()
            ):
                promote_kwargs['promotion_reason'] = data['promotion_reason']

            # Promote using shared service
            result = olympic_service.promote_query(**promote_kwargs)

            # If result contains an error, return 400
            if not result or (isinstance(result, dict) and result.get('error')):
                error_msg = result.get('error', 'Failed to promote query') if isinstance(result, dict) else 'Failed to promote query'
                return _handle_api_error(RestfulBackendError(error_msg, 400))

            return jsonify({
                "success": True,
                "data": result,
                "message": f"Query {query_id} promoted to {target_rank}"
            })

        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Query promotion error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to promote query: {str(e)}", 500))
    
    @admin_bp.route('/queries/bronze', methods=['POST', 'OPTIONS'])
    def add_bronze_query():
        """Add a bronze query to the Olympic system"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            data = request.get_json()
            if not data:
                raise RestfulBackendError("No JSON data provided", 400)
            
            # Extract required fields
            explore_id = data.get('explore_id')
            input_text = data.get('input')
            output_data = data.get('output')
            link = data.get('link')
            user_email = data.get('user_email')
            
            # Validate required fields
            if not all([explore_id, input_text, output_data, link, user_email]):
                raise RestfulBackendError(
                    "explore_id, input, output, link, and user_email are required", 400
                )
            
            # Initialize Olympic service
            from core.olympic_service import OlympicOperationsService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            olympic_service = OlympicOperationsService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Add bronze query
            result = olympic_service.add_bronze_query(
                explore_id=explore_id,
                input_text=input_text,
                output_data=output_data,
                link=link,
                user_email=user_email,
                session_id=data.get('session_id')
            )
            
            if not result.get('success'):
                raise RestfulBackendError(result.get('error', 'Failed to add bronze query'), 500)
            
            return jsonify({
                "success": True,
                "data": result,
                "message": "Bronze query added successfully"
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Add bronze query error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to add bronze query: {str(e)}", 500))
    
    @admin_bp.route('/queries/silver', methods=['POST', 'OPTIONS'])
    def add_silver_query():
        """Add a silver query to the Olympic system"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            data = request.get_json()
            if not data:
                raise RestfulBackendError("No JSON data provided", 400)
            
            # Extract required fields
            explore_id = data.get('explore_id')
            input_text = data.get('input')
            output_data = data.get('output')
            link = data.get('link')
            user_id = data.get('user_id')
            feedback_type = data.get('feedback_type')
            
            # Validate required fields
            if not all([explore_id, input_text, output_data, link, user_id, feedback_type]):
                raise RestfulBackendError(
                    "explore_id, input, output, link, user_id, and feedback_type are required", 400
                )
            
            # Initialize Olympic service
            from core.olympic_service import OlympicOperationsService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            olympic_service = OlympicOperationsService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Add silver query
            result = olympic_service.add_silver_query(
                explore_id=explore_id,
                input_text=input_text,
                output_data=output_data,
                link=link,
                user_id=user_id,
                feedback_type=feedback_type,
                conversation_history=data.get('conversation_history')
            )
            
            if not result.get('success'):
                raise RestfulBackendError(result.get('error', 'Failed to add silver query'), 500)
            
            return jsonify({
                "success": True,
                "data": result,
                "message": "Silver query added successfully"
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Add silver query error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to add silver query: {str(e)}", 500))
    
    @admin_bp.route('/queries/<query_id>', methods=['DELETE', 'OPTIONS'])
    def delete_query(query_id: str):
        """Delete a query from the Olympic system"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            data = request.get_json() or {}
            deleted_by = data.get('deleted_by', 'unknown')
            
            # Initialize Olympic service
            from core.olympic_service import OlympicOperationsService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            olympic_service = OlympicOperationsService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Delete query
            result = olympic_service.delete_query(
                query_id=query_id,
                deleted_by=deleted_by
            )
            
            if not result.get('success'):
                raise RestfulBackendError(result.get('error', 'Failed to delete query'), 500)
            
            return jsonify({
                "success": True,
                "data": result,
                "message": f"Query {query_id} deleted successfully"
            })
            
        except RestfulBackendError as e:
            return _handle_api_error(e)
        except Exception as e:
            logger.error(f"Delete query error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to delete query: {str(e)}", 500))
    
    @admin_bp.route('/stats', methods=['GET', 'OPTIONS'])
    def get_query_stats():
        """Get Olympic query statistics"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        try:
            # Initialize Olympic service
            from core.olympic_service import OlympicOperationsService
            from core.config import BQ_PROJECT_ID, BQ_DATASET_ID
            
            olympic_service = OlympicOperationsService(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            
            # Get query stats
            stats = olympic_service.get_query_stats()
            
            return jsonify({
                "success": True,
                "data": stats
            })
            
        except Exception as e:
            logger.error(f"Get query stats error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to get query stats: {str(e)}", 500))
    
    # --- Custom: Disqualified Queries Endpoint ---
    @admin_bp.route('/queries/disqualified', methods=['GET', 'OPTIONS'])
    def get_disqualified_queries():
        """Get queries with rank 'disqualified' from the Olympic system"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        try:
            # Use OlympicQueryManager directly (for legacy/compat)
            queries = app.olympic_manager.get_queries_by_rank(QueryRank.DISQUALIFIED)
            return jsonify({
                "success": True,
                "data": queries,
                "table": "disqualified",
                "count": len(queries)
            })
        except Exception as e:
            logger.error(f"Get disqualified queries error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to get disqualified queries: {str(e)}", 500))

    # --- Custom: Olympic Migration Endpoint ---
    @admin_bp.route('/migrate', methods=['POST', 'OPTIONS'])
    def perform_olympic_migration():
        """Perform migration to the Olympic system (unified table)"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        try:
            data = request.get_json() or {}
            preserve_data = data.get('preserve_data', True)
            verify_migration = data.get('verify_migration', True)
            # Use OlympicMCPIntegration for migration logic
            migration_manager = OlympicMCPIntegration(
                bq_client=app.bq_client,
                project_id=BQ_PROJECT_ID,
                dataset_id=BQ_DATASET_ID
            )
            # The MCP method is async, but we can call it synchronously for Flask
            import asyncio
            migration_result = asyncio.run(
                migration_manager.handle_migrate_to_olympic_system({
                    'preserve_data': preserve_data,
                    'verify_migration': verify_migration
                })
            )
            return jsonify({
                "success": True,
                "data": migration_result
            })
        except Exception as e:
            logger.error(f"Olympic migration error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to perform migration: {str(e)}", 500))

    # --- Vector Search Management Endpoints ---
    @admin_bp.route('/vector-search/status', methods=['GET', 'OPTIONS'])
    def get_vector_search_status():
        """Get comprehensive vector search system status"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        try:
            from vector_table_manager import VectorTableManager
            vector_manager = VectorTableManager()
            
            # Get comprehensive status
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "system_status": "unknown",
                "components": {
                    "bigquery_connection": "unknown",
                    "embedding_model": "unknown",
                    "field_values_table": "unknown",
                    "vector_index": "unknown"
                },
                "statistics": {},
                "recommendations": []
            }
            
            # Check BigQuery connection
            try:
                list(app.bq_client.query("SELECT 1").result())
                status["components"]["bigquery_connection"] = "operational"
            except Exception as e:
                status["components"]["bigquery_connection"] = "failed"
                status["recommendations"].append(f"BigQuery connection failed: {str(e)}")
            
            # Check embedding model
            try:
                model_query = f"""
                SELECT model_name FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.INFORMATION_SCHEMA.MODELS`
                WHERE model_name = 'text_embedding_model'
                """
                results = list(app.bq_client.query(model_query).result())
                if results:
                    status["components"]["embedding_model"] = "operational"
                else:
                    status["components"]["embedding_model"] = "missing"
                    status["recommendations"].append("Text embedding model needs to be created")
            except Exception as e:
                status["components"]["embedding_model"] = "failed"
                status["recommendations"].append(f"Failed to check embedding model: {str(e)}")
            
            # Check field values table and get statistics
            try:
                table_stats = vector_manager.get_table_stats()
                if "error" in table_stats:
                    status["components"]["field_values_table"] = "missing"
                    status["recommendations"].append("Field values table needs to be created")
                else:
                    status["components"]["field_values_table"] = "operational"
                    status["statistics"] = table_stats
            except Exception as e:
                status["components"]["field_values_table"] = "failed"
                status["recommendations"].append(f"Failed to check field values table: {str(e)}")
            
            # Check vector index (optional)
            try:
                index_query = f"""
                SELECT index_name FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.INFORMATION_SCHEMA.VECTOR_INDEXES`
                WHERE table_name = 'field_values_for_vectorization'
                """
                results = list(app.bq_client.query(index_query).result())
                status["components"]["vector_index"] = "operational" if results else "optional"
            except Exception:
                status["components"]["vector_index"] = "optional"
            
            # Determine overall system status
            component_values = list(status["components"].values())
            if "failed" in component_values:
                status["system_status"] = "degraded"
            elif "missing" in component_values:
                status["system_status"] = "needs_setup"
            elif all(v in ["operational", "optional"] for v in component_values):
                status["system_status"] = "operational"
                if not status["recommendations"]:
                    status["recommendations"].append("Vector search system is fully operational")
            else:
                status["system_status"] = "partial"
            
            return jsonify({
                "success": True,
                "data": status
            })
            
        except Exception as e:
            logger.error(f"Vector search status error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to get vector search status: {str(e)}", 500))
    
    @admin_bp.route('/vector-search/setup', methods=['POST', 'OPTIONS'])
    def setup_vector_search_system():
        """Setup the complete vector search system"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        try:
            data = request.get_json() or {}
            force_refresh = data.get('force_refresh', False)
            focus_explore = data.get('focus_explore')
            
            from vector_table_manager import VectorTableManager
            vector_manager = VectorTableManager()
            
            setup_result = {
                "started_at": datetime.utcnow().isoformat(),
                "steps": [],
                "success": False,
                "errors": [],
                "statistics": {}
            }
            
            try:
                # Step 1: Create embedding model
                setup_result["steps"].append("Creating embedding model...")
                logger.info("Setting up embedding model...")
                model_success = vector_manager.create_embedding_model()
                if model_success:
                    setup_result["steps"].append("✅ Embedding model created successfully")
                else:
                    setup_result["errors"].append("❌ Failed to create embedding model")
                    if not force_refresh:
                        raise Exception("Embedding model creation failed")
                
                # Step 2: Create field values table
                setup_result["steps"].append("Creating field values table from Looker explores...")
                logger.info(f"Creating field values table (focus_explore: {focus_explore})")
                table_success = vector_manager.create_field_values_table_from_looker_explores(focus_explore)
                if table_success:
                    setup_result["steps"].append("✅ Field values table created successfully")
                else:
                    setup_result["errors"].append("❌ Failed to create field values table")
                    raise Exception("Field values table creation failed")
                
                # Step 3: Create vector index
                setup_result["steps"].append("Creating vector index...")
                logger.info("Creating vector index...")
                index_success = vector_manager.create_vector_index()
                if index_success:
                    setup_result["steps"].append("✅ Vector index created successfully")
                else:
                    setup_result["steps"].append("⚠️ Vector index creation skipped (not enough data or optional)")
                
                # Step 4: Get final statistics
                setup_result["steps"].append("Gathering final statistics...")
                final_stats = vector_manager.get_table_stats()
                setup_result["statistics"] = final_stats
                
                if "error" not in final_stats:
                    setup_result["steps"].append(f"✅ Setup complete! Indexed {final_stats.get('total_rows', 0)} field values across {final_stats.get('unique_explores', 0)} explores")
                    setup_result["success"] = True
                else:
                    setup_result["errors"].append("Failed to get final statistics")
                
            except Exception as e:
                setup_result["errors"].append(f"Setup failed: {str(e)}")
                logger.error(f"Vector search setup failed: {e}")
            
            setup_result["completed_at"] = datetime.utcnow().isoformat()
            
            return jsonify({
                "success": setup_result["success"],
                "data": setup_result,
                "message": "Vector search system setup completed" if setup_result["success"] else "Vector search system setup failed"
            })
            
        except Exception as e:
            logger.error(f"Vector search setup error: {traceback.format_exc()}")
            return _handle_api_error(RestfulBackendError(f"Failed to setup vector search system: {str(e)}", 500))

    app.register_blueprint(admin_bp)


def _register_legacy_endpoints(app: Flask) -> None:
    """Register legacy endpoints for backward compatibility"""
    
    @app.route('/', methods=['POST', 'OPTIONS'])
    def legacy_root():
        """Legacy root endpoint for backward compatibility"""
        if request.method == 'OPTIONS':
            return _handle_cors()
        
        # Redirect to new API endpoint
        return handle_query()
    
    @app.route('/health', methods=['GET'])
    def legacy_health():
        """Legacy health endpoint"""
        return health_check()
    


def _process_query_request(data: Dict[str, Any], auth_header: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """Process a query request using the new modular architecture"""
    
    # Extract query parameters
    query_text = data.get('query', data.get('prompt', ''))
    if not query_text:
        raise RestfulBackendError("Query text is required", 400)

    conversation_context = data.get('conversation_context', '')
    explore_key = data.get('explore_key')

    # Extract additional context
    restricted_explore_keys = data.get('restricted_explore_keys')
    golden_queries = data.get('golden_queries')
    semantic_models = data.get('semantic_models')

    logger.info(f"🚀 Processing query: {query_text[:100]}...")
    logger.info(f"restricted_explore_keys from request: {restricted_explore_keys}")
    logger.info(f"golden_queries from request: {type(golden_queries)}")
    logger.info(f"semantic_models from request: {type(semantic_models)}")

    try:
        # Step 1: Determine explore if not provided
        if not explore_key:
            explore_key = determine_explore_from_prompt(
                auth_header=auth_header,
                prompt=query_text,
                golden_queries=golden_queries,
                conversation_context=conversation_context,
                restricted_explore_keys=restricted_explore_keys,
                semantic_models=semantic_models
            )

            if not explore_key:
                raise RestfulBackendError("Could not determine appropriate explore", 400)

        # Step 2: Generate parameters using new modular system
        # Optionally, you may want to use the request's golden_queries/semantic_models here as well
        result = generate_explore_params_from_query(
            auth_header=auth_header,
            query=query_text,
            explore_key=explore_key,
            golden_queries=golden_queries,
            semantic_models=semantic_models,
            current_explore={}
        )

        if not result:
            raise RestfulBackendError("Failed to generate query parameters", 500)

        # Step 3: Validate and format parameters
        validated_params = validate_explore_parameters(
            result.get('explore_params', {}),
            explore_key
        )

        # Step 4: Store query for learning (Olympic system)
        _store_query_for_learning(query_text, explore_key, validated_params, user_info)

        return {
            "explore_key": explore_key,
            "parameters": validated_params,
            "generation_metadata": {
                "model_used": result.get('model_used', VERTEX_MODEL),
                "vector_search_used": result.get('vector_search_used', []),
                "generation_method": result.get('generation_method', 'modular_pipeline')
            },
            "user_info": {
                "email": user_info.get('email'),
                "user_id": user_info.get('user_id')
            }
        }

    except ParameterGenerationError as e:
        raise RestfulBackendError(f"Parameter generation failed: {e.message}", 400, {"explore_key": e.explore_key})
    except Exception as e:
        logger.error(f"Query processing error: {traceback.format_exc()}")
        raise RestfulBackendError(f"Query processing failed: {str(e)}", 500)


def _get_available_explores() -> List[str]:
    """Get list of available explores (placeholder implementation)"""
    # This would integrate with your Looker SDK to get actual explores
    return [
        "ecommerce:order_items",
        "ecommerce:users", 
        "ecommerce:events"
    ]


def _get_golden_queries_for_explore(explore_key: str) -> Dict[str, Any]:
    """Get golden queries for a specific explore"""
    try:
        return app.olympic_manager.get_golden_queries_for_explore(explore_key)
    except Exception as e:
        logger.warning(f"Failed to get golden queries for {explore_key}: {e}")
        return {}


def _get_semantic_models() -> Dict[str, Any]:
    """Get semantic models (placeholder implementation)"""
    # This would load your semantic models from storage
    return {}


def _store_query_for_learning(query: str, explore_key: str, params: Dict, user_info: Dict) -> None:
    """Store query in Olympic system for learning"""
    try:
        app.olympic_manager.store_query(
            query_text=query,
            explore_key=explore_key,
            parameters=params,
            user_email=user_info.get('email', 'unknown'),
            rank=QueryRank.BRONZE  # Start as bronze
        )
    except Exception as e:
        logger.warning(f"Failed to store query for learning: {e}")


def _handle_cors() -> Response:
    """Handle CORS preflight requests"""
    response = Response()
    response.headers.update({
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
        'Access-Control-Max-Age': '3600'
    })
    return response


def _handle_api_error(error: RestfulBackendError) -> Tuple[Response, int]:
    """Handle API errors consistently"""
    response_data = {
        "success": False,
        "error": {
            "message": error.message,
            "details": error.details
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    logger.error(f"API Error {error.status_code}: {error.message}")
    return jsonify(response_data), error.status_code


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False,
            "error": {
                "message": "Endpoint not found",
                "details": {"path": request.path}
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "success": False,
            "error": {
                "message": "Internal server error",
                "details": {}
            }
        }), 500


# Create the application instance for Gunicorn
app = create_app()


def handle_query():
    """Helper function for legacy compatibility"""
    # This calls the actual API endpoint
    from flask import current_app
    with current_app.test_request_context():
        return current_app.view_functions['api_v1.handle_query']()


def health_check():
    """Helper function for legacy compatibility"""
    from flask import current_app
    with current_app.test_request_context():
        return current_app.view_functions['api_v1.health_check']()


if __name__ == "__main__":
    # Only for local development - Gunicorn will use the app instance above
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Starting development server on port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)