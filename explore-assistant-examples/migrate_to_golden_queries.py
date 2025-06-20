import argparse
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import json

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Migrate data from explore_assistant_examples to golden_queries table')
    parser.add_argument('--project_id', type=str, required=True, help='Google Cloud project ID')
    parser.add_argument('--dataset_id', type=str, help='BigQuery dataset ID', default='explore_assistant')
    parser.add_argument('--source_table', type=str, help='Source table name', default='explore_assistant_examples')
    parser.add_argument('--target_table', type=str, help='Target table name', default='golden_queries')
    parser.add_argument('--dry_run', action='store_true', help='Show what would be migrated without actually doing it')
    parser.add_argument('--clear_target', action='store_true', help='Clear target table before migration')
    return parser.parse_args()

def get_bigquery_client(project_id):
    """Initialize and return a BigQuery client."""
    return bigquery.Client(project=project_id)

def create_golden_queries_table_if_not_exists(client, project_id, dataset_id, target_table):
    """Create the golden_queries table if it doesn't exist."""
    table_id = f"{project_id}.{dataset_id}.{target_table}"
    
    try:
        # Check if table exists
        client.get_table(table_id)
        print(f"Table {table_id} already exists")
        return True
    except NotFound:
        print(f"Table {table_id} does not exist, creating it...")
        
        # Define the schema for golden_queries table
        schema = [
            bigquery.SchemaField("explore_id", "STRING", mode="REQUIRED", description="The explore identifier"),
            bigquery.SchemaField("input", "STRING", mode="REQUIRED", description="The user input/question"),
            bigquery.SchemaField("output", "STRING", mode="REQUIRED", description="The expected Looker query output/parameters"),
        ]
        
        # Create the table
        table = bigquery.Table(table_id, schema=schema)
        table.description = "Golden queries table for Looker Explore Assistant examples - migrated from explore_assistant_examples"
        
        try:
            table = client.create_table(table)
            print(f"✅ Created table {table_id}")
            return True
        except Exception as e:
            print(f"❌ Failed to create table {table_id}: {e}")
            return False

def read_source_data(client, project_id, dataset_id, source_table):
    """Read all data from the source explore_assistant_examples table."""
    query = f"""
    SELECT 
        explore_id,
        examples
    FROM `{project_id}.{dataset_id}.{source_table}`
    ORDER BY explore_id
    """
    
    print(f"Reading data from {project_id}.{dataset_id}.{source_table}...")
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        
        source_data = []
        for row in results:
            source_data.append({
                'explore_id': row.explore_id,
                'examples': row.examples
            })
        
        print(f"Found {len(source_data)} rows in source table")
        return source_data
    
    except NotFound:
        print(f"❌ Source table {project_id}.{dataset_id}.{source_table} does not exist")
        return None
    except Exception as e:
        print(f"❌ Error reading source table: {e}")
        return None

def parse_examples_json(examples_json_str):
    """Parse the JSON string from the examples column and extract individual examples."""
    try:
        examples_data = json.loads(examples_json_str)
        
        # Handle different possible JSON structures
        individual_examples = []
        
        if isinstance(examples_data, list):
            # Direct list of examples
            for example in examples_data:
                if isinstance(example, dict) and 'input' in example and 'output' in example:
                    individual_examples.append({
                        'input': example['input'],
                        'output': example['output']
                    })
        elif isinstance(examples_data, dict):
            # Could be nested structure, try to find examples
            if 'examples' in examples_data:
                examples_list = examples_data['examples']
                if isinstance(examples_list, list):
                    for example in examples_list:
                        if isinstance(example, dict) and 'input' in example and 'output' in example:
                            individual_examples.append({
                                'input': example['input'],
                                'output': example['output']
                            })
            # Or it could be a direct dict with input/output
            elif 'input' in examples_data and 'output' in examples_data:
                individual_examples.append({
                    'input': examples_data['input'],
                    'output': examples_data['output']
                })
            # Or it could have multiple example keys
            else:
                for key, value in examples_data.items():
                    if isinstance(value, list):
                        for example in value:
                            if isinstance(example, dict) and 'input' in example and 'output' in example:
                                individual_examples.append({
                                    'input': example['input'],
                                    'output': example['output']
                                })
        
        return individual_examples
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Error processing examples: {e}")
        return []

def convert_to_golden_queries_format(source_data):
    """Convert source data to golden_queries format (individual rows)."""
    golden_queries_rows = []
    
    for source_row in source_data:
        explore_id = source_row['explore_id']
        examples_json = source_row['examples']
        
        print(f"\nProcessing explore_id: {explore_id}")
        
        # Parse the JSON examples
        individual_examples = parse_examples_json(examples_json)
        
        if not individual_examples:
            print(f"  Warning: No valid examples found for {explore_id}")
            continue
        
        print(f"  Found {len(individual_examples)} individual examples")
        
        # Create individual rows for golden_queries table
        for i, example in enumerate(individual_examples, 1):
            golden_queries_rows.append({
                'explore_id': explore_id,
                'input': example['input'],
                'output': example['output']
            })
            print(f"    {i}. Input: {example['input'][:50]}...")
    
    return golden_queries_rows

def clear_target_table(client, project_id, dataset_id, target_table):
    """Clear all data from the target table."""
    delete_query = f"DELETE FROM `{project_id}.{dataset_id}.{target_table}` WHERE TRUE"
    print(f"Clearing target table {project_id}.{dataset_id}.{target_table}...")
    
    try:
        delete_job = client.query(delete_query)
        delete_job.result()
        
        if delete_job.errors:
            print(f"Failed to clear target table: {delete_job.errors}")
            return False
        else:
            print("Target table cleared successfully")
            return True
    except Exception as e:
        print(f"Error clearing target table: {e}")
        return False

def insert_golden_queries_data(client, project_id, dataset_id, target_table, golden_queries_rows, dry_run=False):
    """Insert data into the golden_queries table."""
    if dry_run:
        print(f"\n=== DRY RUN: Would insert {len(golden_queries_rows)} rows ===")
        
        # Group by explore_id for summary
        explore_counts = {}
        for row in golden_queries_rows:
            explore_id = row['explore_id']
            explore_counts[explore_id] = explore_counts.get(explore_id, 0) + 1
        
        print("Summary by explore_id:")
        for explore_id, count in explore_counts.items():
            print(f"  {explore_id}: {count} examples")
        
        # Show first few examples
        print("\nFirst 3 examples that would be inserted:")
        for i, row in enumerate(golden_queries_rows[:3], 1):
            print(f"  {i}. {row['explore_id']}: {row['input'][:60]}...")
        
        return True
    
    if not golden_queries_rows:
        print("No data to insert")
        return True
    
    try:
        # Get table reference
        table_ref = client.dataset(dataset_id).table(target_table)
        table = client.get_table(table_ref)
        
        # Insert in batches to avoid memory issues
        batch_size = 1000
        total_rows = len(golden_queries_rows)
        
        print(f"\nInserting {total_rows} rows into {project_id}.{dataset_id}.{target_table}...")
        
        for i in range(0, total_rows, batch_size):
            batch = golden_queries_rows[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_rows + batch_size - 1) // batch_size
            
            print(f"  Inserting batch {batch_num}/{total_batches} ({len(batch)} rows)...")
            
            errors = client.insert_rows_json(table, batch)
            
            if errors:
                print(f"Errors in batch {batch_num}: {errors}")
                return False
        
        print(f"Successfully inserted all {total_rows} rows")
        return True
    
    except Exception as e:
        print(f"Error inserting data: {e}")
        return False

def verify_migration(client, project_id, dataset_id, source_table, target_table):
    """Verify the migration by comparing counts."""
    print("\n=== Verification ===")
    
    try:
        # Count source examples (total JSON objects)
        source_query = f"SELECT COUNT(*) as count FROM `{project_id}.{dataset_id}.{source_table}`"
        source_result = list(client.query(source_query).result())[0]
        source_count = source_result.count
        
        # Count target rows
        target_query = f"SELECT COUNT(*) as count FROM `{project_id}.{dataset_id}.{target_table}`"
        target_result = list(client.query(target_query).result())[0]
        target_count = target_result.count
        
        # Count by explore_id in target
        explore_counts_query = f"""
        SELECT 
            explore_id,
            COUNT(*) as example_count
        FROM `{project_id}.{dataset_id}.{target_table}`
        GROUP BY explore_id
        ORDER BY explore_id
        """
        explore_results = client.query(explore_counts_query).result()
        
        print(f"Source table ({source_table}): {source_count} JSON records")
        print(f"Target table ({target_table}): {target_count} individual examples")
        print("\nExamples by explore_id in target table:")
        
        for row in explore_results:
            print(f"  {row.explore_id}: {row.example_count} examples")
    
    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    args = parse_arguments()
    
    # Initialize BigQuery client
    client = get_bigquery_client(args.project_id)
    
    try:
        # Step 0: Create target table if it doesn't exist
        if not args.dry_run:
            if not create_golden_queries_table_if_not_exists(client, args.project_id, args.dataset_id, args.target_table):
                print("Failed to create target table, aborting")
                return
        else:
            print(f"DRY RUN: Would check/create table {args.project_id}.{args.dataset_id}.{args.target_table}")
        
        # Step 1: Read source data
        source_data = read_source_data(client, args.project_id, args.dataset_id, args.source_table)
        
        if source_data is None:
            return
        
        if not source_data:
            print("No data found in source table")
            return
        
        # Step 2: Convert to golden_queries format
        golden_queries_rows = convert_to_golden_queries_format(source_data)
        
        if not golden_queries_rows:
            print("No valid examples found to migrate")
            return
        
        # Step 3: Clear target table if requested
        if args.clear_target and not args.dry_run:
            if not clear_target_table(client, args.project_id, args.dataset_id, args.target_table):
                print("Failed to clear target table, aborting")
                return
        
        # Step 4: Insert data (or show what would be inserted)
        success = insert_golden_queries_data(
            client, args.project_id, args.dataset_id, args.target_table, 
            golden_queries_rows, args.dry_run
        )
        
        if not success:
            print("Migration failed")
            return
        
        # Step 5: Verify (only if not dry run)
        if not args.dry_run:
            verify_migration(client, args.project_id, args.dataset_id, args.source_table, args.target_table)
        
        print("\n🎉 Migration completed successfully!")
        
        if args.dry_run:
            print("\nTo actually perform the migration, run without --dry_run flag")
        
    except Exception as e:
        print(f"Migration failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()