"""
Enhanced Vector Search Integration

Integrates LLM-based entity extraction with vector search for intelligent
field discovery in explore selection and parameter generation.
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable

from vector_search.field_lookup import FieldLookupService
from core.exceptions import VectorSearchError
from llm_utils import parse_llm_response

import logging
logger = logging.getLogger(__name__)


class EnhancedVectorIntegration:
    """
    Integrates intelligent entity extraction with vector search for use in
    explore selection and parameter generation.
    """
    
    def __init__(self):
        self.field_service = FieldLookupService()
    
    def extract_entities_with_llm_call(self, query: str, call_vertex_ai_func: Callable) -> List[str]:
        """
        Use LLM to intelligently extract potential filter values from query.
        Takes the call_vertex_ai function as parameter to avoid circular imports.
        """
        
        extraction_prompt = f"""You are a data analysis assistant. Extract any specific values from the user query that might be used as filters in a database query.

Examples:
- "sales for Adidas" -> ["Adidas"]  
- "revenue by state in California" -> ["California"]
- "orders from 2024 with status pending" -> ["2024", "pending"]
- "top products by category Electronics" -> ["Electronics"]
- "users in New York and Chicago" -> ["New York", "Chicago"]

Query: {query}

Return only a JSON array of extracted values, no explanation:"""
        
        try:
            request_body = {
                "contents": [{
                    "role": "user",
                    "parts": [{"text": extraction_prompt}]
                }],
                "generationConfig": {
                    "maxOutputTokens": 500,
                    "temperature": 0.1,
                    "topP": 0.8,
                    "topK": 20
                }
            }
            
            response = call_vertex_ai_func(request_body)
            
            if response and 'candidates' in response:
                text_response = response['candidates'][0]['content']['parts'][0]['text']
                logger.info(f"🤖 Raw LLM response: {text_response[:200]}")
                
                # Preprocess to remove markdown code blocks
                clean_response = text_response.strip()
                if clean_response.startswith('```'):
                    # Find the end of the opening fence
                    lines = clean_response.split('\n')
                    if len(lines) > 1:
                        # Remove first line (```json or ```)
                        lines = lines[1:]
                        # Remove last line if it's closing fence
                        if lines and lines[-1].strip() == '```':
                            lines = lines[:-1]
                        clean_response = '\n'.join(lines).strip()
                
                # Use robust LLM response parser on cleaned text
                parsed_response = parse_llm_response(clean_response)
                logger.info(f"🧹 Cleaned response: {clean_response[:100]}")
                
                if parsed_response and isinstance(parsed_response, list):
                    # Filter out empty strings and very short values
                    filtered_entities = [e for e in parsed_response if isinstance(e, str) and len(e.strip()) > 1]
                    logger.info(f"🧠 LLM extracted entities: {filtered_entities}")
                    return filtered_entities[:5]  # Limit to 5 entities
                else:
                    logger.warning(f"LLM response wasn't a valid array. Parsed: {parsed_response}")
                    return []
            
            return []
            
        except Exception as e:
            logger.error(f"LLM entity extraction failed: {e}")
            return []
    
    
    async def enhance_query_with_vector_search(self, query: str, call_vertex_ai_func: Callable) -> Tuple[str, str, Dict[str, List]]:
        """
        Enhance a query with vector search results for better parameter generation.
        
        Args:
            query: The user's natural language query
            call_vertex_ai_func: Function to call Vertex AI API
            
        Returns:
            Tuple of (param_context, explore_context, search_results)
        """
        
        logger.info(f"🔍 Enhancing query with vector search: {query}")
        
        try:
            # Step 1: Extract potential entities from the query
            logger.info(f"🎯 Extracting entities from query: {query}")
            entities = self.extract_entities_with_llm_call(query, call_vertex_ai_func)
            logger.info(f"🎯 Final extracted entities: {entities}")
            
            if not entities:
                logger.warning("❌ No entities extracted, skipping vector search enhancement")
                return "", "", {}
            
            # Step 2: Search for relevant fields using the entities
            semantic_results = await self.field_service.search_semantic_fields(
                search_terms=entities,
                limit_per_term=3
            )
            
            # Step 3: Look up field values for the entities
            field_value_results = []
            for entity in entities:
                try:
                    values = await self.field_service.lookup_field_values(
                        search_string=entity,
                        limit=5
                    )
                    field_value_results.extend(values)
                except Exception as e:
                    logger.warning(f"Field value lookup failed for '{entity}': {e}")
            
            # Step 4: Build context strings for parameter generation
            param_context = self._build_parameter_context(semantic_results, field_value_results)
            explore_context = self._build_explore_context(semantic_results)
            
            # Step 5: Organize results for tracking
            search_results = {
                "semantic_fields": [
                    {
                        "field_location": match.field_location,
                        "similarity": match.similarity_score,
                        "description": match.description
                    }
                    for match in semantic_results
                ],
                "field_values": field_value_results
            }
            
            logger.info(f"✅ Vector search enhancement complete: {len(semantic_results)} field matches, {len(field_value_results)} value matches")
            
            return param_context, explore_context, search_results
            
        except Exception as e:
            logger.error(f"Vector search enhancement failed: {e}")
            return "", "", {}
    
    def _build_parameter_context(self, field_matches: List, value_matches: List[Dict]) -> str:
        """Build parameter context for LLM from search results"""
        
        if not field_matches and not value_matches:
            return ""
        
        context = "\\n## 🔍 VECTOR SEARCH DISCOVERIES:\\n"
        
        if field_matches:
            context += f"\\n### Relevant Fields Found ({len(field_matches)}):\\n"
            for match in field_matches[:5]:  # Top 5 field matches
                context += f"- **{match.field_location}** (similarity: {match.similarity_score:.2f})\\n"
                if match.description:
                    context += f"  Description: {match.description}\\n"
        
        if value_matches:
            context += f"\\n### Field Values Found ({len(value_matches)}):\\n"
            # Group by field location
            by_field = {}
            for match in value_matches:
                field = match["field_location"]
                if field not in by_field:
                    by_field[field] = []
                by_field[field].append(match["value"])
            
            for field, values in by_field.items():
                context += f"- **{field}**: {', '.join(str(v) for v in values[:3])}\\n"
        
        context += "\\n⚠️ USE THESE DISCOVERED FIELDS AND VALUES IN YOUR QUERY PARAMETERS\\n"
        
        return context
    
    def _build_explore_context(self, field_matches: List) -> str:
        """Build explore context for explore selection"""
        
        if not field_matches:
            return ""
        
        # Group fields by explore
        by_explore = {}
        for match in field_matches:
            # Assuming field_location format: model.explore.view.field
            parts = match.field_location.split('.')
            if len(parts) >= 2:
                explore_key = f"{parts[0]}.{parts[1]}"
                if explore_key not in by_explore:
                    by_explore[explore_key] = []
                by_explore[explore_key].append(match)
        
        context = f"\\n## Vector Search Suggests These Explores:\\n"
        for explore_key, matches in by_explore.items():
            avg_similarity = sum(m.similarity_score for m in matches) / len(matches)
            context += f"- **{explore_key}** (avg similarity: {avg_similarity:.2f}, {len(matches)} fields)\\n"
        
        return context
    
    async def search_field_semantically(self, search_terms: List[str], explore_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Simplified semantic field search interface
        
        Args:
            search_terms: Terms to search for
            explore_filter: Optional explore IDs to filter by
            
        Returns:
            List of field matches
        """
        try:
            matches = await self.field_service.search_semantic_fields(
                search_terms=search_terms,
                explore_ids=explore_filter,
                limit_per_term=5
            )
            
            return [
                {
                    "field_location": match.field_location,
                    "field_name": match.field_name,
                    "similarity": match.similarity_score,
                    "description": match.description,
                    "field_type": match.field_type
                }
                for match in matches
            ]
            
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(f"Semantic field search failed: {e}", search_type="semantic")
    
    async def lookup_field_values_by_string(self, search_string: str, field_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Simplified field value lookup interface
        
        Args:
            search_string: String to search for in field values
            field_filter: Optional field location to filter by
            
        Returns:
            List of value matches
        """
        try:
            return await self.field_service.lookup_field_values(
                search_string=search_string,
                field_location=field_filter,
                limit=10
            )
            
        except VectorSearchError:
            raise
        except Exception as e:
            raise VectorSearchError(f"Field value lookup failed: {e}", search_type="field_values")