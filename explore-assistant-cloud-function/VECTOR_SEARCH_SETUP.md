# Vector Search Setup Guide

## Overview

The Vector Search system enables semantic field discovery for the Looker Explore Assistant. It uses BigQuery's vector capabilities with Vertex AI embeddings to create a searchable index of field metadata and sample values from Looker explores.

## Architecture

The vector search system consists of several key components:

### 1. **Vector Table Manager** (`vector_table_manager.py`)
- **Purpose**: Creates and manages BigQuery tables for vector storage
- **Key Functions**:
  - Creates Vertex AI embedding models in BigQuery
  - Extracts field metadata from Looker explores
  - Generates embeddings for field names, descriptions, and sample values
  - Creates vector indexes for fast similarity search

### 2. **Vector Search Client** (`vector_search/client.py`)
- **Purpose**: High-level interface for performing semantic searches
- **Key Functions**:
  - Semantic field discovery using natural language queries
  - Field value lookup and matching
  - Integration with query generation pipeline

### 3. **Enhanced Vector Integration** (`vector_search/enhanced_integration.py`)
- **Purpose**: Advanced query processing with vector search
- **Key Functions**:
  - Entity extraction from user queries
  - Contextual field recommendations
  - Golden query integration with vector search

### 4. **Field Lookup Service** (`vector_search/field_lookup.py`)
- **Purpose**: Specific field value search and matching
- **Key Functions**:
  - Value-based field suggestions
  - Type-aware field filtering
  - Performance optimized lookups

## Data Organization

### Field Values Table (`field_values_for_vectorization`)

The main table stores:

| Column | Type | Description |
|--------|------|-------------|
| `field_name` | STRING | Looker field name (e.g., `users.age`) |
| `field_type` | STRING | Data type (dimension, measure, filter) |
| `field_description` | STRING | Human-readable field description |
| `field_label` | STRING | Display label for the field |
| `explore_id` | STRING | Explore identifier (e.g., `ecommerce:users`) |
| `model_name` | STRING | Looker model name |
| `view_name` | STRING | Looker view name |
| `sample_values` | STRING | JSON array of sample values |
| `value_count` | INTEGER | Number of unique values |
| `searchable_text` | STRING | Combined text for embedding generation |
| `embedding` | ARRAY<FLOAT64> | Vector embedding (1536 dimensions) |
| `created_at` | TIMESTAMP | Record creation timestamp |

### How Data is Populated

1. **Looker Metadata Extraction**:
   - Connects to Looker API using SDK
   - Iterates through all explores in specified models
   - Extracts field definitions, types, and descriptions

2. **Sample Value Collection**:
   - Runs LIMIT queries against Looker to get sample values
   - Collects up to 100 unique values per field
   - Stores values as JSON arrays for searchability

3. **Text Preparation**:
   - Combines field name, description, label, and sample values
   - Creates searchable text optimized for embedding generation
   - Handles various data types and edge cases

4. **Embedding Generation**:
   - Uses Vertex AI `text-embedding-004` model via BigQuery
   - Generates 1536-dimensional vectors for each field
   - Stores embeddings directly in BigQuery for fast access

5. **Vector Indexing** (Optional):
   - Creates vector index on embedding column
   - Optimizes similarity search performance
   - Uses approximate nearest neighbor (ANN) algorithms

## Setup Requirements

### Prerequisites

1. **Google Cloud Project**
   - BigQuery API enabled
   - Vertex AI API enabled
   - Appropriate IAM permissions

2. **BigQuery Connection to Vertex AI**
   ```bash
   bq mk --connection --connection_type=CLOUD_RESOURCE \
     --project_id=YOUR_PROJECT_ID \
     --location=us-central1 vertex-ai
   ```

3. **IAM Permissions**
   - Grant Vertex AI User role to BigQuery connection service account:
   ```bash
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:CONNECTION_SERVICE_ACCOUNT" \
     --role="roles/aiplatform.user"
   ```

4. **Looker SDK Configuration**
   - Valid Looker API credentials
   - Access to explores and field metadata

### Configuration

Update your `.env` file or environment variables:

```bash
# GCP Configuration
PROJECT=your-project-id
REGION=us-central1
VERTEX_MODEL=gemini-2.0-flash-001

# BigQuery Configuration
BQ_PROJECT_ID=your-project-id
BQ_DATASET_ID=explore_assistant
BQ_SUGGESTED_TABLE=silver_queries

# Looker Configuration
LOOKERSDK_BASE_URL=https://your-instance.looker.com
LOOKERSDK_CLIENT_ID=your_client_id
LOOKERSDK_CLIENT_SECRET=your_client_secret
LOOKERSDK_VERIFY_SSL=true
LOOKERSDK_TIMEOUT=120
```

## Setup Process

### Method 1: Via Web Interface

1. **Start the Backend Server**:
   ```bash
   cd explore-assistant-cloud-function
   python3 restful_backend.py
   ```

2. **Access Vector Setup Page**:
   - Navigate to the Looker extension
   - Click "Vector Search Setup" in the sidebar
   - Click "Run Vector Search Setup"

3. **Monitor Progress**:
   - Watch the setup steps in the UI
   - Check server logs for detailed progress

### Method 2: Via Python Script

```python
from vector_table_manager import VectorTableManager

# Initialize manager
manager = VectorTableManager()

# Complete setup process
success = manager.setup_complete_system()

if success:
    print("Vector search system setup complete!")
    
    # Get statistics
    stats = manager.get_table_stats()
    print(f"Indexed {stats['total_rows']} fields from {stats['unique_explores']} explores")
else:
    print("Setup failed. Check logs for details.")
```

### Method 3: Via REST API

```bash
# Check system status
curl -X GET http://localhost:8001/api/v1/admin/vector-search/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Run setup
curl -X POST http://localhost:8001/api/v1/admin/vector-search/setup \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"force_refresh": false}'
```

## Setup Steps Explained

The setup process performs these operations in sequence:

### 1. **Create Embedding Model**
```sql
CREATE OR REPLACE MODEL `project.dataset.text_embedding_model`
REMOTE WITH CONNECTION `project.us-central1.vertex-ai`
OPTIONS(ENDPOINT = 'text-embedding-004')
```

### 2. **Extract Field Metadata**
- Connects to Looker SDK
- Iterates through explores
- Collects field definitions and sample values
- Prepares data for embedding generation

### 3. **Create Vector Table**
```sql
CREATE OR REPLACE TABLE `project.dataset.field_values_for_vectorization` (
  field_name STRING,
  field_type STRING,
  field_description STRING,
  -- ... other columns
  embedding ARRAY<FLOAT64>
)
```

### 4. **Generate Embeddings**
```sql
UPDATE `project.dataset.field_values_for_vectorization`
SET embedding = ML.GENERATE_TEXT_EMBEDDING(
  MODEL `project.dataset.text_embedding_model`,
  (SELECT searchable_text as content)
)
WHERE embedding IS NULL
```

### 5. **Create Vector Index** (Optional)
```sql
CREATE VECTOR INDEX field_embedding_index
ON `project.dataset.field_values_for_vectorization`(embedding)
OPTIONS(distance_type = 'COSINE', index_type = 'IVF')
```

## Usage

### Semantic Field Search

```python
from vector_search.client import VectorSearchClient

client = VectorSearchClient()

# Search for fields related to "customer age"
results = await client.search_fields_semantically(
    query="customer age",
    explore_filter=["ecommerce:users"],
    limit=5
)

for field in results.fields:
    print(f"{field.field_name}: {field.similarity_score}")
```

### Field Value Lookup

```python
# Find fields containing specific values
matches = await client.lookup_field_values(
    values=["Premium", "Gold", "Silver"],
    explore_filter=["ecommerce:orders"]
)
```

### Integration with Query Generation

The vector search system is automatically integrated into the query generation pipeline:

1. **Entity Extraction**: Identifies key terms from user queries
2. **Field Discovery**: Finds relevant fields using semantic search
3. **Context Enhancement**: Provides field suggestions to LLM
4. **Query Optimization**: Uses field metadata for better parameter generation

## Performance Considerations

### Indexing Performance
- Initial setup may take 10-30 minutes depending on Looker explore size
- Embedding generation is the most time-intensive step
- Consider using `focus_explore` parameter for faster testing

### Query Performance
- Vector searches typically complete in <2 seconds
- Vector indexes significantly improve performance for large datasets
- Consider field filtering to reduce search space

### Cost Optimization
- Vertex AI embedding calls are the primary cost factor
- Batch processing minimizes API calls
- Consider incremental updates for large systems

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```
   Error: 400 The service account does not have permission
   ```
   **Solution**: Ensure BigQuery connection service account has `roles/aiplatform.user`

2. **Connection Errors**
   ```
   Error: Connection 'vertex-ai' not found
   ```
   **Solution**: Create BigQuery connection to Vertex AI first

3. **Quota Errors**
   ```
   Error: Quota exceeded for Vertex AI API
   ```
   **Solution**: Request quota increase or implement rate limiting

4. **Empty Results**
   ```
   Error: No fields found in explores
   ```
   **Solution**: Check Looker SDK configuration and explore permissions

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
import logging
logging.getLogger('vector_table_manager').setLevel(logging.DEBUG)
```

### Health Checks

Monitor system status via the status endpoint:

```bash
curl http://localhost:8001/api/v1/admin/vector-search/status
```

Expected healthy response:
```json
{
  "system_status": "operational",
  "components": {
    "bigquery_connection": "operational",
    "embedding_model": "operational", 
    "field_values_table": "operational",
    "vector_index": "operational"
  },
  "statistics": {
    "total_rows": 1500,
    "unique_explores": 12,
    "unique_fields": 450
  }
}
```

## Maintenance

### Regular Tasks

1. **Refresh Field Data**
   - Run setup with `force_refresh: true` monthly
   - Updates field metadata and sample values
   - Regenerates embeddings for new/changed fields

2. **Monitor Performance**
   - Check query response times
   - Monitor BigQuery slot usage
   - Review embedding model costs

3. **Update Configurations**
   - Add new explores to indexing
   - Adjust field filtering rules
   - Update embedding model versions

### Backup and Recovery

1. **Export Table Data**
   ```bash
   bq extract --destination_format=PARQUET \
     project:dataset.field_values_for_vectorization \
     gs://bucket/backup/vector_data_*.parquet
   ```

2. **Recreate from Backup**
   ```bash
   bq load --source_format=PARQUET \
     project:dataset.field_values_for_vectorization \
     gs://bucket/backup/vector_data_*.parquet
   ```

## Security Considerations

1. **Access Control**
   - Use IAM roles for granular access control
   - Limit vector search to authorized users
   - Monitor API usage and access patterns

2. **Data Privacy**
   - Field sample values may contain sensitive data
   - Consider data classification and masking
   - Implement appropriate retention policies

3. **API Security**
   - Use authentication tokens for API access
   - Implement rate limiting and quotas
   - Monitor for unusual usage patterns

## Advanced Configuration

### Custom Embedding Models

To use different embedding models:

```sql
CREATE OR REPLACE MODEL `project.dataset.custom_embedding_model`
REMOTE WITH CONNECTION `project.us-central1.vertex-ai`
OPTIONS(ENDPOINT = 'text-multilingual-embedding-002')
```

### Field Filtering

Customize field inclusion rules in `vector_table_manager.py`:

```python
def should_include_field(self, field_info: Dict) -> bool:
    # Custom logic for field filtering
    if field_info.get('hidden'):
        return False
    if field_info.get('type') == 'string' and field_info.get('category') == 'measure':
        return False
    return True
```

### Performance Tuning

Optimize for your use case:

```python
# Batch size for embedding generation
EMBEDDING_BATCH_SIZE = 100

# Maximum sample values per field
MAX_SAMPLE_VALUES = 50

# Vector index configuration
VECTOR_INDEX_OPTIONS = {
    'distance_type': 'COSINE',
    'index_type': 'IVF',
    'ivf_options': '{"num_lists": 1000}'
}
```