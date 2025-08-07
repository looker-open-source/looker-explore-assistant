#!/usr/bin/env python3
"""
Vector Table Management for Field Discovery

This module handles the creation, population, and indexing of BigQuery tables
used for semantic field discovery. It processes Looker field metadata and
sample values to create vector embeddings for similarity search.
"""

import json
import logging
import os
import sys
import io
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
        logging.info("Loaded environment variables from .env file")
except ImportError:
    logging.info("python-dotenv not available, relying on system environment variables")

import looker_sdk
from google.cloud import bigquery
from google.auth import default

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
PROJECT_ID = os.environ.get("PROJECT", "ml-accelerator-dbarr")  # GCP project for connections
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")  # BigQuery project
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

class VectorTableManager:
    """Manages BigQuery tables for field value vectorization"""
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
        self.looker_sdk = None
        
    def get_looker_sdk(self):
        """Initialize and return Looker SDK instance"""
        if self.looker_sdk is not None:
            return self.looker_sdk
            
        try:
            logger.info("Initializing Looker SDK...")
            
            # Check required environment variables
            base_url = os.environ.get('LOOKERSDK_BASE_URL')
            client_id = os.environ.get('LOOKERSDK_CLIENT_ID')
            client_secret = os.environ.get('LOOKERSDK_CLIENT_SECRET')
            
            if not all([base_url, client_id, client_secret]):
                logger.error("Missing required Looker SDK environment variables")
                return None
            
            self.looker_sdk = looker_sdk.init40()
            logger.info("Looker SDK initialized successfully")
            
            # Test the connection
            user = self.looker_sdk.me()
            logger.info(f"Connected to Looker as: {user.email}")
            
            return self.looker_sdk
            
        except Exception as e:
            logger.error(f"Failed to initialize Looker SDK: {e}")
            return None
    
    def create_embedding_model(self) -> bool:
        """
        Create a remote model that connects to Vertex AI text embedding
        """
        try:
            logger.info("Creating remote text embedding model...")
            
            # First, we need a BigQuery connection to Vertex AI
            # This should already exist, but let's try to create the model
            model_query = f"""
            CREATE OR REPLACE MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`
            REMOTE WITH CONNECTION `{BQ_PROJECT_ID}.us-central1.vertex-ai`
            OPTIONS(ENDPOINT = 'text-embedding-004')
            """
            
            job = self.bq_client.query(model_query)
            job.result()
            
            logger.info("Remote text embedding model created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create embedding model: {e}")
            logger.info("Trying with different connection name...")
            
            # Try with a different connection name pattern
            try:
                model_query = f"""
                CREATE OR REPLACE MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`
                REMOTE WITH CONNECTION `us-central1.vertex-ai`
                OPTIONS(ENDPOINT = 'text-embedding-004')
                """
                
                job = self.bq_client.query(model_query)
                job.result()
                
                logger.info("Remote text embedding model created successfully with alternative connection")
                return True
                
            except Exception as e2:
                logger.error(f"Failed to create embedding model with alternative connection: {e2}")
                logger.info("You may need to create a BigQuery connection to Vertex AI first.")
                logger.info(f"Run: bq mk --connection --connection_type=CLOUD_RESOURCE --project_id={BQ_PROJECT_ID} --location=us-central1 vertex-ai")
                return False
    
    def create_field_values_table_from_looker_explores(self, focus_explore: str = None) -> bool:
        """
        Create the field_values_for_vectorization table from Looker explore fields
        
        Args:
            focus_explore: Optional specific explore to focus on (format: "model:explore")
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            sdk = self.get_looker_sdk()
            field_entries = []
            
            # If focusing on a specific explore, extract model and explore names
            target_model = None
            target_explore = None
            if focus_explore:
                if ':' in focus_explore:
                    target_model, target_explore = focus_explore.split(':', 1)
                    logger.info(f"🎯 FOCUSING ON SPECIFIC EXPLORE: {target_model}:{target_explore}")
                else:
                    logger.warning(f"Invalid focus_explore format: {focus_explore}. Expected 'model:explore'")
            
            # Step 1: Get all models and their explores
            logger.info("Fetching all LookML models and explores...")
            models = sdk.all_lookml_models(
                fields='name,explores',
                exclude_empty=True,
                exclude_hidden=True
            )
            
            if not models:
                logger.error("No models found")
                return False
            
            total_explores = sum(len(model.explores or []) for model in models)
            logger.info(f"Found {len(models)} models with {total_explores} explores")
            
            # Step 2: For each explore, get detailed field information
            processed_explores = 0
            for model in models:
                model_name = model.name
                explores = model.explores or []
                
                # Skip if focusing on specific model and this isn't it
                if target_model and model_name != target_model:
                    continue
                
                for explore in explores:
                    explore_name = explore.name
                    processed_explores += 1
                    
                    # Skip if focusing on specific explore and this isn't it
                    if target_explore and explore_name != target_explore:
                        continue
                    
                    try:
                        explore_key = f"{model_name}:{explore_name}"
                        logger.info(f"🔍 Processing explore {processed_explores}/{total_explores}: {explore_key}")
                        
                        # Get detailed explore information with sets and fields
                        logger.info(f"   📡 Fetching explore details for {explore_key}...")
                        explore_detail = sdk.lookml_model_explore(
                            lookml_model_name=model_name,
                            explore_name=explore_name,
                            fields='sets,fields'
                        )
                        
                        # Debug: Log basic explore info
                        logger.info(f"   📋 Explore detail loaded: has_sets={bool(explore_detail.sets)}, has_fields={bool(explore_detail.fields)}")
                        
                        # Find all 'index' sets (including view-prefixed ones like 'view.index')
                        index_sets = []
                        if explore_detail.sets:
                            logger.info(f"   📦 Found {len(explore_detail.sets)} sets in {explore_key}")
                            for set_info in explore_detail.sets:
                                logger.info(f"   📦   Set: {set_info.name} (value_count={len(set_info.value) if set_info.value else 0})")
                                # Check if set name is 'index' or ends with '.index'
                                if set_info.name == 'index' or set_info.name.endswith('.index'):
                                    if set_info.value:  # Only include sets with values
                                        index_sets.append(set_info)
                                        logger.info(f"   ✅   Found index set: {set_info.name}")
                        else:
                            logger.info(f"   📦 No sets found in {explore_key}")
                        
                        if not index_sets:
                            logger.info(f"   ❌ No 'index' sets found in {explore_key}")
                            continue
                        
                        # Combine all index set values
                        all_index_fields = []
                        for index_set in index_sets:
                            all_index_fields.extend(index_set.value or [])
                        
                        if not all_index_fields:
                            logger.info(f"   ❌ All 'index' sets are empty in {explore_key}")
                            continue
                        
                        logger.info(f"   ✅ Found {len(index_sets)} 'index' sets with total {len(all_index_fields)} fields in {explore_key}")
                        logger.info(f"   📋 Combined index fields: {all_index_fields[:20]}{'...' if len(all_index_fields) > 20 else ''}")  # Show first 20
                        
                        # Get field details for all fields in the explore
                        all_fields = {}
                        if explore_detail.fields:
                            # Process dimensions
                            if explore_detail.fields.dimensions:
                                logger.info(f"   📊 Processing {len(explore_detail.fields.dimensions)} dimensions...")
                                for dimension in explore_detail.fields.dimensions:
                                    field_key = f"{dimension.view}.{dimension.name}" if dimension.view else dimension.name
                                    all_fields[field_key] = {
                                        'name': dimension.name,
                                        'view': dimension.view or 'unknown_view',
                                        'type': 'dimension',
                                        'description': dimension.description or '',
                                        'label': dimension.label or dimension.name,
                                        'sql_name': dimension.sql or dimension.name
                                    }
                                    if focus_explore:
                                        logger.info(f"   📊   Dimension: {field_key} (label={dimension.label}, desc={dimension.description})")
                            else:
                                logger.info(f"   📊 No dimensions found in {explore_key}")
                            
                            # Process measures
                            if explore_detail.fields.measures:
                                logger.info(f"   📈 Processing {len(explore_detail.fields.measures)} measures...")
                                for measure in explore_detail.fields.measures:
                                    field_key = f"{measure.view}.{measure.name}" if measure.view else measure.name
                                    all_fields[field_key] = {
                                        'name': measure.name,
                                        'view': measure.view or 'unknown_view',
                                        'type': 'measure',
                                        'description': measure.description or '',
                                        'label': measure.label or measure.name,
                                        'sql_name': measure.sql or measure.name
                                    }
                                    if focus_explore:
                                        logger.info(f"   📈   Measure: {field_key} (label={measure.label}, desc={measure.description})")
                            else:
                                logger.info(f"   📈 No measures found in {explore_key}")
                        else:
                            logger.info(f"   ❌ No fields found in {explore_key}")
                        
                        logger.info(f"   🔍 Total available fields: {len(all_fields)}")
                        
                        # Process fields from all 'index' sets
                        matched_fields = 0
                        for field_path in all_index_fields:
                            field_info = None
                            matched_key = None
                            
                            # Try multiple field key patterns to match
                            possible_keys = [field_path]  # Original path
                            
                            # If field_path contains a dot, try different patterns
                            if '.' in field_path:
                                parts = field_path.split('.')
                                if len(parts) == 2:  # e.g., "inventory_items.product_sku"
                                    view_name, field_name = parts
                                    # Try view.view.field pattern (common in joined explores)
                                    possible_keys.append(f"{view_name}.{view_name}.{field_name}")
                                    # Try view.field pattern
                                    possible_keys.append(f"{view_name}.{field_name}")
                            
                            # Try to match against available field keys
                            for possible_key in possible_keys:
                                if possible_key in all_fields:
                                    field_info = all_fields[possible_key]
                                    matched_key = possible_key
                                    break
                            
                            if field_info:
                                matched_fields += 1
                                
                                # For dimensions, get sample values from Looker data
                                if field_info['type'] == 'dimension':
                                    sample_values = self._get_dimension_sample_values(sdk, model_name, explore_name, field_info, focus_explore)
                                    
                                    if focus_explore:
                                        logger.info(f"   🔍   Sample values collected: {len(sample_values)} values")
                                        logger.info(f"   🔍   Sample values preview: {list(sample_values.keys())[:5]}")
                                    
                                    # Create separate entries for each sample value
                                    for value, frequency in sample_values.items():
                                        # Create searchable text from field metadata and value
                                        searchable_text = f"{field_info['name']} {field_info['label']} {field_info['description']} {value} {model_name} {explore_name}"
                                        
                                        field_entry = {
                                            'model_name': model_name,
                                            'explore_name': explore_name,
                                            'view_name': field_info['view'],
                                            'field_name': field_info['name'],
                                            'field_type': field_info['type'],
                                            'field_description': field_info['description'],
                                            'field_value': str(value),  # Actual dimension value
                                            'value_frequency': frequency,
                                            'searchable_text': searchable_text
                                        }
                                        
                                        field_entries.append(field_entry)
                                        
                                        if focus_explore:
                                            logger.info(f"   ✅   Added dimension value: {field_path} → {matched_key} → {value} (freq={frequency})")
                                else:
                                    # For measures, just use the metadata
                                    searchable_text = f"{field_info['name']} {field_info['label']} {field_info['description']} {model_name} {explore_name}"
                                    
                                    field_entry = {
                                        'model_name': model_name,
                                        'explore_name': explore_name,
                                        'view_name': field_info['view'],
                                        'field_name': field_info['name'],
                                        'field_type': field_info['type'],
                                        'field_description': field_info['description'],
                                        'field_value': field_info['label'],  # Use label as sample value for measures
                                        'value_frequency': 1,
                                        'searchable_text': searchable_text
                                    }
                                    
                                    field_entries.append(field_entry)
                                    
                                    if focus_explore:
                                        logger.info(f"   ✅   Added measure: {field_path} → {matched_key} → {field_entry}")
                            else:
                                logger.warning(f"   ❌   Field {field_path} from index set not found in explore fields")
                                if focus_explore:
                                    logger.info(f"   🔍   Tried keys: {possible_keys}")
                                    logger.info(f"   🔍   Available field keys: {list(all_fields.keys())[:20]}...")  # Show first 20 for debugging
                        
                        logger.info(f"   ✅ Matched {matched_fields}/{len(all_index_fields)} fields from index sets in {explore_key}")
                    
                    except Exception as e:
                        logger.error(f"Error processing explore {model_name}:{explore_name}: {e}")
                        if focus_explore:
                            import traceback
                            logger.error(f"Detailed error: {traceback.format_exc()}")
                        continue
            
            if not field_entries:
                logger.error("No field entries generated from Looker explores")
                return False
            
            logger.info(f"Generated {len(field_entries)} field entries from {processed_explores} explores")
            
            # Log details about the field entries
            if len(field_entries) > 0:
                logger.info(f"🔍 FIELD ENTRIES DEBUG:")
                logger.info(f"   Total entries: {len(field_entries)}")
                dimension_entries = [e for e in field_entries if e['field_type'] == 'dimension']
                measure_entries = [e for e in field_entries if e['field_type'] == 'measure']
                logger.info(f"   Dimension entries: {len(dimension_entries)}")
                logger.info(f"   Measure entries: {len(measure_entries)}")
                
                # Show a sample of entries
                for i, entry in enumerate(field_entries[:5]):
                    logger.info(f"   Entry {i+1}: {entry['field_type']} {entry['view_name']}.{entry['field_name']} = '{entry['field_value']}'")
                
                if len(field_entries) > 5:
                    logger.info(f"   ... and {len(field_entries) - 5} more entries")
            
            # Create table with embeddings
            return self._create_table_with_embeddings(field_entries)
            
        except Exception as e:
            logger.error(f"Failed to create field values table from Looker explores: {e}")
            return False

    def _create_table_with_embeddings(self, field_entries: List[Dict[str, Any]]) -> bool:
        """Create the table with embeddings from field entries"""
        try:
            # First, create a temporary table with the field data
            temp_table_id = f"{FIELD_VALUES_TABLE}_temp_{int(datetime.now().timestamp())}"
            temp_table_ref = self.bq_client.dataset(DATASET_ID).table(temp_table_id)
            
            # Define schema
            schema = [
                bigquery.SchemaField("model_name", "STRING"),
                bigquery.SchemaField("explore_name", "STRING"), 
                bigquery.SchemaField("view_name", "STRING"),
                bigquery.SchemaField("field_name", "STRING"),
                bigquery.SchemaField("field_type", "STRING"),
                bigquery.SchemaField("field_description", "STRING"),
                bigquery.SchemaField("field_value", "STRING"),
                bigquery.SchemaField("value_frequency", "INTEGER"),
                bigquery.SchemaField("searchable_text", "STRING"),
            ]
            
            # Create temporary table
            table = bigquery.Table(temp_table_ref, schema=schema)
            table = self.bq_client.create_table(table)
            logger.info(f"Created temporary table: {temp_table_id}")
            
            # Insert data
            job_config = bigquery.LoadJobConfig()
            job_config.source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
            
            # Convert field entries to newline-delimited JSON
            json_data = '\n'.join([json.dumps(entry) for entry in field_entries])
            
            job = self.bq_client.load_table_from_file(
                io.StringIO(json_data), 
                temp_table_ref, 
                job_config=job_config
            )
            job.result()
            
            logger.info(f"Loaded {len(field_entries)} rows into temporary table")
            
            # Create the final table with embeddings using the correct ML.GENERATE_EMBEDDING syntax
            final_query = f"""
            CREATE OR REPLACE TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}` AS
            SELECT *
            FROM ML.GENERATE_EMBEDDING(
                MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`,
                (
                    SELECT 
                        *,
                        CONCAT(model_name, '.', explore_name, '.', view_name, '.', field_name) as field_location,
                        searchable_text as content
                    FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{temp_table_id}`
                ),
                STRUCT(TRUE AS flatten_json_output)
            )
            """
            
            job = self.bq_client.query(final_query)
            job.result()
            
            logger.info(f"Created final table with embeddings: {FIELD_VALUES_TABLE}")
            
            # Clean up temporary table
            self.bq_client.delete_table(temp_table_ref)
            logger.info(f"Cleaned up temporary table: {temp_table_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create table with embeddings: {e}")
            return False
    
    def _get_dimension_sample_values(self, sdk, model_name: str, explore_name: str, field_info: Dict[str, Any], focus_explore: str = None) -> Dict[str, int]:
        """Get sample values for a dimension by running a Looker query"""
        try:
            # Construct the field reference for the query
            field_reference = f"{field_info['view']}.{field_info['name']}"
            
            # Handle duplicate prefixes like "products.products.brand" -> "products.brand"
            if field_reference.count('.') >= 2:
                # If there are 2+ periods, remove the first part (before first period)
                parts = field_reference.split('.', 1)  # Split only on first period
                if len(parts) == 2:
                    field_reference = parts[1]  # Use everything after first period
            
            # Print the field details for debugging
            if focus_explore:
                logger.info(f"   🔍   QUERY FIELD DEBUG:")
                logger.info(f"       Model: {model_name}")
                logger.info(f"       Explore: {explore_name}")
                logger.info(f"       Original Field: {field_info['view']}.{field_info['name']}")
                logger.info(f"       Cleaned Field Reference: {field_reference}")
                logger.info(f"       Field Info: {field_info}")
            
            # Create a simple query to get top values for this dimension
            # Use a basic row count instead of a specific measure
            query_body = {
                "model": model_name,
                "view": explore_name,  # Quirky API: uses "view" even though it's an explore
                "fields": [field_reference],  # API uses "fields" not "dimensions"
                "sorts": [f"{field_reference}"],
                "limit": "5000",  # Get top 5000 values
                "vis_config": {"type": "table"}
            }
            
            if focus_explore:
                logger.info(f"   🔍   RAW API CALL - Query Body:")
                logger.info(f"       {json.dumps(query_body, indent=8)}")
            
            # Log the actual API call details
            if focus_explore:
                logger.info(f"   🔍   RAW API CALL - Making request:")
                logger.info(f"       Method: POST")
                logger.info(f"       Endpoint: /queries/run/json")
                logger.info(f"       SDK Method: run_inline_query(result_format='json', body=...)")
            
            # Run the query
            query_result = sdk.run_inline_query(
                result_format="json",
                body=query_body
            )
            
            # Log the raw response
            if focus_explore:
                logger.info(f"   🔍   RAW API RESPONSE:")
                logger.info(f"       Response Type: {type(query_result)}")
                logger.info(f"       Response Length: {len(query_result) if query_result else 'None'}")
                if query_result:
                    # Show first 500 chars of response for debugging
                    response_preview = str(query_result)[:500]
                    logger.info(f"       Response Preview (first 500 chars): {response_preview}")
                    if len(str(query_result)) > 500:
                        logger.info(f"       ... (response truncated, total length: {len(str(query_result))})")
                else:
                    logger.info(f"       Response: None/Empty")
            
            # Parse the results
            sample_values = {}
            if query_result:
                try:
                    data = json.loads(query_result)
                    
                    if focus_explore:
                        logger.info(f"   🔍   PARSED JSON RESPONSE:")
                        logger.info(f"       Data Type: {type(data)}")
                        logger.info(f"       Data Length: {len(data) if hasattr(data, '__len__') else 'No length'}")
                        if isinstance(data, list) and len(data) > 0:
                            logger.info(f"       First Row: {data[0]}")
                            logger.info(f"       First Few Rows: {data[:3]}")
                    
                    for row in data:
                        # Handle dictionary format (expected from Looker API)
                        if isinstance(row, dict):
                            # Get the single field value from this row dictionary
                            for field_key, field_value in row.items():
                                if field_value is not None:
                                    value = str(field_value).strip()
                                    
                                    # Skip empty values
                                    if value and value.lower() not in ['null', 'n/a', '']:
                                        sample_values[value] = 1  # Default frequency
                        else:
                            # Fallback for list format (old format)
                            if len(row) >= 1 and row[0] is not None:
                                value = str(row[0]).strip()
                                
                                # Skip empty values
                                if value and value.lower() not in ['null', 'n/a', '']:
                                    sample_values[value] = 1  # Default frequency
                    
                    if focus_explore:
                        logger.info(f"   ✅   Found {len(sample_values)} sample values for {field_reference}")
                        if sample_values:
                            top_values = list(sample_values.keys())[:5]
                            logger.info(f"   📋   Top values: {top_values}")
                
                except Exception as e:
                    if focus_explore:
                        logger.error(f"   ⚠️   JSON PARSING ERROR for {field_reference}: {e}")
                        logger.error(f"   ⚠️   Raw response that failed to parse: {query_result}")
                    # Fallback to just the field label
                    sample_values = {field_info['label']: 1}
            
            # If no sample values found, use field metadata as fallback
            if not sample_values:
                sample_values = {field_info['label']: 1}
                if focus_explore:
                    logger.info(f"   ℹ️   No sample values found, using field label as fallback")
            
            return sample_values
            
        except Exception as e:
            if focus_explore:
                logger.error(f"   ❌   FULL EXCEPTION for dimension {field_info['name']}: {e}")
                logger.error(f" {query_body}")
            else:
                logger.warning(f"Failed to get sample values for dimension {field_info['name']}: {e}")
            # Return field label as fallback
            return {field_info['label']: 1}
    
    def create_vector_index(self) -> bool:
        """Create vector index for fast similarity search"""
        try:
            logger.info("Creating vector index...")
            
            # First check if we have enough rows for a vector index
            count_query = f"""
            SELECT COUNT(*) as total_rows 
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            """
            count_result = self.bq_client.query(count_query).result()
            total_rows = next(count_result).total_rows
            
            if total_rows < 5000:
                logger.warning(f"Only {total_rows} rows in table. Vector index requires at least 5,000 rows.")
                logger.info("Will use VECTOR_SEARCH function directly instead of creating an index.")
                return True  # Consider this successful since we can still do vector search
            
            index_query = f"""
            CREATE VECTOR INDEX IF NOT EXISTS field_values_embedding_index
            ON `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`(ml_generate_embedding_result)
            OPTIONS (
                index_type = 'IVF',
                distance_type = 'COSINE'
            )
            """
            
            job = self.bq_client.query(index_query)
            job.result()
            
            logger.info("Successfully created vector index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create vector index: {e}")
            # If it's a row count issue, still consider it successful
            if "smaller than min allowed" in str(e):
                logger.info("Will use VECTOR_SEARCH function directly instead of creating an index.")
                return True
            return False
    
    def setup_complete_system(self, focus_explore: str = None) -> bool:
        """Set up the complete vector search system"""
        try:
            logger.info("Setting up complete vector search system...")
            
            # Step 1: Create embedding model
            if not self.create_embedding_model():
                return False
            
            # Step 2: Create field values table from Looker explores
            if focus_explore:
                logger.info(f"Using focused explore: {focus_explore}")
            else:
                logger.info("Using Looker explores with 'index' sets to populate fields...")
            if not self.create_field_values_table_from_looker_explores(focus_explore):
                return False
            
            # Step 3: Create vector index
            if not self.create_vector_index():
                return False
            
            logger.info("✅ Vector search system setup complete!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup vector search system: {e}")
            return False
    
    def update_field_values(self, focus_explore: str = None) -> bool:
        """Update field values table with latest Looker data"""
        try:
            if focus_explore:
                logger.info(f"Updating field values table with focus explore: {focus_explore}")
            else:
                logger.info("Updating field values table...")
            return self.create_field_values_table_from_looker_explores(focus_explore)
            
        except Exception as e:
            logger.error(f"Failed to update field values: {e}")
            return False
    
    def get_table_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector tables"""
        try:
            stats_query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT field_location) as unique_fields,
                COUNT(DISTINCT CONCAT(model_name, ':', explore_name)) as unique_explores,
                COUNT(DISTINCT model_name) as unique_models
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            """
            
            result = self.bq_client.query(stats_query).result()
            stats = next(result)
            
            return {
                "total_rows": stats.total_rows,
                "unique_fields": stats.unique_fields,
                "unique_explores": stats.unique_explores,
                "unique_models": stats.unique_models,
                "table_name": FIELD_VALUES_TABLE,
                "project_id": PROJECT_ID,
                "dataset_id": DATASET_ID
            }
            
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return {"error": str(e)}

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage vector tables for field discovery")
    parser.add_argument("--action", choices=["setup", "update", "stats"], required=True,
                       help="Action to perform")
    parser.add_argument("--focus-explore", type=str,
                       help="Focus on a specific explore (format: model:explore)")
    
    args = parser.parse_args()
    
    manager = VectorTableManager()
    
    if args.action == "setup":
        success = manager.setup_complete_system(args.focus_explore)
        sys.exit(0 if success else 1)
    
    elif args.action == "update":
        success = manager.update_field_values(args.focus_explore)
        sys.exit(0 if success else 1)
    
    elif args.action == "stats":
        stats = manager.get_table_stats()
        print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
