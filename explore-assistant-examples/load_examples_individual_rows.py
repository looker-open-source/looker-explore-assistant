import argparse
from google.cloud import bigquery
import json

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Load examples data into BigQuery with individual rows')
    parser.add_argument('--project_id', type=str, required=True, help='Google Cloud project ID')
    parser.add_argument('--dataset_id', type=str, help='BigQuery dataset ID', default='explore_assistant')
    parser.add_argument('--table_id', type=str, help='BigQuery table ID', default='golden_queries')
    parser.add_argument('--explore_id', type=str, required=True, help='The name of the explore in the model:explore_name format')
    parser.add_argument('--json_file', '--file', type=str, help='Path to the JSON file containing the data', default='examples.json')
    return parser.parse_args()

def get_bigquery_client(project_id):
    """Initialize and return a BigQuery client."""
    return bigquery.Client(project=project_id)

def delete_existing_rows(client, project_id, dataset_id, table_id, explore_id):
    """Delete existing rows with the given explore_id."""
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    delete_query = f"DELETE FROM `{full_table_id}` WHERE explore_id = @explore_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)]
    )
    delete_job = client.query(delete_query, job_config=job_config)
    delete_job.result()  # Wait for the job to complete
    if delete_job.errors:
        print(f"Failed to delete existing rows for explore_id {explore_id}: {delete_job.errors}")
    else:
        print(f"Successfully deleted existing rows for explore_id {explore_id}")

def load_examples_from_file(file_path):
    """Load examples data from a JSON file."""
    with open(file_path, 'r') as file:
        return json.load(file)

def insert_examples_into_bigquery(client, dataset_id, table_id, explore_id, examples):
    """Insert examples data into BigQuery as individual rows."""
    
    # Prepare rows for insertion
    rows_to_insert = []
    for example in examples:
        if 'input' in example and 'output' in example:
            rows_to_insert.append({
                'explore_id': explore_id,
                'input': example['input'],
                'output': example['output']
            })
        else:
            print(f"Skipping example with missing input/output: {example}")
    
    if not rows_to_insert:
        print("No valid examples to insert")
        return
    
    # Get table reference
    table_ref = client.dataset(dataset_id).table(table_id)
    table = client.get_table(table_ref)
    
    # Insert the rows
    errors = client.insert_rows_json(table, rows_to_insert)
    
    if not errors:
        print(f"Successfully inserted {len(rows_to_insert)} examples for explore_id {explore_id}")
    else:
        print(f"Encountered errors while inserting data: {errors}")

def main():
    args = parse_arguments()
    
    # Initialize BigQuery client
    client = get_bigquery_client(args.project_id)
    
    # Delete existing rows for this explore_id
    delete_existing_rows(client, args.project_id, args.dataset_id, args.table_id, args.explore_id)
    
    # Load examples from file
    examples = load_examples_from_file(args.json_file)
    
    # Insert examples into BigQuery
    insert_examples_into_bigquery(client, args.dataset_id, args.table_id, args.explore_id, examples)

if __name__ == '__main__':
    main()
