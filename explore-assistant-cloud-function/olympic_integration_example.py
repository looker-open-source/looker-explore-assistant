"""
Example integration of Olympic Migration System with existing MCP server.

This file shows how to integrate the Olympic migration functionality
into the existing looker_mcp_server.py without disrupting current operations.
"""

# Add this import to the top of looker_mcp_server.py
from olympic_mcp_integration import add_olympic_mcp_tools, OLYMPIC_MCP_TOOLS

class LookerMCPServer:
    """Enhanced MCP Server with Olympic Migration Support"""
    
    def __init__(self, bq_client, project_id, dataset_id="explore_assistant"):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        
        # Existing initialization code...
        self.tools = {}
        
        # Add existing tools
        self._register_existing_tools()
        
        # Add Olympic migration tools
        add_olympic_mcp_tools(self)
        
    def _register_existing_tools(self):
        """Register existing MCP tools (unchanged)"""
        self.tools.update({
            'generate_explore_params': self.handle_generate_explore_params,
            'get_explore_fields': self.handle_get_explore_fields,
            'run_looker_query': self.handle_run_looker_query,
            'add_bronze_query': self.handle_add_bronze_query,
            'get_golden_queries': self.handle_get_golden_queries,
            # ... other existing tools
        })
    
    async def handle_add_bronze_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced bronze query handler with Olympic system integration.
        
        This replaces the existing handler to use flexible schema handling
        while maintaining backward compatibility.
        """
        
        # Try Olympic system first via flexible handling
        if hasattr(self, 'tools') and 'add_bronze_query_flexible' in self.tools:
            try:
                return await self.tools['add_bronze_query_flexible'](arguments)
            except Exception as e:
                logger.warning(f"Olympic system failed, using legacy: {str(e)}")
        
        # Fallback to original implementation
        return await self._legacy_add_bronze_query(arguments)
    
    async def handle_get_golden_queries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced golden query handler with Olympic system integration.
        
        This replaces the existing handler to use flexible schema handling
        while maintaining backward compatibility.
        """
        
        # Try Olympic system first via flexible handling
        if hasattr(self, 'tools') and 'get_golden_queries_flexible' in self.tools:
            try:
                result = await self.tools['get_golden_queries_flexible'](arguments)
                if result['status'] == 'success' and result['result']['queries']:
                    return result['result']  # Return in expected format
            except Exception as e:
                logger.warning(f"Olympic system failed, using legacy: {str(e)}")
        
        # Fallback to original implementation  
        return await self._legacy_get_golden_queries(arguments)
    
    async def _legacy_add_bronze_query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Original bronze query implementation (unchanged)"""
        # Original implementation code here...
        pass
    
    async def _legacy_get_golden_queries(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Original golden query implementation (unchanged)"""
        # Original implementation code here...
        pass

    def get_tool_descriptions(self) -> Dict[str, Any]:
        """
        Get tool descriptions including Olympic migration tools.
        
        Returns:
            dict: Complete tool descriptions for MCP registration
        """
        descriptions = {
            # Existing tool descriptions...
            'generate_explore_params': {
                "description": "Generate explore parameters from natural language prompt",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "restricted_explore_keys": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["prompt", "restricted_explore_keys"]
                }
            },
            # Add Olympic tool descriptions
            **OLYMPIC_MCP_TOOLS
        }
        
        return descriptions


# Example usage in main server initialization
def create_enhanced_mcp_server():
    """Create MCP server with Olympic migration support."""
    
    # Initialize BigQuery client
    bq_client = bigquery.Client(project=BQ_PROJECT_ID)
    
    # Create enhanced server
    server = LookerMCPServer(
        bq_client=bq_client,
        project_id=BQ_PROJECT_ID,
        dataset_id=BQ_DATASET_ID
    )
    
    return server


# Migration trigger example for frontend
def check_and_suggest_migration():
    """
    Example function to check migration status and provide recommendations.
    This could be called during app initialization or periodically.
    """
    
    server = create_enhanced_mcp_server()
    
    # Check if migration tools are available
    if 'check_migration_status' in server.tools:
        try:
            # Check migration status
            status_result = asyncio.run(
                server.tools['check_migration_status']({})
            )
            
            if status_result['status'] == 'success':
                status = status_result['result']
                
                if status['migration_needed']:
                    print("🔄 Olympic migration available:")
                    print(f"   • {len(status['legacy_tables_exist'])} legacy tables found")
                    print(f"   • {status['estimated_record_count']} total records")
                    print(f"   • Migration safety: {'✅ Safe' if status['can_migrate_safely'] else '⚠️ Needs attention'}")
                    
                    if status['can_migrate_safely']:
                        print("\n💡 Recommendation: Run migration to improve performance")
                        print("   Use: await server.tools['migrate_to_olympic_system']({'preserve_data': True})")
                    else:
                        print("\n⚠️  Schema issues detected - manual review needed")
                        for issue in status['schema_issues']:
                            print(f"   • {issue['table']}: {issue['issue']}")
                else:
                    print("✅ Olympic system is active and ready")
        except Exception as e:
            print(f"❌ Migration check failed: {str(e)}")
    else:
        print("ℹ️  Olympic migration tools not available")


# Example migration workflow for operations team
async def perform_safe_migration():
    """
    Example migration workflow with comprehensive safety checks.
    This shows how operations teams can safely migrate systems.
    """
    
    server = create_enhanced_mcp_server()
    
    print("🚀 Starting Olympic Migration Workflow")
    
    # Step 1: Check current system status
    print("\n1️⃣ Checking system status...")
    status_result = await server.tools['get_system_status']({})
    
    if status_result['status'] != 'success':
        print("❌ Cannot get system status - aborting")
        return False
    
    system_status = status_result['result']
    print(f"   Olympic available: {system_status['olympic_available']}")
    print(f"   Legacy tables: {len(system_status['legacy_tables'])}")
    
    # Step 2: Check migration requirements
    print("\n2️⃣ Checking migration requirements...")
    migration_status = await server.tools['check_migration_status']({})
    
    if migration_status['status'] != 'success':
        print("❌ Cannot check migration status - aborting")
        return False
    
    status = migration_status['result']
    print(f"   Migration needed: {status['migration_needed']}")
    print(f"   Can migrate safely: {status['can_migrate_safely']}")
    
    if not status['migration_needed']:
        print("✅ No migration needed - system is ready")
        return True
        
    if not status['can_migrate_safely']:
        print("❌ Migration cannot proceed safely:")
        for issue in status['schema_issues']:
            print(f"   • {issue['table']}: {issue['issue']}")
        return False
    
    # Step 3: Perform migration with verification
    print("\n3️⃣ Performing migration...")
    migration_result = await server.tools['migrate_to_olympic_system']({
        'preserve_data': True,
        'verify_migration': True
    })
    
    if migration_result['status'] != 'success':
        print(f"❌ Migration failed: {migration_result['error']}")
        return False
    
    result = migration_result['result']
    print(f"✅ Migration completed successfully!")
    print(f"   Records migrated: {result['records_migrated']}")
    print(f"   Steps completed: {len(result['steps_completed'])}")
    print(f"   Archive tables: {len(result['archived_tables'])}")
    
    # Step 4: Verify system is working
    print("\n4️⃣ Verifying Olympic system...")
    
    # Test adding a query
    test_query = {
        'explore_id': 'test:migration',
        'input_text': 'Test query after migration',
        'output_data': '{"test": "verification"}',
        'link': 'https://test.com/migration-verify',
        'user_email': 'migration@test.com'
    }
    
    add_result = await server.tools['add_bronze_query_flexible'](test_query)
    
    if add_result['status'] == 'success':
        print("✅ Olympic system operational - test query added successfully")
        print(f"   System used: {add_result['result']['system']}")
        return True
    else:
        print(f"⚠️  Olympic system test failed: {add_result['error']}")
        return False


if __name__ == "__main__":
    """Example of how to run migration workflow"""
    
    # Check migration status
    print("Checking migration status...")
    check_and_suggest_migration()
    
    # Optionally perform migration
    if input("\nProceed with migration? (y/N): ").lower() == 'y':
        success = asyncio.run(perform_safe_migration())
        if success:
            print("\n🎉 Olympic Migration completed successfully!")
        else:
            print("\n💥 Migration failed - please review logs")
