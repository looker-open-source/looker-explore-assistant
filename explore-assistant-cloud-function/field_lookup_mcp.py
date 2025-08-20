#!/usr/bin/env python3
"""
Field Value Lookup Service for Looker Explore Assistant

A simple semantic search service that finds Looker fields and dimension values
based on string similarity. This service takes specific strings (not natural language phrases)
and returns matching field locations and values.
"""

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from google.cloud import bigquery
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

class FieldMatch(BaseModel):
    """A single field match from vector search"""
    field_location: str = Field(description="Full field path: model.explore.view.field")
    model_name: str
    explore_name: str
    view_name: str
    field_name: str
    field_type: str
    field_description: Optional[str]
    search_term: str
    similarity: float
    matching_values: List[Dict[str, Any]] = Field(description="List of matching field values")

class FieldValueLookupService:
    """Simple service for looking up field values by string matching"""
    
    def __init__(self):
        self.bq_client = None
    
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
            logger.info(f"Initialized BigQuery client for project: {BQ_PROJECT_ID}")
    
    async def semantic_field_search(
        self,
        search_terms: List[str], 
        explore_ids: Optional[List[str]] = None,
        limit_per_term: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[FieldMatch]:
        """Find Looker fields that semantically match the search terms"""
        
        if not search_terms:
            return []
        
        await self._ensure_bigquery_client()
        all_results = []
        
        for term in search_terms:
            try:
                # Use BigQuery VECTOR_SEARCH to find similar fields
                search_query = f"""
                SELECT 
                    field_location,
                    model_name,
                    explore_name,
                    view_name,
                    field_name,
                    field_type,
                    field_description,
                    field_value,
                    value_frequency,
                    distance,
                    (1 - distance) as similarity
                FROM VECTOR_SEARCH(
                    TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
                    'ml_generate_embedding_result',
                    (
                        SELECT ml_generate_embedding_result 
                        FROM ML.GENERATE_EMBEDDING(
                            MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.{EMBEDDING_MODEL}`,
                            (SELECT @search_term as content),
                            STRUCT(TRUE AS flatten_json_output)
                        )
                    ),
                    top_k => @limit_per_term
                )
                WHERE (1 - distance) >= @similarity_threshold
                """
                
                query_params = [
                    bigquery.ScalarQueryParameter("search_term", "STRING", term),
                    bigquery.ScalarQueryParameter("limit_per_term", "INT64", limit_per_term),
                    bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold)
                ]
                
                # Add explore filtering if specified
                if explore_ids:
                    explore_conditions = []
                    for i, explore_id in enumerate(explore_ids):
                        model_name, explore_name = explore_id.split(':')
                        model_param = f"model_name_{i}"
                        explore_param = f"explore_name_{i}"
                        explore_conditions.append(f"(model_name = @{model_param} AND explore_name = @{explore_param})")
                        query_params.extend([
                            bigquery.ScalarQueryParameter(model_param, "STRING", model_name),
                            bigquery.ScalarQueryParameter(explore_param, "STRING", explore_name)
                        ])
                    search_query += f" AND ({' OR '.join(explore_conditions)})"
                
                search_query += " ORDER BY similarity DESC"
                
                job_config = bigquery.QueryJobConfig(query_parameters=query_params)
                results = self.bq_client.query(search_query, job_config=job_config).result()
                
                # Group results by field and collect matching values
                field_matches = {}
                for row in results:
                    field_location = row.field_location
                    
                    if field_location not in field_matches:
                        field_matches[field_location] = FieldMatch(
                            field_location=field_location,
                            model_name=row.model_name,
                            explore_name=row.explore_name,
                            view_name=row.view_name,
                            field_name=row.field_name,
                            field_type=row.field_type,
                            field_description=row.field_description,
                            search_term=term,
                            similarity=float(row.similarity),
                            matching_values=[]
                        )
                    
                    # Add this value to the matching values
                    field_matches[field_location].matching_values.append({
                        "value": row.field_value,
                        "similarity": float(row.similarity),
                        "frequency": int(row.value_frequency)
                    })
                    
                    # Update best similarity for this field
                    if float(row.similarity) > field_matches[field_location].similarity:
                        field_matches[field_location].similarity = float(row.similarity)
                
                all_results.extend(field_matches.values())
                
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {e}")
                continue
        
        # Remove duplicates and sort by similarity
        unique_results = {}
        for result in all_results:
            key = result.field_location
            if key not in unique_results or result.similarity > unique_results[key].similarity:
                unique_results[key] = result
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x.similarity, reverse=True)
        
        logger.info(f"Found {len(sorted_results)} unique field matches for terms: {search_terms}")
        return sorted_results
    
    async def field_value_lookup(
        self, 
        search_string: str,
        field_location: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find dimension values that contain a specific string"""
        
        await self._ensure_bigquery_client()
        
        try:
            # Build query to find dimension values containing the search string
            base_query = f"""
            SELECT 
                field_location,
                model_name,
                explore_name,
                view_name,
                field_name,
                field_type,
                field_value,
                value_frequency
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            WHERE LOWER(field_value) LIKE LOWER(@search_pattern)
            """
            
            query_params = [
                bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_string}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            # Add field location filter if specified
            if field_location:
                base_query += " AND field_location = @field_location"
                query_params.append(
                    bigquery.ScalarQueryParameter("field_location", "STRING", field_location)
                )
            
            base_query += " ORDER BY value_frequency DESC, field_value LIMIT @limit"
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            results = self.bq_client.query(base_query, job_config=job_config).result()
            
            matching_values = []
            for row in results:
                matching_values.append({
                    "field_location": row.field_location,
                    "model_name": row.model_name,
                    "explore_name": row.explore_name,
                    "view_name": row.view_name,
                    "field_name": row.field_name,
                    "field_type": row.field_type,
                    "field_value": row.field_value,
                    "value_frequency": int(row.value_frequency)
                })
            
            logger.info(f"Found {len(matching_values)} matching values for '{search_string}'")
            return matching_values
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            raise

# Example usage functions
async def test_field_search():
    """Test the field search functionality"""
    service = FieldValueLookupService()
    
    # Test semantic field search
    print("🔍 Testing semantic field search...")
    search_terms = ["brand", "customer", "revenue", "inventory"]
    results = await service.semantic_field_search(search_terms, limit_per_term=3)
    
    for result in results:
        print(f"  Field: {result.field_location} ({result.field_type})")
        print(f"  Search term: {result.search_term}")
        print(f"  Similarity: {result.similarity:.3f}")
        print(f"  Sample values: {[v['value'] for v in result.matching_values[:3]]}")
        print()
    
    # Test field value lookup
    print("🔍 Testing field value lookup...")
    value_results = await service.field_value_lookup("nike", limit=5)
    
    for result in value_results:
        print(f"  {result['field_location']}: {result['field_value']}")
    
    print(f"Completed tests!")

async def main():
    """Main entry point for testing"""
    await test_field_search()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from google.cloud import bigquery
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

class FieldMatch(BaseModel):
    """A single field match from vector search"""
    field_location: str = Field(description="Full field path: model.explore.view.field")
    model_name: str
    explore_name: str
    view_name: str
    field_name: str
    field_type: str
    field_description: Optional[str]
    search_term: str
    similarity: float
    matching_values: List[Dict[str, Any]] = Field(description="List of matching field values")

class FieldValueLookupService:
    """Simple service for looking up field values by string matching"""
    
    def __init__(self):
        self.bq_client = None
    
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
            logger.info(f"Initialized BigQuery client for project: {BQ_PROJECT_ID}")
    
    async def semantic_field_search(
        self,
        search_terms: List[str], 
        explore_ids: Optional[List[str]] = None,
        limit_per_term: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[FieldMatch]:
        """Find Looker fields that semantically match the search terms"""
        
        if not search_terms:
            return []
        
        await self._ensure_bigquery_client()
        all_results = []
        
        for term in search_terms:
            try:
                # Use BigQuery VECTOR_SEARCH to find similar fields
                search_query = f"""
                SELECT 
                    field_location,
                    model_name,
                    explore_name,
                    view_name,
                    field_name,
                    field_type,
                    field_description,
                    field_value,
                    value_frequency,
                    distance,
                    (1 - distance) as similarity
                FROM VECTOR_SEARCH(
                    TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
                    'ml_generate_embedding_result',
                    (
                        SELECT ml_generate_embedding_result 
                        FROM ML.GENERATE_EMBEDDING(
                            MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.{EMBEDDING_MODEL}`,
                            (SELECT @search_term as content),
                            STRUCT(TRUE AS flatten_json_output)
                        )
                    ),
                    top_k => @limit_per_term
                )
                WHERE (1 - distance) >= @similarity_threshold
                """
                
                query_params = [
                    bigquery.ScalarQueryParameter("search_term", "STRING", term),
                    bigquery.ScalarQueryParameter("limit_per_term", "INT64", limit_per_term),
                    bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold)
                ]
                
                # Add explore filtering if specified
                if explore_ids:
                    explore_conditions = []
                    for i, explore_id in enumerate(explore_ids):
                        model_name, explore_name = explore_id.split(':')
                        model_param = f"model_name_{i}"
                        explore_param = f"explore_name_{i}"
                        explore_conditions.append(f"(model_name = @{model_param} AND explore_name = @{explore_param})")
                        query_params.extend([
                            bigquery.ScalarQueryParameter(model_param, "STRING", model_name),
                            bigquery.ScalarQueryParameter(explore_param, "STRING", explore_name)
                        ])
                    search_query += f" AND ({' OR '.join(explore_conditions)})"
                
                search_query += " ORDER BY similarity DESC"
                
                job_config = bigquery.QueryJobConfig(query_parameters=query_params)
                results = self.bq_client.query(search_query, job_config=job_config).result()
                
                # Group results by field and collect matching values
                field_matches = {}
                for row in results:
                    field_location = row.field_location
                    
                    if field_location not in field_matches:
                        field_matches[field_location] = FieldMatch(
                            field_location=field_location,
                            model_name=row.model_name,
                            explore_name=row.explore_name,
                            view_name=row.view_name,
                            field_name=row.field_name,
                            field_type=row.field_type,
                            field_description=row.field_description,
                            search_term=term,
                            similarity=float(row.similarity),
                            matching_values=[]
                        )
                    
                    # Add this value to the matching values
                    field_matches[field_location].matching_values.append({
                        "value": row.field_value,
                        "similarity": float(row.similarity),
                        "frequency": int(row.value_frequency)
                    })
                    
                    # Update best similarity for this field
                    if float(row.similarity) > field_matches[field_location].similarity:
                        field_matches[field_location].similarity = float(row.similarity)
                
                all_results.extend(field_matches.values())
                
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {e}")
                continue
        
        # Remove duplicates and sort by similarity
        unique_results = {}
        for result in all_results:
            key = result.field_location
            if key not in unique_results or result.similarity > unique_results[key].similarity:
                unique_results[key] = result
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x.similarity, reverse=True)
        
        logger.info(f"Found {len(sorted_results)} unique field matches for terms: {search_terms}")
        return sorted_results
    
    async def field_value_lookup(
        self, 
        search_string: str,
        field_location: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find dimension values that contain a specific string"""
        
        await self._ensure_bigquery_client()
        
        try:
            # Build query to find dimension values containing the search string
            base_query = f"""
            SELECT 
                field_location,
                model_name,
                explore_name,
                view_name,
                field_name,
                field_type,
                field_value,
                value_frequency
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            WHERE LOWER(field_value) LIKE LOWER(@search_pattern)
            """
            
            query_params = [
                bigquery.ScalarQueryParameter("search_pattern", "STRING", f"%{search_string}%"),
                bigquery.ScalarQueryParameter("limit", "INT64", limit)
            ]
            
            # Add field location filter if specified
            if field_location:
                base_query += " AND field_location = @field_location"
                query_params.append(
                    bigquery.ScalarQueryParameter("field_location", "STRING", field_location)
                )
            
            base_query += " ORDER BY value_frequency DESC, field_value LIMIT @limit"
            
            job_config = bigquery.QueryJobConfig(query_parameters=query_params)
            results = self.bq_client.query(base_query, job_config=job_config).result()
            
            matching_values = []
            for row in results:
                matching_values.append({
                    "field_location": row.field_location,
                    "model_name": row.model_name,
                    "explore_name": row.explore_name,
                    "view_name": row.view_name,
                    "field_name": row.field_name,
                    "field_type": row.field_type,
                    "field_value": row.field_value,
                    "value_frequency": int(row.value_frequency)
                })
            
            logger.info(f"Found {len(matching_values)} matching values for '{search_string}'")
            return matching_values
            
        except Exception as e:
            logger.error(f"Field value lookup failed: {e}")
            raise

# Example usage functions
async def test_field_search():
    """Test the field search functionality"""
    service = FieldValueLookupService()
    
    # Test semantic field search
    print("🔍 Testing semantic field search...")
    search_terms = ["brand", "customer", "revenue", "inventory"]
    results = await service.semantic_field_search(search_terms, limit_per_term=3)
    
    for result in results:
        print(f"  Field: {result.field_location} ({result.field_type})")
        print(f"  Search term: {result.search_term}")
        print(f"  Similarity: {result.similarity:.3f}")
        print(f"  Sample values: {[v['value'] for v in result.matching_values[:3]]}")
        print()
    
    # Test field value lookup
    print("🔍 Testing field value lookup...")
    value_results = await service.field_value_lookup("nike", limit=5)
    
    for result in value_results:
        print(f"  {result['field_location']}: {result['field_value']}")
    
    print(f"Completed tests!")

async def main():
    """Main entry point for testing"""
    await test_field_search()

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional

from google.cloud import bigquery
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"
EMBEDDING_MODEL = "text_embedding_model"

class FieldMatch(BaseModel):
    """A single field match from vector search"""
    field_location: str = Field(description="Full field path: model.explore.view.field")
    model_name: str
    explore_name: str
    view_name: str
    field_name: str
    field_type: str
    field_description: Optional[str]
    search_term: str
    similarity: float
    matching_values: List[Dict[str, Any]] = Field(description="List of matching field values")

class FieldDiscoveryResult(BaseModel):
    """Complete field discovery result"""
    searchable_terms: List[str]
    discovered_fields: List[FieldMatch]
    field_suggestions: Dict[str, List[str]]

class FieldLookupMCPServer:
    """MCP Server for semantic field discovery in Looker"""
    
    def __init__(self):
        self.server = Server("field-lookup")
        self.bq_client = None
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """List available resources"""
            return [
                Resource(
                    uri="field://discovery",
                    name="Field Discovery Service",
                    description="Semantic field discovery using vector search",
                    mimeType="application/json"
                ),
                Resource(
                    uri="field://status",
                    name="Service Status",
                    description="Current status of the field discovery service",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content"""
            if uri == "field://discovery":
                return json.dumps({
                    "service": "field-lookup",
                    "version": "1.0.0",
                    "description": "Semantic field discovery for Looker fields",
                    "capabilities": [
                        "extract_searchable_terms",
                        "semantic_field_search", 
                        "discover_fields_for_query"
                    ]
                }, indent=2)
            elif uri == "field://status":
                return json.dumps({
                    "status": "active",
                    "bigquery_connected": self.bq_client is not None,
                    "vector_search_available": True,  # Modern vector search replaces spaCy
                    "project_id": PROJECT_ID,
                    "dataset_id": DATASET_ID
                }, indent=2)
            else:
                raise ValueError(f"Unknown resource: {uri}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available tools"""
            return [
                Tool(
                    name="extract_searchable_terms",
                    description="Extract searchable terms (nouns, codes, business concepts) from natural language",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_text": {
                                "type": "string",
                                "description": "Natural language query to extract terms from"
                            }
                        },
                        "required": ["query_text"]
                    }
                ),
                Tool(
                    name="semantic_field_search",
                    description="Find Looker fields that semantically match search terms using vector similarity",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "searchable_terms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of terms to search for"
                            },
                            "explore_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "pattern": "^[^:]+:[^:]+$"
                                },
                                "description": "Optional list of explore filters (model:explore format)"
                            },
                            "limit_per_term": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum results per search term"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "default": 0.7,
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Minimum cosine similarity threshold"
                            }
                        },
                        "required": ["searchable_terms"]
                    }
                ),
                Tool(
                    name="discover_fields_for_query",
                    description="High-level field discovery that combines term extraction and semantic search",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query_text": {
                                "type": "string",
                                "description": "Natural language query to analyze"
                            },
                            "explore_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "pattern": "^[^:]+:[^:]+$"
                                },
                                "description": "Optional list of explore filters (model:explore format)"
                            },
                            "limit_per_term": {
                                "type": "integer",
                                "default": 5,
                                "description": "Maximum results per search term"
                            },
                            "similarity_threshold": {
                                "type": "number",
                                "default": 0.6,
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Minimum cosine similarity threshold"
                            }
                        },
                        "required": ["query_text"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool calls"""
            try:
                await self._ensure_bigquery_client()
                
                if name == "extract_searchable_terms":
                    result = self.extract_searchable_terms(arguments["query_text"])
                    return [TextContent(
                        type="text",
                        text=json.dumps({"searchable_terms": result}, indent=2)
                    )]
                
                elif name == "semantic_field_search":
                    result = await self.semantic_field_search(
                        searchable_terms=arguments["searchable_terms"],
                        explore_ids=arguments.get("explore_ids"),
                        limit_per_term=arguments.get("limit_per_term", 5),
                        similarity_threshold=arguments.get("similarity_threshold", 0.7)
                    )
                    return [TextContent(
                        type="text",
                        text=json.dumps([match.dict() for match in result], indent=2)
                    )]
                
                elif name == "discover_fields_for_query":
                    result = await self.discover_fields_for_query(
                        query_text=arguments["query_text"],
                        explore_ids=arguments.get("explore_ids"),
                        limit_per_term=arguments.get("limit_per_term", 5),
                        similarity_threshold=arguments.get("similarity_threshold", 0.6)
                    )
                    return [TextContent(
                        type="text",
                        text=json.dumps(result.dict(), indent=2)
                    )]
                
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    async def _ensure_bigquery_client(self):
        """Ensure BigQuery client is initialized"""
        if self.bq_client is None:
            self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
            logger.info(f"Initialized BigQuery client for project: {BQ_PROJECT_ID}")
    
    def extract_searchable_terms(self, query_text: str) -> List[str]:
        """
        Extract searchable terms from natural language query using regex patterns.
        
        DEPRECATED: spaCy noun extraction has been replaced with modern vector search.
        This method now uses simple regex patterns for basic term extraction.
        
        Args:
            query_text: "Show me customer lifetime value for orders with status shipped"
        
        Returns:
            ["customer", "lifetime", "value", "orders", "status", "shipped"]
        """
        logger.info("Using regex-based term extraction (spaCy deprecated)")
        
        searchable_terms = []
        
        # Extract basic words (3+ characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query_text.lower())
        searchable_terms.extend(words)
        
        # Extract quoted strings (often codes or specific values)
        quoted_pattern = r"['\"]([^'\"]+)['\"]"
        quoted_matches = re.findall(quoted_pattern, query_text)
        searchable_terms.extend([match.lower() for match in quoted_matches])
        
        # Extract potential codes (alphanumeric patterns)
        code_pattern = r'\b[A-Z0-9]{2,}[A-Z0-9_-]*\b'
        code_matches = re.findall(code_pattern, query_text)
        searchable_terms.extend([match.lower() for match in code_matches])
        
        # Extract common business terms compound words
        business_patterns = [
            r'\b(customer\s+lifetime\s+value|CLV|LTV)\b',
            r'\b(return\s+on\s+investment|ROI)\b',
            r'\b(average\s+order\s+value|AOV)\b',
            r'\b(customer\s+acquisition\s+cost|CAC)\b',
            r'\b(monthly\s+recurring\s+revenue|MRR)\b',
            r'\b(annual\s+recurring\s+revenue|ARR)\b',
        ]
        
        for pattern in business_patterns:
            matches = re.findall(pattern, query_text, re.IGNORECASE)
            searchable_terms.extend([match.lower().replace(' ', '_') for match in matches])
        
        # Remove duplicates and filter out very short terms
        unique_terms = list(set([term for term in searchable_terms if len(term) > 2]))
        
        logger.info(f"Extracted {len(unique_terms)} searchable terms from: '{query_text}'")
        logger.debug(f"Terms: {unique_terms}")
        
        return unique_terms
    
    async def semantic_field_search(
        self,
        searchable_terms: List[str], 
        explore_ids: Optional[List[str]] = None,
        limit_per_term: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[FieldMatch]:
        """
        Find Looker fields that semantically match the searchable terms
        
        Args:
            searchable_terms: ["customer", "lifetime", "value", "status", "shipped"]
            explore_ids: Optional list of explores to filter (model:explore format)
            limit_per_term: Max results per search term
            similarity_threshold: Minimum cosine similarity
        
        Returns:
            List of FieldMatch objects with similarity scores and matching values
        """
        if not searchable_terms:
            return []
        
        await self._ensure_bigquery_client()
        all_results = []
        
        for term in searchable_terms:
            try:
                # Generate embedding for search term
                embedding_query = f"""
                SELECT ML.GENERATE_EMBEDDING(
                    MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.{EMBEDDING_MODEL}`,
                    @search_term
                ) AS query_embedding
                """
                
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("search_term", "STRING", term)
                    ]
                )
                
                embedding_result = self.bq_client.query(embedding_query, job_config=job_config).result()
                query_embedding = next(embedding_result).query_embedding
                
                # Build search query with optional explore filters
                where_clause = ""
                query_params = [
                    bigquery.ArrayQueryParameter("query_embedding", "FLOAT64", query_embedding),
                    bigquery.ScalarQueryParameter("similarity_threshold", "FLOAT64", similarity_threshold),
                    bigquery.ScalarQueryParameter("limit_per_term", "INT64", limit_per_term),
                    bigquery.ScalarQueryParameter("search_term", "STRING", term)
                ]
                
                if explore_ids:
                    # Build WHERE clause for multiple explores
                    explore_conditions = []
                    for i, explore_id in enumerate(explore_ids):
                        model_name, explore_name = explore_id.split(':')
                        model_param = f"model_name_{i}"
                        explore_param = f"explore_name_{i}"
                        explore_conditions.append(f"(model_name = @{model_param} AND explore_name = @{explore_param})")
                        query_params.extend([
                            bigquery.ScalarQueryParameter(model_param, "STRING", model_name),
                            bigquery.ScalarQueryParameter(explore_param, "STRING", explore_name)
                        ])
                    where_clause = f"AND ({' OR '.join(explore_conditions)})"
                
                # Enhanced search that groups results by field but preserves individual values
                search_query = f"""
                WITH ranked_matches AS (
                  SELECT 
                    field_location,
                    model_name,
                    explore_name,
                    view_name,
                    field_name,
                    field_type,
                    field_description,
                    field_value,
                    value_frequency,
                    @search_term as search_term,
                    (1 - ML.DISTANCE(embedding, @query_embedding, 'COSINE')) as similarity,
                    ROW_NUMBER() OVER (
                      PARTITION BY field_location 
                      ORDER BY (1 - ML.DISTANCE(embedding, @query_embedding, 'COSINE')) DESC
                    ) as rank_in_field
                  FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
                  WHERE (1 - ML.DISTANCE(embedding, @query_embedding, 'COSINE')) >= @similarity_threshold
                      {where_clause}
                ),
                
                field_aggregated AS (
                  SELECT 
                    field_location,
                    model_name,
                    explore_name,
                    view_name,
                    field_name,
                    field_type,
                    field_description,
                    search_term,
                    -- Get the best matching values for this field
                    ARRAY_AGG(
                      STRUCT(field_value, similarity, value_frequency) 
                      ORDER BY similarity DESC 
                      LIMIT 3
                    ) as top_matching_values,
                    -- Use the best similarity score for this field
                    MAX(similarity) as best_similarity
                  FROM ranked_matches
                  WHERE rank_in_field <= 3  -- Top 3 values per field
                  GROUP BY 1,2,3,4,5,6,7,8
                )
                
                SELECT * FROM field_aggregated
                ORDER BY best_similarity DESC
                LIMIT @limit_per_term
                """
                
                job_config = bigquery.QueryJobConfig(query_parameters=query_params)
                results = self.bq_client.query(search_query, job_config=job_config).result()
                
                for row in results:
                    # Convert top_matching_values to a more usable format
                    matching_values = [
                        {
                            "value": val.field_value,
                            "similarity": float(val.similarity),
                            "frequency": int(val.value_frequency)
                        }
                        for val in row.top_matching_values
                    ]
                    
                    field_match = FieldMatch(
                        field_location=row.field_location,
                        model_name=row.model_name,
                        explore_name=row.explore_name,
                        view_name=row.view_name,
                        field_name=row.field_name,
                        field_type=row.field_type,
                        field_description=row.field_description,
                        search_term=row.search_term,
                        similarity=float(row.best_similarity),
                        matching_values=matching_values
                    )
                    
                    all_results.append(field_match)
                    
            except Exception as e:
                logger.error(f"Error searching for term '{term}': {e}")
                continue
        
        # Sort by similarity and remove duplicates
        unique_results = {}
        for result in all_results:
            key = result.field_location
            if key not in unique_results or result.similarity > unique_results[key].similarity:
                unique_results[key] = result
        
        sorted_results = sorted(unique_results.values(), key=lambda x: x.similarity, reverse=True)
        
        logger.info(f"Found {len(sorted_results)} unique field matches")
        return sorted_results
    
    async def discover_fields_for_query(
        self, 
        query_text: str, 
        explore_ids: Optional[List[str]] = None,
        limit_per_term: int = 5,
        similarity_threshold: float = 0.6
    ) -> FieldDiscoveryResult:
        """
        High-level function to discover relevant fields for a natural language query
        
        Args:
            query_text: Natural language query to analyze
            explore_ids: Optional list of explores to filter (model:explore format)
            limit_per_term: Max results per search term
            similarity_threshold: Minimum cosine similarity
        
        Returns:
            FieldDiscoveryResult with searchable terms, discovered fields, and categorized suggestions
        """
        # Extract searchable terms
        searchable_terms = self.extract_searchable_terms(query_text)
        
        # Perform semantic field search
        discovered_fields = await self.semantic_field_search(
            searchable_terms=searchable_terms,
            explore_ids=explore_ids,
            limit_per_term=limit_per_term,
            similarity_threshold=similarity_threshold
        )
        
        # Categorize discovered fields by type
        field_suggestions = {
            "dimensions": [],
            "measures": [],
            "filters": []
        }
        
        for field in discovered_fields:
            field_location = field.field_location
            
            if field.field_type == "dimension":
                field_suggestions["dimensions"].append(field_location)
                # Dimensions can also be used as filters
                field_suggestions["filters"].append(field_location)
            elif field.field_type == "measure":
                field_suggestions["measures"].append(field_location)
        
        result = FieldDiscoveryResult(
            searchable_terms=searchable_terms,
            discovered_fields=discovered_fields,
            field_suggestions=field_suggestions
        )
        
        logger.info(f"Field discovery complete: {len(searchable_terms)} terms, {len(discovered_fields)} fields found")
        return result
    
    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Field Lookup MCP Server...")
        logger.info(f"Project: {BQ_PROJECT_ID}, Dataset: {DATASET_ID}")
        
        # Initialize BigQuery client
        await self._ensure_bigquery_client()
        
        # Run the server using stdio transport
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

def main():
    """Main entry point"""
    server = FieldLookupMCPServer()
    asyncio.run(server.run())

if __name__ == "__main__":
    main()
