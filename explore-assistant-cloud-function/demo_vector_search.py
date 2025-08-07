#!/usr/bin/env python3
"""
Comprehensive Vector Search Demo Script

This script provides an interactive demonstration of the semantic field discovery
system, showing how natural language queries match to Looker fields and values.
"""

import json
import logging
import os
import sys
import time
from typing import List, Dict, Any
from datetime import datetime

try:
    from dotenv import load_dotenv
    if os.path.exists('.env'):
        load_dotenv()
except ImportError:
    pass

from google.cloud import bigquery

# Configure logging for demo
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Clean output for demo
)
logger = logging.getLogger(__name__)

# Environment configuration
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
FIELD_VALUES_TABLE = "field_values_for_vectorization"

class VectorSearchDemo:
    """Interactive demo class for vector search capabilities"""
    
    def __init__(self):
        self.bq_client = bigquery.Client(project=BQ_PROJECT_ID)
        print(f"🔧 Connected to BigQuery project: {BQ_PROJECT_ID}")
        print(f"📊 Using dataset: {DATASET_ID}")
        print()
    
    def system_health_check(self):
        """Check if the vector search system is ready"""
        print("🏥 SYSTEM HEALTH CHECK")
        print("=" * 50)
        
        try:
            # Check if table exists
            table_ref = f"{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}"
            table = self.bq_client.get_table(table_ref)
            print(f"✅ Vector table exists: {table.num_rows:,} rows")
            
            # Check embedding model
            model_ref = f"{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model"
            try:
                model = self.bq_client.get_model(model_ref)
                print(f"✅ Embedding model exists: {model.model_id}")
            except Exception:
                print("⚠️  Embedding model not found (may still work)")
            
            # Get basic statistics
            stats_query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT CONCAT(model_name, ':', explore_name)) as unique_explores,
                COUNT(DISTINCT field_name) as unique_fields,
                COUNT(DISTINCT field_type) as field_types,
                COUNT(DISTINCT field_value) as unique_values
            FROM `{table_ref}`
            """
            
            results = self.bq_client.query(stats_query).result()
            stats = next(results)
            
            print(f"📈 Statistics:")
            print(f"   Total field-value pairs: {stats.total_rows:,}")
            print(f"   Unique explores: {stats.unique_explores}")
            print(f"   Unique fields: {stats.unique_fields}")
            print(f"   Field types: {stats.field_types}")
            print(f"   Unique dimension values: {stats.unique_values:,}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ System check failed: {e}")
            print("   Please run the setup script first:")
            print("   ./setup_field_discovery.sh")
            print()
            return False
    
    def search_with_explanation(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search with detailed explanation"""
        
        print(f"🔍 SEMANTIC SEARCH: '{query}'")
        print("-" * 40)
        
        start_time = time.time()
        
        # Use VECTOR_SEARCH for semantic similarity
        search_query = f"""
        SELECT 
            CONCAT(model_name, ':', explore_name, '.', view_name, '.', field_name) as field_location,
            model_name,
            explore_name,
            view_name,
            field_name,
            field_type,
            field_description,
            field_value,
            value_frequency,
            searchable_text,
            distance,
            (1 - distance) as similarity
        FROM VECTOR_SEARCH(
            TABLE `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`,
            'ml_generate_embedding_result',
            (
                SELECT ml_generate_embedding_result
                FROM ML.GENERATE_EMBEDDING(
                    MODEL `{BQ_PROJECT_ID}.{DATASET_ID}.text_embedding_model`,
                    (SELECT @query_text AS content),
                    STRUCT(TRUE AS flatten_json_output)
                )
            ),
            top_k => @limit
        )
        ORDER BY distance ASC
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[\n                bigquery.ScalarQueryParameter("query_text", "STRING", query),\n                bigquery.ScalarQueryParameter("limit", "INT64", limit)\n            ]
        )
        
        try:
            results = self.bq_client.query(search_query, job_config=job_config).result()
            
            matches = []
            for i, row in enumerate(results, 1):
                match = {
                    "rank": i,
                    "field_location": row.field_location,
                    "model": row.model_name,
                    "explore": row.explore_name,
                    "view": row.view_name,
                    "field": row.field_name,
                    "type": row.field_type,
                    "description": row.field_description or "No description",
                    "sample_value": row.field_value,
                    "frequency": row.value_frequency,
                    "similarity": float(row.similarity),
                    "distance": float(row.distance)
                }
                matches.append(match)
            
            # Display results
            elapsed = time.time() - start_time
            print(f"⚡ Query executed in {elapsed:.3f} seconds")
            print(f"📊 Found {len(matches)} semantic matches:")
            print()
            
            for match in matches:
                similarity_bar = "█" * int(match["similarity"] * 20)
                print(f"  {match['rank']}. {match['field_location']} ({match['type']})")
                print(f"     🎯 Similarity: {match['similarity']:.3f} |{similarity_bar}|")
                print(f"     💡 Sample Value: '{match['sample_value']}'")
                if match['description'] != "No description":
                    print(f"     📝 Description: {match['description']}")
                if match['type'] == 'dimension' and match['frequency'] > 1:
                    print(f"     📊 Value Frequency: {match['frequency']:,} occurrences")
                print()
            
            return matches
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
    
    def run_business_scenarios(self):
        """Run realistic business query scenarios"""
        print("💼 BUSINESS SCENARIO DEMOS")
        print("=" * 50)
        
        scenarios = [
            {
                "title": "E-commerce Product Analysis",
                "queries": ["premium brands", "product categories", "inventory levels"]
            },
            {
                "title": "Customer Analytics", 
                "queries": ["customer lifetime value", "user demographics", "purchase history"]
            },
            {
                "title": "Sales Performance",
                "queries": ["revenue by region", "order dates", "sales metrics"]
            },
            {
                "title": "Fashion & Retail",
                "queries": ["clothing categories", "seasonal products", "size information"]
            }
        ]
        
        for scenario in scenarios:
            print(f"📋 {scenario['title']}")
            print("~" * len(scenario['title']))
            
            for query in scenario['queries']:
                matches = self.search_with_explanation(query, limit=3)
                
                if not matches:
                    print("   ⚠️  No matches found - may need more indexed data")
                
                # Brief pause for readability
                time.sleep(0.5)
                
            print("\n")
    
    def interactive_search(self):
        """Interactive search mode for custom queries"""
        print("🎮 INTERACTIVE SEARCH MODE")
        print("=" * 50)
        print("Enter natural language queries to search for Looker fields.")
        print("Examples: 'customer names', 'product pricing', 'sales data'")
        print("Type 'quit' to exit, 'help' for examples")
        print()
        
        while True:
            try:
                query = input("🔍 Search query: ").strip()
                
                if not query:
                    continue
                elif query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                elif query.lower() == 'help':
                    print("💡 Try these example queries:")
                    examples = [
                        "customer information",
                        "product brands",
                        "sales revenue", 
                        "order tracking",
                        "inventory status",
                        "user preferences",
                        "category data"
                    ]
                    for ex in examples:
                        print(f"   • '{ex}'")
                    print()
                    continue
                
                # Perform search
                matches = self.search_with_explanation(query, limit=5)
                
                if matches:
                    print(f"💡 Tip: You could use these fields in a Looker explore:")
                    for match in matches[:3]:
                        print(f"   • {match['field_location']}")
                    print()
                else:
                    print("🤔 No matches found. Try different terms or check if your explores are indexed.")
                    print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                continue
    
    def show_available_data(self):
        """Show what data is available in the system"""
        print("📚 AVAILABLE DATA OVERVIEW")
        print("=" * 50)
        
        # Get explore breakdown
        explore_query = f"""
        SELECT 
            CONCAT(model_name, ':', explore_name) as explore_key,
            COUNT(DISTINCT field_name) as field_count,
            COUNT(*) as total_values,
            STRING_AGG(DISTINCT field_type ORDER BY field_type) as field_types
        FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
        GROUP BY model_name, explore_name
        ORDER BY total_values DESC
        LIMIT 20
        """
        
        try:
            results = self.bq_client.query(explore_query).result()
            
            print("🎯 Top explores by data volume:")
            for row in results:
                print(f"   📊 {row.explore_key}")
                print(f"       Fields: {row.field_count}, Values: {row.total_values:,}, Types: {row.field_types}")
            print()
            
            # Show sample field names for context
            sample_query = f"""
            SELECT DISTINCT field_name
            FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{FIELD_VALUES_TABLE}`
            WHERE field_type = 'dimension'
            ORDER BY field_name
            LIMIT 20
            """
            
            sample_results = self.bq_client.query(sample_query).result()
            print("🔤 Sample dimension field names:")
            field_names = [row.field_name for row in sample_results]
            print(f"   {', '.join(field_names)}")
            print()
            
        except Exception as e:
            print(f"❌ Failed to show available data: {e}")

def main():
    """Main demo function"""
    print("🚀 VECTOR SEARCH FOR LOOKER DIMENSIONS - LIVE DEMO")
    print("=" * 60)
    print(f"⏰ Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    demo = VectorSearchDemo()
    
    # Step 1: Health check
    if not demo.system_health_check():
        print("❌ System not ready. Please run setup first.")
        return
    
    # Step 2: Show available data
    demo.show_available_data()
    
    # Step 3: Run business scenarios
    demo.run_business_scenarios()
    
    # Step 4: Interactive mode (optional)
    print("🎯 DEMO OPTIONS:")
    print("1. Enter interactive search mode")
    print("2. Exit demo")
    print()
    
    choice = input("Choose option (1 or 2): ").strip()
    
    if choice == "1":
        demo.interactive_search()
    
    print("✅ Demo completed successfully!")
    print(f"⏰ Demo ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
