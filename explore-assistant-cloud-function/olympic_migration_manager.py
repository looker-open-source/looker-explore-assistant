"""
Olympic Migration Manager - Enhanced system to migrate from Bronze/Silver/Golden table system to unified Olympic table.

Handles schema flexibility for tables that may use either 'explore_key' or 'explore_id' fields.
Provides safe migration with data preservation and rollback capabilities.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OlympicMigrationManager:
    """
    Manages migration from legacy three-table system (bronze, silver, golden) 
    to unified Olympic table system with flexible schema handling.
    """
    
    def __init__(self, bq_client: bigquery.Client, project_id: str, dataset_id: str = "explore_assistant"):
        self.bq_client = bq_client
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.legacy_tables = ['bronze_queries', 'silver_queries', 'golden_queries']
        self.olympic_table = 'olympic_queries'
        
    def _detect_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Detect schema and field mappings for a table.
        
        Returns:
            dict: Schema information including explore field type and available fields
        """
        schema_info = {
            'table_exists': False,
            'explore_field': None,  # 'explore_id' or 'explore_key'
            'available_fields': [],
            'needs_mapping': False,
            'record_count': 0
        }
        
        try:
            table_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
            table = self.bq_client.get_table(table_ref)
            schema_info['table_exists'] = True
            schema_info['available_fields'] = [field.name for field in table.schema]
            schema_info['record_count'] = table.num_rows
            
            # Check which explore field exists
            if 'explore_id' in schema_info['available_fields']:
                schema_info['explore_field'] = 'explore_id'
            elif 'explore_key' in schema_info['available_fields']:
                schema_info['explore_field'] = 'explore_key'
                schema_info['needs_mapping'] = True
            else:
                schema_info['explore_field'] = None
                
            logger.info(f"Table {table_name}: {schema_info['explore_field']} field, {schema_info['record_count']} records")
                
        except NotFound:
            logger.info(f"Table {table_name} not found")
            schema_info['table_exists'] = False
            
        return schema_info
    
    def check_migration_status(self) -> Dict[str, Any]:
        """
        Check migration status with comprehensive schema detection.
        
        Returns:
            dict: Complete migration status including schema issues and recommendations
        """
        status = {
            'migration_needed': False,
            'legacy_tables_exist': [],
            'olympic_table_exists': False,
            'estimated_record_count': 0,
            'schema_issues': [],
            'can_migrate_safely': True,
            'recommendations': []
        }
        
        logger.info("Checking migration status...")
        
        # Check Olympic table
        olympic_schema = self._detect_table_schema(self.olympic_table)
        status['olympic_table_exists'] = olympic_schema['table_exists']
        
        if olympic_schema['table_exists']:
            status['olympic_record_count'] = olympic_schema['record_count']
            
            # Check if Olympic table has correct schema
            if olympic_schema['explore_field'] != 'explore_id':
                status['schema_issues'].append({
                    'table': self.olympic_table,
                    'issue': f"Uses {olympic_schema['explore_field']} instead of explore_id",
                    'fixable': True,
                    'severity': 'medium'
                })
                status['recommendations'].append(
                    f"Olympic table schema will be updated to use explore_id field"
                )
        
        # Check legacy tables with schema detection
        for table_name in self.legacy_tables:
            table_schema = self._detect_table_schema(table_name)
            
            if table_schema['table_exists']:
                table_info = {
                    'table': table_name,
                    'record_count': table_schema['record_count'],
                    'explore_field': table_schema['explore_field'],
                    'needs_mapping': table_schema['needs_mapping'],
                    'available_fields': table_schema['available_fields']
                }
                
                status['legacy_tables_exist'].append(table_info)
                status['estimated_record_count'] += table_schema['record_count']
                
                # Note schema issues
                if table_schema['explore_field'] is None:
                    status['schema_issues'].append({
                        'table': table_name,
                        'issue': 'Missing both explore_id and explore_key fields',
                        'fixable': False,
                        'severity': 'critical'
                    })
                    status['can_migrate_safely'] = False
                elif table_schema['needs_mapping']:
                    status['recommendations'].append(
                        f"Table {table_name} will map explore_key → explore_id during migration"
                    )
        
        # Determine if migration is needed
        status['migration_needed'] = (
            len(status['legacy_tables_exist']) > 0 and 
            (not status['olympic_table_exists'] or status.get('olympic_record_count', 0) == 0)
        )
        
        # Add overall recommendations
        if status['migration_needed']:
            if status['can_migrate_safely']:
                status['recommendations'].append("Migration can proceed safely with automatic schema handling")
            else:
                status['recommendations'].append("Migration requires manual intervention for critical schema issues")
        
        logger.info(f"Migration status: needed={status['migration_needed']}, safe={status['can_migrate_safely']}")
        return status
    
    def _ensure_olympic_table_exists(self):
        """Create Olympic table with proper explore_id schema."""
        olympic_schema = f"""
        CREATE TABLE IF NOT EXISTS `{self.project_id}.{self.dataset_id}.olympic_queries` (
          id STRING NOT NULL,
          explore_id STRING NOT NULL,  -- Always use explore_id in Olympic system
          input STRING NOT NULL,
          output STRING,
          link STRING,
          user_email STRING,
          rank STRING DEFAULT 'bronze',  -- bronze, silver, gold
          query_run_count INT64 DEFAULT 1,
          feedback_type STRING,
          conversation_history JSON,
          promoted_by STRING,
          promoted_at TIMESTAMP,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
        )
        CLUSTER BY explore_id, rank
        """
        
        logger.info("Creating Olympic table with standard schema")
        self.bq_client.query(olympic_schema).result()
        
    def _fix_olympic_schema(self) -> bool:
        """
        Fix Olympic table schema if it uses explore_key instead of explore_id.
        
        Returns:
            bool: True if schema was fixed or no fix needed, False if fix failed
        """
        olympic_schema = self._detect_table_schema(self.olympic_table)
        
        if not olympic_schema['table_exists']:
            return False
            
        if olympic_schema['explore_field'] == 'explore_key':
            logger.info("Fixing Olympic table schema: renaming explore_key to explore_id")
            
            try:
                # Create temporary table with correct schema
                temp_table_name = f"{self.olympic_table}_migration_temp_{int(datetime.now().timestamp())}"
                
                # Copy data with field renaming
                migration_query = f"""
                CREATE TABLE `{self.project_id}.{self.dataset_id}.{temp_table_name}` AS
                SELECT 
                    id,
                    explore_key as explore_id,  -- Rename field
                    input,
                    output,
                    link,
                    user_email,
                    COALESCE(rank, 'bronze') as rank,  -- Ensure rank has default
                    COALESCE(query_run_count, 1) as query_run_count,
                    feedback_type,
                    conversation_history,
                    promoted_by,
                    promoted_at,
                    created_at,
                    CURRENT_TIMESTAMP() as updated_at
                FROM `{self.project_id}.{self.dataset_id}.{self.olympic_table}`
                """
                
                self.bq_client.query(migration_query).result()
                logger.info(f"Created temporary table {temp_table_name}")
                
                # Archive old table
                archive_name = f"{self.olympic_table}_schema_backup_{int(datetime.now().timestamp())}"
                archive_query = f"""
                CREATE TABLE `{self.project_id}.{self.dataset_id}.{archive_name}` AS
                SELECT * FROM `{self.project_id}.{self.dataset_id}.{self.olympic_table}`
                """
                self.bq_client.query(archive_query).result()
                logger.info(f"Archived old Olympic table as {archive_name}")
                
                # Drop old table
                old_table_ref = self.bq_client.dataset(self.dataset_id).table(self.olympic_table)
                self.bq_client.delete_table(old_table_ref)
                
                # Rename temp table to olympic_queries
                rename_query = f"""
                CREATE TABLE `{self.project_id}.{self.dataset_id}.{self.olympic_table}` AS
                SELECT * FROM `{self.project_id}.{self.dataset_id}.{temp_table_name}`
                """
                self.bq_client.query(rename_query).result()
                
                # Drop temp table
                temp_table_ref = self.bq_client.dataset(self.dataset_id).table(temp_table_name)
                self.bq_client.delete_table(temp_table_ref)
                
                logger.info("Successfully fixed Olympic table schema")
                return True
                
            except Exception as e:
                logger.error(f"Error fixing Olympic schema: {str(e)}")
                return False
                
        elif olympic_schema['explore_field'] == 'explore_id':
            logger.info("Olympic table already has correct schema")
            return True
        else:
            logger.warning("Olympic table has no explore field - will be handled during migration")
            return True
    
    def _migrate_legacy_data(self) -> int:
        """
        Migrate data from legacy tables with flexible schema handling.
        
        Returns:
            int: Total number of records migrated
        """
        total_records = 0
        
        # Migration mappings for each legacy table
        migrations = [
            {
                'source': 'bronze_queries',
                'rank': 'bronze',
                'core_fields': ['id', 'input', 'output', 'link', 'created_at'],
                'optional_fields': ['user_email', 'query_run_count']
            },
            {
                'source': 'silver_queries', 
                'rank': 'silver',
                'core_fields': ['id', 'input', 'output', 'link', 'created_at'],
                'optional_fields': ['user_id', 'user_email', 'feedback_type', 'conversation_history']
            },
            {
                'source': 'golden_queries',
                'rank': 'gold', 
                'core_fields': ['id', 'input', 'output', 'link', 'created_at'],
                'optional_fields': ['promoted_by', 'promoted_at']
            }
        ]
        
        for migration in migrations:
            try:
                # Detect source table schema
                source_schema = self._detect_table_schema(migration['source'])
                
                if not source_schema['table_exists']:
                    logger.info(f"Source table {migration['source']} not found, skipping")
                    continue
                    
                if source_schema['record_count'] == 0:
                    logger.info(f"Source table {migration['source']} is empty, skipping")
                    continue
                
                # Build flexible field mapping
                available_fields = source_schema['available_fields']
                
                # Handle explore field mapping (explore_key -> explore_id)
                explore_field_sql = ""
                if source_schema['explore_field'] == 'explore_id':
                    explore_field_sql = "explore_id"
                elif source_schema['explore_field'] == 'explore_key':
                    explore_field_sql = "explore_key"  # Field name only, not aliased
                else:
                    explore_field_sql = "'unknown'"  # Default if missing
                
                # Handle core fields with safe defaults - these are now handled directly in the SQL
                # The migration query below handles all field mapping and defaults
                
                # Check if source table has id field
                table_ref = f"{self.project_id}.{self.dataset_id}.{migration['source']}"
                table = self.bq_client.get_table(table_ref)
                source_fields = {field.name for field in table.schema}
                has_id_field = 'id' in source_fields
                
                logger.info(f"Source table {migration['source']} fields: {sorted(source_fields)}")
                logger.info(f"Source table has 'id' field: {has_id_field}")
                
                # Determine ID field handling
                if has_id_field:
                    id_field_sql = "COALESCE(id, GENERATE_UUID())"
                    dedup_condition = "AND COALESCE(id, GENERATE_UUID()) NOT IN (SELECT id FROM `{}.{}.olympic_queries` WHERE id IS NOT NULL)".format(
                        self.project_id, self.dataset_id)
                else:
                    id_field_sql = "GENERATE_UUID()"
                    dedup_condition = "-- No deduplication needed for generated UUIDs"
                
                # Handle optional fields - check if they exist in source table
                optional_fields = {
                    'user_email': 'NULL',
                    'query_run_count': '1', 
                    'feedback_type': 'NULL',
                    'conversation_history': 'NULL',
                    'promoted_by': 'NULL',
                    'promoted_at': 'NULL',
                    'link': 'NULL',
                    'output': 'NULL'
                }
                
                field_selects = []
                for field, default in optional_fields.items():
                    if field in source_fields:
                        if field == 'promoted_at':
                            # Handle timestamp type compatibility for promoted_at
                            field_selects.append(f"SAFE_CAST(COALESCE({field}, {default}) AS TIMESTAMP) as {field}")
                        else:
                            field_selects.append(f"COALESCE({field}, {default}) as {field}")
                    else:
                        if field == 'promoted_at':
                            field_selects.append(f"CAST({default} AS TIMESTAMP) as {field}")
                        else:
                            field_selects.append(f"{default} as {field}")
                
                # Handle required fields
                if 'input' in source_fields:
                    input_sql = "COALESCE(input, 'Legacy query')"
                elif 'prompt' in source_fields:
                    input_sql = "COALESCE(prompt, 'Legacy query')"
                elif 'input_question' in source_fields:
                    input_sql = "COALESCE(input_question, 'Legacy query')"
                else:
                    input_sql = "'Legacy query'"
                    
                if 'created_at' in source_fields:
                    # Handle type compatibility by casting created_at to TIMESTAMP if it's a string
                    created_at_sql = "COALESCE(SAFE_CAST(created_at AS TIMESTAMP), CURRENT_TIMESTAMP())"
                else:
                    created_at_sql = "CURRENT_TIMESTAMP()"
                
                # Handle promoted_at field with proper type casting
                if 'promoted_at' in source_fields:
                    promoted_at_sql = "SAFE_CAST(promoted_at AS TIMESTAMP)"
                else:
                    promoted_at_sql = "CAST(NULL AS TIMESTAMP)"
                
                # Build migration query with deduplication and data validation
                migration_query = f"""
                INSERT INTO `{self.project_id}.{self.dataset_id}.olympic_queries`
                (id, explore_id, input, output, link, user_email, rank, query_run_count, 
                 feedback_type, conversation_history, promoted_by, promoted_at, created_at, updated_at)
                SELECT 
                    {id_field_sql} as id,
                    COALESCE({explore_field_sql}, 'unknown') as explore_id,
                    {input_sql} as input,
                    {field_selects[7].split(' as ')[0]} as output,
                    {field_selects[6].split(' as ')[0]} as link,
                    {field_selects[0].split(' as ')[0]} as user_email,
                    '{migration['rank']}' as rank,
                    {field_selects[1].split(' as ')[0]} as query_run_count,
                    {field_selects[2].split(' as ')[0]} as feedback_type,
                    {field_selects[3].split(' as ')[0]} as conversation_history,
                    {field_selects[4].split(' as ')[0]} as promoted_by,
                    {promoted_at_sql} as promoted_at,
                    {created_at_sql} as created_at,
                    CURRENT_TIMESTAMP() as updated_at
                FROM `{self.project_id}.{self.dataset_id}.{migration['source']}`
                WHERE {source_schema['explore_field']} IS NOT NULL  -- Only migrate records with explore field
                  {dedup_condition}
                """
                
                logger.info(f"Migrating from {migration['source']} (schema: {source_schema['explore_field']})")
                logger.debug(f"Using ID field SQL: {id_field_sql}")
                logger.debug(f"Migration query: {migration_query[:200]}...")
                
                result = self.bq_client.query(migration_query).result()
                
                # Get actual migrated count
                count_query = f"""
                SELECT COUNT(*) as migrated_count 
                FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
                WHERE rank = '{migration['rank']}'
                """
                count_result = list(self.bq_client.query(count_query).result())[0]
                migrated_count = count_result.migrated_count
                
                total_records += migrated_count
                logger.info(f"Migrated {migrated_count} records from {migration['source']} to olympic_queries")
                
            except Exception as e:
                logger.error(f"Error migrating from {migration['source']}: {str(e)}")
                # Continue with other tables instead of failing completely
                continue
                
        return total_records
    
    def _verify_migration(self) -> Dict[str, Any]:
        """
        Verify migration completed successfully with comprehensive checks.
        
        Returns:
            dict: Verification results including validity and detailed stats
        """
        verification = {
            'valid': True, 
            'errors': [], 
            'warnings': [],
            'stats': {},
            'data_integrity_checks': {}
        }
        
        try:
            # Check Olympic table record counts by rank
            count_query = f"""
            SELECT 
                rank,
                COUNT(*) as record_count,
                COUNT(DISTINCT explore_id) as unique_explores,
                COUNT(DISTINCT id) as unique_ids,
                COUNT(*) - COUNT(DISTINCT id) as duplicate_ids
            FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
            GROUP BY rank
            ORDER BY rank
            """
            
            results = self.bq_client.query(count_query).result()
            for row in results:
                verification['stats'][row.rank] = {
                    'record_count': row.record_count,
                    'unique_explores': row.unique_explores,
                    'unique_ids': row.unique_ids,
                    'duplicate_ids': row.duplicate_ids
                }
                
                if row.duplicate_ids > 0:
                    verification['warnings'].append(f"Rank {row.rank} has {row.duplicate_ids} duplicate IDs")
                    
            # Check for orphaned records (missing required fields)
            orphan_query = f"""
            SELECT COUNT(*) as orphan_count
            FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
            WHERE explore_id IS NULL OR explore_id = '' 
               OR input IS NULL OR input = ''
               OR id IS NULL OR id = ''
            """
            
            orphan_result = list(self.bq_client.query(orphan_query).result())[0]
            if orphan_result.orphan_count > 0:
                verification['errors'].append(f"Found {orphan_result.orphan_count} records with missing required fields")
                verification['valid'] = False
                
            # Check data distribution
            total_query = f"""
            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT explore_id) as total_explores,
                MIN(created_at) as earliest_record,
                MAX(created_at) as latest_record
            FROM `{self.project_id}.{self.dataset_id}.olympic_queries`
            """
            
            total_result = list(self.bq_client.query(total_query).result())[0]
            verification['data_integrity_checks'] = {
                'total_records': total_result.total_records,
                'total_explores': total_result.total_explores,
                'earliest_record': total_result.earliest_record.isoformat() if total_result.earliest_record else None,
                'latest_record': total_result.latest_record.isoformat() if total_result.latest_record else None
            }
            
            logger.info(f"Migration verification: {total_result.total_records} total records across {total_result.total_explores} explores")
                
        except Exception as e:
            verification['valid'] = False
            verification['errors'].append(f"Verification query failed: {str(e)}")
            logger.error(f"Migration verification failed: {str(e)}")
            
        return verification
    
    def _archive_legacy_tables(self):
        """Archive legacy tables with timestamp suffix instead of dropping them."""
        archive_suffix = f"_archived_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        archived_tables = []
        
        for table_name in self.legacy_tables:
            try:
                source_ref = self.bq_client.dataset(self.dataset_id).table(table_name)
                self.bq_client.get_table(source_ref)  # Check if exists
                
                # Create archived copy
                archive_name = f"{table_name}{archive_suffix}"
                copy_query = f"""
                CREATE TABLE `{self.project_id}.{self.dataset_id}.{archive_name}`
                AS SELECT * FROM `{self.project_id}.{self.dataset_id}.{table_name}`
                """
                self.bq_client.query(copy_query).result()
                
                # Drop original (data is preserved in archive)
                self.bq_client.delete_table(source_ref)
                archived_tables.append({'original': table_name, 'archive': archive_name})
                logger.info(f"Archived {table_name} to {archive_name}")
                
            except NotFound:
                logger.info(f"Legacy table {table_name} not found, skipping archive")
                continue
            except Exception as e:
                logger.error(f"Error archiving {table_name}: {str(e)}")
                continue
        
        return archived_tables
    
    def migrate_to_olympic_system(self, preserve_data: bool = True, verify_migration: bool = True) -> Dict[str, Any]:
        """
        Perform complete migration to Olympic system with comprehensive logging.
        
        Args:
            preserve_data: Whether to preserve legacy data during migration
            verify_migration: Whether to run verification checks after migration
            
        Returns:
            dict: Complete migration log with results and status
        """
        
        migration_log = {
            'started_at': datetime.utcnow().isoformat(),
            'migration_id': str(uuid.uuid4()),
            'steps_completed': [],
            'records_migrated': 0,
            'schema_fixes_applied': [],
            'archived_tables': [],
            'verification_results': None,
            'errors': [],
            'warnings': [],
            'success': False
        }
        
        logger.info(f"Starting Olympic migration {migration_log['migration_id']}")
        
        try:
            # Step 1: Check current status
            current_status = self.check_migration_status()
            if not current_status['can_migrate_safely']:
                raise Exception(f"Migration cannot proceed safely: {current_status['schema_issues']}")
            
            migration_log['pre_migration_status'] = current_status
            migration_log['steps_completed'].append('status_checked')
            
            # Step 2: Ensure Olympic table exists with correct schema
            self._ensure_olympic_table_exists()
            migration_log['steps_completed'].append('olympic_table_created')
            
            # Step 3: Fix Olympic table schema if needed
            schema_fixed = self._fix_olympic_schema()
            if schema_fixed:
                migration_log['schema_fixes_applied'].append('olympic_table_schema_updated')
                migration_log['steps_completed'].append('olympic_schema_fixed')
            
            # Step 4: Migrate data from legacy tables with flexible schema handling
            if preserve_data:
                records_migrated = self._migrate_legacy_data()
                migration_log['records_migrated'] = records_migrated
                migration_log['steps_completed'].append('data_migrated')
                logger.info(f"Migrated {records_migrated} total records")
            
            # Step 5: Verify migration
            if verify_migration:
                verification_result = self._verify_migration()
                migration_log['verification_results'] = verification_result
                
                if not verification_result['valid']:
                    migration_log['errors'].extend(verification_result['errors'])
                    raise Exception(f"Migration verification failed: {verification_result['errors']}")
                    
                if verification_result['warnings']:
                    migration_log['warnings'].extend(verification_result['warnings'])
                    
                migration_log['steps_completed'].append('migration_verified')
            
            # Step 6: Archive legacy tables
            if preserve_data:
                archived_tables = self._archive_legacy_tables()
                migration_log['archived_tables'] = archived_tables
                migration_log['steps_completed'].append('legacy_tables_archived')
            
            migration_log['success'] = True
            migration_log['completed_at'] = datetime.utcnow().isoformat()
            logger.info(f"Olympic migration {migration_log['migration_id']} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            migration_log['errors'].append(error_msg)
            migration_log['failed_at'] = datetime.utcnow().isoformat()
            logger.error(f"Olympic migration {migration_log['migration_id']} failed: {error_msg}")
            raise Exception(f"Migration failed: {error_msg}")
            
        return migration_log
    
    def rollback_migration(self, migration_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rollback a migration using archived tables.
        
        Args:
            migration_log: The log from a previous migration attempt
            
        Returns:
            dict: Rollback operation results
        """
        rollback_log = {
            'started_at': datetime.utcnow().isoformat(),
            'original_migration_id': migration_log.get('migration_id'),
            'steps_completed': [],
            'errors': [],
            'success': False
        }
        
        try:
            # Restore archived tables if they exist
            for archived_table in migration_log.get('archived_tables', []):
                original_name = archived_table['original']
                archive_name = archived_table['archive']
                
                try:
                    # Check if archive exists
                    archive_ref = self.bq_client.dataset(self.dataset_id).table(archive_name)
                    self.bq_client.get_table(archive_ref)
                    
                    # Restore from archive
                    restore_query = f"""
                    CREATE OR REPLACE TABLE `{self.project_id}.{self.dataset_id}.{original_name}`
                    AS SELECT * FROM `{self.project_id}.{self.dataset_id}.{archive_name}`
                    """
                    self.bq_client.query(restore_query).result()
                    rollback_log['steps_completed'].append(f'restored_{original_name}')
                    logger.info(f"Restored {original_name} from {archive_name}")
                    
                except NotFound:
                    rollback_log['errors'].append(f"Archive table {archive_name} not found")
                    continue
            
            rollback_log['success'] = True
            rollback_log['completed_at'] = datetime.utcnow().isoformat()
            
        except Exception as e:
            rollback_log['errors'].append(str(e))
            rollback_log['failed_at'] = datetime.utcnow().isoformat()
            logger.error(f"Rollback failed: {str(e)}")
            
        return rollback_log
