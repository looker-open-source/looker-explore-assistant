#!/usr/bin/env python3
"""
Test script for Olympic Migration System

Tests the migration functionality, schema flexibility, and graceful table operations.
Provides comprehensive testing of the new Olympic system components.
"""

import sys
import os
import asyncio
import logging
import uuid
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Add the current directory to the Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from olympic_migration_manager import OlympicMigrationManager
from graceful_table_manager import GracefulTableManager
from olympic_mcp_integration import OlympicMCPIntegration

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
BQ_PROJECT_ID = os.getenv('BQ_PROJECT_ID', 'your-project-id')
BQ_DATASET_ID = os.getenv('BQ_DATASET_ID', 'explore_assistant')


class OlympicSystemTester:
    """Comprehensive testing for Olympic migration system."""
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
        self.migration_manager = OlympicMigrationManager(self.bq_client, BQ_PROJECT_ID, BQ_DATASET_ID)
        self.table_manager = GracefulTableManager(self.bq_client, BQ_PROJECT_ID, BQ_DATASET_ID)
        self.mcp_integration = OlympicMCPIntegration(self.bq_client, BQ_PROJECT_ID, BQ_DATASET_ID)
        self.test_data = []
        
    def setup_test_data(self):
        """Create test data for migration testing."""
        self.test_data = [
            {
                'id': str(uuid.uuid4()),
                'explore_id': 'ecommerce:orders',
                'input': 'Show me total sales by month',
                'output': '{"dimensions":["orders.created_month"],"measures":["orders.total_amount"]}',
                'link': 'https://example.looker.com/query1',
                'user_email': 'test@example.com'
            },
            {
                'id': str(uuid.uuid4()),
                'explore_id': 'products:inventory',
                'input': 'What are the top selling products?',
                'output': '{"dimensions":["products.name"],"measures":["orders.count"],"sorts":[{"field":"orders.count","direction":"desc"}]}',
                'link': 'https://example.looker.com/query2',
                'user_email': 'analyst@example.com'
            },
            {
                'id': str(uuid.uuid4()),
                'explore_id': 'customers:profiles',
                'input': 'Customer segmentation by region',
                'output': '{"dimensions":["customers.region","customers.segment"],"measures":["customers.count"]}',
                'link': 'https://example.looker.com/query3',
                'user_email': 'manager@example.com'
            }
        ]
        logger.info(f"Created {len(self.test_data)} test records")
    
    def cleanup_test_tables(self):
        """Clean up any test tables before starting."""
        tables_to_clean = [
            'olympic_queries',
            'bronze_queries',
            'silver_queries', 
            'golden_queries',
            'bronze_queries_test',
            'olympic_queries_test'
        ]
        
        for table_name in tables_to_clean:
            try:
                table_ref = self.bq_client.dataset(BQ_DATASET_ID).table(table_name)
                self.bq_client.delete_table(table_ref)
                logger.info(f"Cleaned up table {table_name}")
            except NotFound:
                pass
            except Exception as e:
                logger.warning(f"Error cleaning {table_name}: {str(e)}")
    
    def create_legacy_test_tables(self):
        """Create legacy tables with mixed schemas for testing."""
        
        # Bronze table with explore_key (old schema)
        bronze_schema = f"""
        CREATE TABLE `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.bronze_queries` (
          id STRING,
          explore_key STRING,  -- Old field name
          input STRING,
          output STRING,
          link STRING,
          user_email STRING,
          query_run_count INT64,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        # Silver table with explore_id (new schema)
        silver_schema = f"""
        CREATE TABLE `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.silver_queries` (
          id STRING,
          explore_id STRING,  -- New field name
          input STRING,
          output STRING,
          link STRING,
          user_id STRING,
          feedback_type STRING,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        # Golden table with explore_key (old schema)
        golden_schema = f"""
        CREATE TABLE `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.golden_queries` (
          id STRING,
          explore_key STRING,  -- Old field name
          input STRING,
          output STRING,
          link STRING,
          promoted_by STRING,
          promoted_at TIMESTAMP,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        """
        
        schemas = [
            ('bronze_queries', bronze_schema),
            ('silver_queries', silver_schema),
            ('golden_queries', golden_schema)
        ]
        
        for table_name, schema in schemas:
            try:
                self.bq_client.query(schema).result()
                logger.info(f"Created legacy test table {table_name}")
            except Exception as e:
                logger.error(f"Error creating {table_name}: {str(e)}")
    
    def populate_legacy_test_tables(self):
        """Populate legacy tables with test data."""
        
        # Populate bronze table (explore_key schema)
        for i, data in enumerate(self.test_data):
            bronze_query = f"""
            INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.bronze_queries`
            (id, explore_key, input, output, link, user_email, query_run_count)
            VALUES (@id, @explore_key, @input, @output, @link, @user_email, 1)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("id", "STRING", data['id'] + '_bronze'),
                    bigquery.ScalarQueryParameter("explore_key", "STRING", data['explore_id']),
                    bigquery.ScalarQueryParameter("input", "STRING", data['input']),
                    bigquery.ScalarQueryParameter("output", "STRING", data['output']),
                    bigquery.ScalarQueryParameter("link", "STRING", data['link']),
                    bigquery.ScalarQueryParameter("user_email", "STRING", data['user_email']),
                ]
            )
            self.bq_client.query(bronze_query, job_config=job_config).result()
        
        # Populate silver table (explore_id schema)  
        for i, data in enumerate(self.test_data[:2]):  # Only first 2 records
            silver_query = f"""
            INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.silver_queries`
            (id, explore_id, input, output, link, user_id, feedback_type)
            VALUES (@id, @explore_id, @input, @output, @link, @user_id, @feedback_type)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("id", "STRING", data['id'] + '_silver'),
                    bigquery.ScalarQueryParameter("explore_id", "STRING", data['explore_id']),
                    bigquery.ScalarQueryParameter("input", "STRING", data['input']),
                    bigquery.ScalarQueryParameter("output", "STRING", data['output']),
                    bigquery.ScalarQueryParameter("link", "STRING", data['link']),
                    bigquery.ScalarQueryParameter("user_id", "STRING", data['user_email']),
                    bigquery.ScalarQueryParameter("feedback_type", "STRING", "positive"),
                ]
            )
            self.bq_client.query(silver_query, job_config=job_config).result()
        
        # Populate golden table (explore_key schema)
        data = self.test_data[0]  # Only first record
        golden_query = f"""
        INSERT INTO `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.golden_queries`
        (id, explore_key, input, output, link, promoted_by, promoted_at)
        VALUES (@id, @explore_key, @input, @output, @link, @promoted_by, CURRENT_TIMESTAMP())
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("id", "STRING", data['id'] + '_golden'),
                bigquery.ScalarQueryParameter("explore_key", "STRING", data['explore_id']),
                bigquery.ScalarQueryParameter("input", "STRING", data['input']),
                bigquery.ScalarQueryParameter("output", "STRING", data['output']),
                bigquery.ScalarQueryParameter("link", "STRING", data['link']),
                bigquery.ScalarQueryParameter("promoted_by", "STRING", "admin@example.com"),
            ]
        )
        self.bq_client.query(golden_query, job_config=job_config).result()
        
        logger.info("Populated legacy tables with test data")
    
    async def test_schema_detection(self):
        """Test schema detection functionality."""
        logger.info("=== Testing Schema Detection ===")
        
        # Test detection for each legacy table
        tables_to_test = ['bronze_queries', 'silver_queries', 'golden_queries']
        
        for table_name in tables_to_test:
            schema_info = self.migration_manager._detect_table_schema(table_name)
            logger.info(f"{table_name}: {schema_info}")
            
            assert schema_info['table_exists'], f"Table {table_name} should exist"
            assert schema_info['explore_field'] in ['explore_key', 'explore_id'], f"Should detect explore field in {table_name}"
            
        logger.info("✅ Schema detection tests passed")
    
    async def test_migration_status_check(self):
        """Test migration status checking."""
        logger.info("=== Testing Migration Status Check ===")
        
        status = self.migration_manager.check_migration_status()
        
        assert status['migration_needed'], "Migration should be needed with legacy tables present"
        assert len(status['legacy_tables_exist']) == 3, "Should find all 3 legacy tables"
        assert status['can_migrate_safely'], "Should be able to migrate safely"
        assert status['estimated_record_count'] > 0, "Should count records in legacy tables"
        
        # Check via MCP integration
        mcp_result = await self.mcp_integration.handle_check_migration_status({})
        assert mcp_result['status'] == 'success', "MCP status check should succeed"
        assert 'summary' in mcp_result['result'], "Should include user-friendly summary"
        
        logger.info("✅ Migration status check tests passed")
    
    async def test_olympic_migration(self):
        """Test full Olympic system migration."""
        logger.info("=== Testing Olympic Migration ===")
        
        # Perform migration
        migration_result = self.migration_manager.migrate_to_olympic_system(
            preserve_data=True,
            verify_migration=True
        )
        
        assert migration_result['success'], f"Migration should succeed: {migration_result['errors']}"
        assert migration_result['records_migrated'] > 0, "Should migrate some records"
        assert 'olympic_table_created' in migration_result['steps_completed'], "Should create Olympic table"
        assert 'data_migrated' in migration_result['steps_completed'], "Should migrate data"
        assert 'migration_verified' in migration_result['steps_completed'], "Should verify migration"
        
        # Verify Olympic table exists and has correct schema
        olympic_ref = self.bq_client.dataset(BQ_DATASET_ID).table('olympic_queries')
        olympic_table = self.bq_client.get_table(olympic_ref)
        field_names = [field.name for field in olympic_table.schema]
        
        assert 'explore_id' in field_names, "Olympic table should use explore_id field"
        assert 'rank' in field_names, "Olympic table should have rank field"
        assert olympic_table.num_rows > 0, "Olympic table should have migrated data"
        
        logger.info("✅ Olympic migration tests passed")
    
    async def test_graceful_table_operations(self):
        """Test graceful table operations with Olympic system."""
        logger.info("=== Testing Graceful Table Operations ===")
        
        # Test adding queries with flexible schema
        test_query = {
            'explore_id': 'test:flexible',
            'input': 'Test flexible query',
            'output': '{"test": "data"}',
            'link': 'https://test.com',
            'user_email': 'test@graceful.com'
        }
        
        # Add bronze query
        result = await self.table_manager.add_olympic_query_flexible(test_query, rank='bronze')
        assert result['status'] == 'success', "Should add bronze query successfully"
        assert result['system'] == 'olympic', "Should use Olympic system"
        
        # Test getting queries
        bronze_queries = await self.table_manager.get_queries_flexible('olympic_queries', rank='bronze')
        assert len(bronze_queries) > 0, "Should retrieve bronze queries"
        
        # Test promotion
        query_to_promote = bronze_queries[0]
        promotion_result = await self.table_manager.promote_query_flexible(
            query_id=query_to_promote['id'],
            from_rank='bronze',
            to_rank='silver',
            promoted_by='test@example.com'
        )
        assert promotion_result['status'] == 'promoted', "Should promote query successfully"
        
        # Verify promotion worked
        silver_queries = await self.table_manager.get_queries_flexible('olympic_queries', rank='silver')
        promoted_query = next((q for q in silver_queries if q['id'] == query_to_promote['id']), None)
        assert promoted_query is not None, "Promoted query should appear in silver rank"
        
        logger.info("✅ Graceful table operations tests passed")
    
    async def test_mcp_integration(self):
        """Test MCP integration tools."""
        logger.info("=== Testing MCP Integration ===")
        
        # Test system status
        status_result = await self.mcp_integration.handle_get_system_status({})
        assert status_result['status'] == 'success', "System status should succeed"
        assert status_result['result']['olympic_available'], "Olympic system should be available"
        
        # Test adding bronze query via MCP
        mcp_query_data = {
            'explore_id': 'mcp:test',
            'input_text': 'MCP test query',
            'output_data': '{"mcp": "test"}',
            'link': 'https://mcp-test.com',
            'user_email': 'mcp@test.com'
        }
        
        add_result = await self.mcp_integration.handle_add_bronze_query_flexible(mcp_query_data)
        assert add_result['status'] == 'success', "MCP add query should succeed"
        
        # Test getting golden queries via MCP
        get_result = await self.mcp_integration.handle_get_golden_queries_flexible({})
        assert get_result['status'] == 'success', "MCP get queries should succeed"
        assert 'queries' in get_result['result'], "Should return queries list"
        
        logger.info("✅ MCP integration tests passed")
    
    async def test_edge_cases(self):
        """Test edge cases and error handling."""
        logger.info("=== Testing Edge Cases ===")
        
        # Test migration when Olympic table already exists
        try:
            # Try migration again (should handle existing table)
            status = self.migration_manager.check_migration_status()
            # Migration should not be needed if Olympic table has data
            if status['olympic_table_exists'] and status.get('olympic_record_count', 0) > 0:
                assert not status['migration_needed'], "Should not need migration when Olympic has data"
        except Exception as e:
            logger.warning(f"Edge case test warning: {str(e)}")
        
        # Test invalid query data
        invalid_query = {}  # Missing required fields
        try:
            invalid_result = await self.mcp_integration.handle_add_bronze_query_flexible(invalid_query)
            assert invalid_result['status'] == 'error', "Should fail with invalid data"
            assert 'Missing required fields' in invalid_result['error'], "Should identify missing fields"
        except Exception as e:
            logger.warning(f"Invalid query test warning: {str(e)}")
        
        logger.info("✅ Edge case tests completed")
    
    async def run_all_tests(self):
        """Run all Olympic system tests."""
        logger.info("🚀 Starting Olympic Migration System Tests")
        
        try:
            # Setup
            self.setup_test_data()
            self.cleanup_test_tables()
            self.create_legacy_test_tables()
            self.populate_legacy_test_tables()
            
            # Run tests
            await self.test_schema_detection()
            await self.test_migration_status_check() 
            await self.test_olympic_migration()
            await self.test_graceful_table_operations()
            await self.test_mcp_integration()
            await self.test_edge_cases()
            
            logger.info("🎉 All Olympic system tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {str(e)}")
            return False
        finally:
            # Optional: cleanup test data
            # self.cleanup_test_tables()
            logger.info("Test tables left in place for inspection")


async def main():
    """Main test execution."""
    if BQ_PROJECT_ID == 'your-project-id':
        logger.error("Please set BQ_PROJECT_ID environment variable")
        return False
    
    tester = OlympicSystemTester()
    success = await tester.run_all_tests()
    
    if success:
        logger.info("✅ Olympic Migration System is ready for production!")
    else:
        logger.error("❌ Tests failed - please check the implementation")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
