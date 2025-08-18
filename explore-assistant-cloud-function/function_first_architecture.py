#!/usr/bin/env python3

"""
Function-First Architecture Implementation
Forces vector search execution before LLM generation to bypass LLM function calling resistance.
"""

import re
import asyncio
import json
from typing import List, Dict, Any, Optional
from field_lookup_service import FieldValueLookupService
from mcp_server import call_vertex_ai_with_retry

class ForcedVectorSearchHandler:
    """
    Bypasses LLM function calling by pre-executing vector searches
    and injecting results directly into the prompt.
    """
    
    def __init__(self):
        self.field_service = FieldValueLookupService()
        
    async def extract_searchable_entities(self, query: str) -> List[str]:
        """Use LLM to intelligently extract potential filter values from query."""
        
        extraction_prompt = f"""You are a data analysis assistant. Extract any specific values from the user query that might be used as filters in a database query.

Look for:
- Brand names (Nike, Adidas, Apple, etc.)
- Product codes/SKUs (686, ABC123, etc.)  
- Product names or models
- Category names
- Status values (active, pending, etc.)
- Location names
- Any other specific identifiers that could be dimension values

Return ONLY a JSON array of the extracted values. If no specific values are found, return an empty array [].

Examples:
- "Show me Nike sales" → ["Nike"]
- "Revenue for product code 686" → ["686"] 
- "Sales of iPhone and Samsung Galaxy" → ["iPhone", "Samsung Galaxy"]
- "Active customers in California" → ["active", "California"]
- "Show me total revenue" → []

User query: {query}

Response (JSON array only):"""

        try:
            # Construct Vertex AI request for entity extraction
            vertex_request = {
                "model": "gemini-2.0-flash-exp",
                "contents": [
                    {
                        "role": "user", 
                        "parts": [{"text": extraction_prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.5,
                    "topK": 20,
                    "maxOutputTokens": 200,
                    "responseMimeType": "application/json",
                    "candidateCount": 1
                }
            }
            
            # Call LLM for entity extraction
            response = call_vertex_ai_with_retry(vertex_request, "entity_extraction", process_response=False)
            
            if not response or 'candidates' not in response:
                print(f"❌ Entity extraction failed - using fallback")
                return self._fallback_entity_extraction(query)
                
            # Extract the JSON array from response
            candidate = response['candidates'][0] if response['candidates'] else {}
            content = candidate.get('content', {})
            parts = content.get('parts', [])
            
            if not parts:
                print(f"❌ No response parts - using fallback")  
                return self._fallback_entity_extraction(query)
                
            response_text = parts[0].get('text', '').strip()
            
            try:
                entities = json.loads(response_text)
                if isinstance(entities, list):
                    print(f"🧠 LLM extracted entities: {entities}")
                    return [str(entity).strip() for entity in entities if entity]
                else:
                    print(f"❌ LLM returned non-array: {entities} - using fallback")
                    return self._fallback_entity_extraction(query)
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON parse error: {e} - using fallback")
                print(f"Raw response: {response_text}")
                return self._fallback_entity_extraction(query)
                
        except Exception as e:
            print(f"❌ Error in LLM entity extraction: {e} - using fallback")
            return self._fallback_entity_extraction(query)
    
    def _fallback_entity_extraction(self, query: str) -> List[str]:
        """Fallback regex-based entity extraction if LLM fails."""
        entities = []
        
        # Pattern for brands/codes - look for quoted terms or specific patterns
        patterns = [
            r'["\']([^"\']+)["\']',  # Quoted terms
            r'\b([A-Z][A-Z0-9]{2,})\b',  # All caps codes like 55DSL, BDI
            r'\b(\d{3,})\b',  # Numeric codes like 686
        ]
        
        # Common brand names to search for
        brand_keywords = [
            'Nike', 'Adidas', 'Apple', 'Samsung', 'Calvin Klein', 'Levis', 
            'Gap', 'H&M', 'Zara', '55DSL', 'BDI', 'Barmah', 'Alia', 'Alfani'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities.extend(matches)
        
        # Check for brand keywords
        query_upper = query.upper()
        for brand in brand_keywords:
            if brand.upper() in query_upper:
                entities.append(brand)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)
        
        print(f"📋 Fallback extracted entities: {unique_entities}")
        return unique_entities
    
    async def pre_execute_vector_search(self, entities: List[str]) -> Dict[str, List[Dict]]:
        """Execute vector searches for all entities before LLM generation."""
        results = {}
        
        for entity in entities:
            try:
                search_results = await self.field_service.field_value_lookup(entity, None, 3)
                if search_results:
                    results[entity] = search_results
                    print(f"🔍 Pre-executed search for '{entity}': found {len(search_results)} matches")
                else:
                    print(f"❌ No results for '{entity}'")
            except Exception as e:
                print(f"❌ Error searching '{entity}': {e}")
        
        return results
    
    def inject_search_results_into_prompt(self, original_prompt: str, search_results: Dict[str, List[Dict]]) -> str:
        """Inject pre-executed search results directly into the LLM prompt."""
        
        if not search_results:
            return original_prompt
        
        # Build injection text
        injection = "\n\n🔍 VECTOR SEARCH RESULTS (PRE-EXECUTED):\n"
        injection += "The following entities were found in the database:\n\n"
        
        for entity, results in search_results.items():
            injection += f"Entity: '{entity}'\n"
            for result in results:
                injection += f"  ✅ Found in: {result['field_location']}\n"
                injection += f"     Value: {result['field_value']}\n"
                injection += f"     Frequency: {result['value_frequency']}\n"
            injection += "\n"
        
        injection += "⚡ USE THESE EXACT FIELD LOCATIONS in your filters. Do not guess other field names.\n"
        injection += "=" * 50 + "\n"
        
        return injection + original_prompt
    
    async def process_query_with_forced_vector_search(self, query: str) -> tuple[str, Dict[str, List[Dict]]]:
        """
        Main method: Extract entities, execute searches, return enhanced prompt.
        
        Returns:
            (enhanced_prompt, search_results_dict)
        """
        print(f"🚀 Processing query with Function-First Architecture")
        print(f"Original query: {query}")
        
        # Step 1: Extract searchable entities
        entities = await self.extract_searchable_entities(query)
        print(f"📋 Extracted entities: {entities}")
        
        # Step 2: Pre-execute vector searches
        search_results = await self.pre_execute_vector_search(entities)
        
        # Step 3: Inject results into prompt
        enhanced_prompt = self.inject_search_results_into_prompt(query, search_results)
        
        print(f"✅ Enhanced prompt length: {len(enhanced_prompt)} chars")
        print(f"✅ Search results for {len(search_results)} entities")
        
        return enhanced_prompt, search_results

# Example usage
async def demo_function_first_architecture():
    """Demonstrate the Function-First Architecture approach."""
    
    handler = ForcedVectorSearchHandler()
    
    test_queries = [
        "Show me sales for Nike products",
        "Find revenue for 686 product code",  
        "Sales data for 55DSL brand items",
        "How much did we sell of Barmah Hats?",
        "Find orders with BDI products"
    ]
    
    print("🎯 DEMONSTRATING FUNCTION-FIRST ARCHITECTURE")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print("-" * 30)
        
        enhanced_prompt, search_results = await handler.process_query_with_forced_vector_search(query)
        
        print(f"🎁 ENHANCED PROMPT:")
        print(enhanced_prompt[:500] + "..." if len(enhanced_prompt) > 500 else enhanced_prompt)
        
        if search_results:
            print(f"\n✅ GUARANTEED VECTOR SEARCH EXECUTION!")
            print(f"Results: {list(search_results.keys())}")
        else:
            print(f"\n⚪ No entities found to search")

if __name__ == "__main__":
    import os
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    asyncio.run(demo_function_first_architecture())
