# Olympic Migration System

A comprehensive migration system to transition from the legacy three-table system (Bronze/Silver/Golden queries) to a unified Olympic table architecture with flexible schema handling.

## Overview

The Olympic Migration System provides:
- **Automatic migration** from legacy tables to unified Olympic system
- **Flexible schema handling** for both `explore_key` and `explore_id` fields
- **Graceful runtime operations** with fallback support
- **MCP integration** for frontend migration management
- **Data preservation** with rollback capabilities

## Architecture

### Components

1. **OlympicMigrationManager** (`olympic_migration_manager.py`)
   - Handles migration from legacy three-table system
   - Flexible schema detection and mapping
   - Data preservation and verification

2. **GracefulTableManager** (`graceful_table_manager.py`)
   - Runtime table operations with fallback support
   - Flexible schema handling for both systems
   - Performance-optimized with caching

3. **OlympicMCPIntegration** (`olympic_mcp_integration.py`)
   - MCP tools for frontend integration
   - User-friendly migration management
   - Comprehensive status reporting

### Table Evolution

#### Legacy System (Three Tables)
```
bronze_queries    (explore_key/explore_id, basic query data)
silver_queries    (explore_key/explore_id, feedback data)  
golden_queries    (explore_key/explore_id, training data)
```

#### Olympic System (Unified Table)
```
olympic_queries   (explore_id, rank, comprehensive data)
- rank: 'bronze', 'silver', 'gold'
- Clustered by explore_id and rank for performance
- Unified schema with all necessary fields
```

## Usage

### 1. Migration Management

#### Check Migration Status
```python
from olympic_migration_manager import OlympicMigrationManager

manager = OlympicMigrationManager(bq_client, project_id, dataset_id)
status = manager.check_migration_status()

print(f"Migration needed: {status['migration_needed']}")
print(f"Can migrate safely: {status['can_migrate_safely']}")
print(f"Legacy tables: {len(status['legacy_tables_exist'])}")
```

#### Perform Migration
```python
migration_result = manager.migrate_to_olympic_system(
    preserve_data=True,
    verify_migration=True
)

if migration_result['success']:
    print(f"Migrated {migration_result['records_migrated']} records")
else:
    print(f"Migration failed: {migration_result['errors']}")
```

### 2. Runtime Operations

#### Add Query (with automatic fallback)
```python
from graceful_table_manager import GracefulTableManager

table_manager = GracefulTableManager(bq_client, project_id, dataset_id)

query_data = {
    'explore_id': 'ecommerce:orders',
    'input': 'Show me sales by month',
    'output': '{"dimensions": ["created_month"], "measures": ["total_sales"]}',
    'link': 'https://looker.com/query/123',
    'user_email': 'user@company.com'
}

# Automatically uses Olympic system if available, falls back to legacy if needed
result = await table_manager.add_olympic_query_flexible(query_data, rank='bronze')
print(f"Added to {result['system']} system")
```

#### Get Queries (works with both systems)
```python
# Get golden queries with automatic system detection
golden_queries = await table_manager.get_queries_flexible(
    'olympic_queries',
    explore_id='ecommerce:orders', 
    rank='gold',
    limit=10
)

print(f"Found {len(golden_queries)} golden queries")
```

### 3. MCP Integration (Frontend)

#### TypeScript Frontend Integration
```typescript
import { useMigrateToOlympic } from '../hooks/useMigrateToOlympic'

const { migrationStatus, checkMigrationNeeded, performMigration } = useMigrateToOlympic()

// Check if migration is needed
const needsMigration = await checkMigrationNeeded()

// Perform migration
if (needsMigration) {
    await performMigration()
}
```

#### MCP Tools Available
```javascript
// Check migration status
await sendMCPMessage({
    tool_name: 'check_migration_status',
    arguments: {}
})

// Perform migration
await sendMCPMessage({
    tool_name: 'migrate_to_olympic_system',
    arguments: { preserve_data: true, verify_migration: true }
})

// Add query with flexible handling
await sendMCPMessage({
    tool_name: 'add_bronze_query_flexible',
    arguments: {
        explore_id: 'ecommerce:orders',
        input_text: 'User query',
        output_data: '{"query": "data"}',
        link: 'https://looker.com/query',
        user_email: 'user@company.com'
    }
})
```

## Schema Flexibility

The system handles both legacy and modern field naming:

### Field Mapping
- **Legacy**: `explore_key` → **Olympic**: `explore_id`
- **User Fields**: `user_id` → `user_email` (when appropriate)
- **Missing Fields**: Sensible defaults provided

### Example Migration
```sql
-- Legacy bronze_queries (explore_key schema)
SELECT explore_key, input, output, link, user_email FROM bronze_queries

-- Migrated to Olympic (explore_id schema)  
INSERT INTO olympic_queries (explore_id, input, output, link, user_email, rank)
SELECT explore_key as explore_id, input, output, link, user_email, 'bronze'
FROM bronze_queries
```

## Data Safety Features

### 1. Archive Strategy
- Legacy tables are **archived**, not dropped
- Archives have timestamp suffixes: `bronze_queries_archived_20250811_143022`
- Rollback capability using archived data

### 2. Migration Verification
- Record count validation
- Duplicate detection
- Data integrity checks
- Schema validation

### 3. Graceful Fallback
- Runtime operations try Olympic first, fall back to legacy
- No performance impact during normal operations
- Automatic system detection and caching

## Testing

### Run Comprehensive Tests
```bash
cd explore-assistant-cloud-function

# Set environment variables
export BQ_PROJECT_ID=your-project-id
export BQ_DATASET_ID=explore_assistant

# Run Olympic system tests
python test_olympic_system.py
```

### Test Coverage
- ✅ Schema detection (explore_key vs explore_id)
- ✅ Migration status checking
- ✅ Full migration with verification
- ✅ Graceful table operations
- ✅ MCP integration tools
- ✅ Edge cases and error handling

## Integration with Existing Code

### Update looker_mcp_server.py
```python
from olympic_mcp_integration import add_olympic_mcp_tools

class LookerMCPServer:
    def __init__(self):
        # ... existing initialization ...
        
        # Add Olympic migration tools
        add_olympic_mcp_tools(self)
```

### Update Frontend State Management
```typescript
// Add migration state to assistantSlice.ts
interface AssistantState {
    // ... existing state ...
    migration: {
        status: 'idle' | 'checking' | 'migrating' | 'complete' | 'error'
        lastCheck: string | null
        migrationNeeded: boolean
    }
}
```

## Environment Variables

```bash
# Required
BQ_PROJECT_ID=your-bigquery-project
BQ_DATASET_ID=explore_assistant

# Optional
MIGRATION_AUTO_MIGRATE=false          # Enable auto-migration on first use
MIGRATION_VERIFY_ALWAYS=true         # Always verify migrations
MIGRATION_PRESERVE_LEGACY=true       # Keep legacy table archives
```

## Monitoring and Observability

### Logging
- Comprehensive logging with structured messages
- Migration progress tracking
- Error reporting with context
- Performance metrics

### Metrics to Monitor
- Migration success/failure rates
- Query operation latencies
- Table usage patterns
- Schema detection cache hit rates

## Troubleshooting

### Common Issues

#### 1. Migration Fails with Schema Issues
```bash
# Check table schemas
python -c "
from olympic_migration_manager import OlympicMigrationManager
from google.cloud import bigquery
manager = OlympicMigrationManager(bigquery.Client(), 'project', 'dataset')
status = manager.check_migration_status()
print('Schema issues:', status['schema_issues'])
"
```

#### 2. Performance Issues
- Enable table caching in GracefulTableManager
- Use clustered tables for large datasets
- Monitor BigQuery query costs

#### 3. Data Inconsistencies
- Run migration verification manually
- Check for duplicate records
- Validate field mappings

### Recovery Procedures

#### Rollback Migration
```python
# Use archived tables to rollback
migration_log = {...}  # From previous migration
rollback_result = manager.rollback_migration(migration_log)
```

#### Manual Data Repair
```sql
-- Fix explore_id field if needed
UPDATE `project.dataset.olympic_queries` 
SET explore_id = REGEXP_REPLACE(explore_id, 'old_pattern', 'new_pattern')
WHERE explore_id LIKE '%pattern%'
```

## Future Enhancements

1. **Streaming Migration** - Migrate large datasets in batches
2. **Cross-Project Migration** - Support migration between projects
3. **Advanced Analytics** - Migration impact analysis
4. **Automated Cleanup** - Scheduled cleanup of archived tables

## Contributing

When contributing to the Olympic Migration System:

1. **Test Coverage** - Ensure all new functionality is tested
2. **Schema Safety** - Handle schema variations gracefully
3. **Backward Compatibility** - Maintain support for legacy systems
4. **Documentation** - Update this README with changes
5. **Logging** - Add comprehensive logging for debugging

## License

This Olympic Migration System is part of the Looker Explore Assistant project and follows the same licensing terms.
