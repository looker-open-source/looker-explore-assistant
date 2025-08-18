#!/usr/bin/env python3

"""
Enhanced Function-First Architecture Integration
Integrates LLM-based entity extraction with vector search into MCP server workflow.
"""

import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from field_lookup_service import FieldValueLookupService

class EnhancedVectorSearchIntegration:
    """
    Integrates intelligent entity extraction with vector search for use in
    explore selection and parameter generation.
    """
    
    def __init__(self):
        self.field_service = FieldValueLookupService()
    
    def extract_entities_with_llm_call(self, query: str, call_vertex_ai_func) -> List[str]:
        """
        Use LLM to intelligently extract potential filter values from query.
        Takes the call_vertex_ai function as parameter to avoid circular imports.
        """
        
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
            response = call_vertex_ai_func(vertex_request, "entity_extraction", process_response=False)
            
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
    
    async def execute_vector_searches(self, entities: List[str]) -> Dict[str, List[Dict]]:
        """Execute vector searches for all entities."""
        results = {}
        
        for entity in entities:
            try:
                search_results = await self.field_service.field_value_lookup(entity, None, 5)
                if search_results:
                    results[entity] = search_results
                    print(f"🔍 Vector search for '{entity}': found {len(search_results)} matches")
                else:
                    print(f"❌ No vector search results for '{entity}'")
            except Exception as e:
                print(f"❌ Error in vector search for '{entity}': {e}")
        
        return results
    
    def create_vector_search_context(self, search_results: Dict[str, List[Dict]]) -> str:
        """Create context string to inject into prompts with vector search results."""
        
        if not search_results:
            return ""
        
        context = "\n\n🔍 VECTOR SEARCH RESULTS:\n"
        context += "The following specific values were found in the database:\n\n"
        
        for entity, results in search_results.items():
            context += f"📍 Entity: '{entity}'\n"
            for i, result in enumerate(results):
                context += f"   {i+1}. Field: {result['field_location']}\n"
                context += f"      Value: {result['field_value']}\n" 
                context += f"      Frequency: {result['value_frequency']}\n"
            context += "\n"
        
        context += "⚡ IMPORTANT: Use these exact field locations for filters. Do not guess field names.\n"
        context += "🎯 These results come from semantic vector search of the actual data.\n"
        context += "=" * 60 + "\n"
        
        return context
    
    def create_explore_selection_context(self, search_results: Dict[str, List[Dict]]) -> str:
        """Create context for explore selection based on vector search results."""
        
        if not search_results:
            return ""
        
        # Group results by explore
        explore_matches = {}
        for entity, results in search_results.items():
            for result in results:
                field_location = result['field_location']
                # Extract explore from field_location (format: model.explore.view.field)
                parts = field_location.split('.')
                if len(parts) >= 2:
                    explore_key = f"{parts[0]}:{parts[1]}"
                    if explore_key not in explore_matches:
                        explore_matches[explore_key] = []
                    explore_matches[explore_key].append({
                        'entity': entity,
                        'field': field_location,
                        'value': result['field_value'],
                        'frequency': result['value_frequency']
                    })
        
        context = "\n\n🎯 EXPLORE SELECTION GUIDANCE FROM VECTOR SEARCH:\n"
        context += "The following explores contain the user's specific values:\n\n"
        
        for explore_key, matches in explore_matches.items():
            context += f"📊 Explore: {explore_key}\n"
            context += f"   Contains {len(matches)} matching values:\n"
            for match in matches:
                context += f"   - '{match['entity']}' in {match['field']} (freq: {match['frequency']})\n"
            context += "\n"
        
        context += "💡 Prioritize explores with the most relevant matches for the user's query.\n"
        context += "=" * 60 + "\n"
        
        return context
    
    async def enhance_query_with_vector_search(self, query: str, call_vertex_ai_func) -> Tuple[str, str, Dict[str, List[Dict]]]:
        """
        Main integration method: Extract entities, run vector search, create context.
        
        Returns:
            (parameter_generation_context, explore_selection_context, search_results)
        """
        print(f"🚀 Enhancing query with intelligent vector search")
        print(f"Query: {query}")
        
        # Step 1: Extract entities using LLM
        entities = self.extract_entities_with_llm_call(query, call_vertex_ai_func)
        print(f"📋 Extracted entities: {entities}")
        
        if not entities:
            print(f"⚪ No entities found - skipping vector search")
            return "", "", {}
        
        # Step 2: Execute vector searches
        search_results = await self.execute_vector_searches(entities)
        
        if not search_results:
            print(f"⚪ No vector search results - no context enhancement")
            return "", "", {}
        
        # Step 3: Create context strings
        param_context = self.create_vector_search_context(search_results)
        explore_context = self.create_explore_selection_context(search_results)
        
        print(f"✅ Vector search enhancement complete!")
        print(f"   - Parameter context: {len(param_context)} chars")
        print(f"   - Explore context: {len(explore_context)} chars")
        print(f"   - Search results: {len(search_results)} entities")
        
        return param_context, explore_context, search_results

# Global instance for use in MCP server
vector_search_integration = EnhancedVectorSearchIntegration()

# Example usage for testing
async def demo_integration():
    """Test the integration with sample queries."""
    
    from mcp_server import call_vertex_ai_with_retry
    
    test_queries = [
        "Show me Nike sales data",
        "Revenue for 686 and 55DSL products", 
        "How many Barmah Hats did we sell?",
        "Compare BDI vs Alia performance",
        "Total revenue across all products"  # Should return no entities
    ]
    
    print("🧪 TESTING ENHANCED VECTOR SEARCH INTEGRATION")
    print("=" * 70)
    
    for query in test_queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print("-" * 30)
        
        param_context, explore_context, results = await vector_search_integration.enhance_query_with_vector_search(
            query, call_vertex_ai_with_retry
        )
        
        print(f"\n📊 PARAMETER CONTEXT ({len(param_context)} chars):")
        if param_context:
            print(param_context[:300] + "..." if len(param_context) > 300 else param_context)
        else:
            print("(No parameter context)")
        
        print(f"\n🎯 EXPLORE CONTEXT ({len(explore_context)} chars):")  
        if explore_context:
            print(explore_context[:300] + "..." if len(explore_context) > 300 else explore_context)
        else:
            print("(No explore context)")

if __name__ == "__main__":
    import os
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "ml-accelerator-dbarr")
    asyncio.run(demo_integration())
