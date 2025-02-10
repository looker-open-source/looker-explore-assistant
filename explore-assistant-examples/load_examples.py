import argparse
from google.cloud import bigquery
import json

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Load data into BigQuery')
    parser.add_argument('--project_id', type=str, required=True, help='Google Cloud project ID')
    parser.add_argument('--dataset_id', type=str, help='BigQuery dataset ID', default='explore_assistant')
    parser.add_argument('--table_id', type=str, help='BigQuery table ID', default='explore_assistant_examples')
    parser.add_argument('--column_name', type=str, help='Column name, if different than "examples"', default='examples')
    parser.add_argument('--explore_id', type=str, required=True, help='The name of the explore in the model:explore_name format')
    parser.add_argument('--json_file', '--file', type=str, help='Path to the JSON file containing the data', default='examples.json')
    parser.add_argument('--format', type=str, choices=['json', 'text'], default='json', help='Format of the input file (json or text)')
    parser.add_argument('--concat', action='store_true', help='Concatenate new data with existing data instead of replacing it')
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
        print(f"Successfully deleted rows for explore_id {explore_id}")

def load_data_from_file(file_path, file_format):
    """Load data from a file based on the specified format."""
    with open(file_path, 'r') as file:
        if file_format == 'json':
            return json.load(file)
        elif file_format == 'text':
            return [line.strip() for line in file.readlines()]

def read_existing_data(client, dataset_id, table_id, explore_id, column_name):
    """Read existing data from BigQuery."""
    query = f"SELECT `{column_name}` FROM `{dataset_id}.{table_id}` WHERE explore_id = @explore_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)]
    )
    query_job = client.query(query, job_config=job_config)
    result = query_job.result()
    for row in result:
        return row[column_name]
    return None

def concatenate_json(existing_data, new_data):
    """Concatenate two JSON arrays."""
    if not existing_data:
        return new_data
    existing_data = existing_data.rstrip(']')
    new_data = new_data.lstrip('[')
    return existing_data + ',' + new_data 

def insert_data_into_bigquery(client, dataset_id, table_id, column_name, explore_id, data, concat=False):
    """Insert data into BigQuery using a SQL INSERT statement."""
    # Convert the data to a JSON string
    data_json = json.dumps(data)

    if concat:
            existing_data = read_existing_data(client, dataset_id, table_id, explore_id, column_name)
            if existing_data:
            # Check if the existing data is valid JSON
                valid_json_query = f"""
                    SELECT SAFE.PARSE_JSON(`{column_name}`) IS NOT NULL AS is_valid_json
                    FROM `{dataset_id}.{table_id}`
                    WHERE explore_id = @explore_id
                    """
                job_config = bigquery.QueryJobConfig(
                    query_parameters=[bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id)]
                )
                query_job = client.query(valid_json_query, job_config=job_config)
                result = query_job.result()
                is_valid_json = False
                for row in result:
                    is_valid_json = row['is_valid_json']
                    break

                if is_valid_json:
                    data_json = concatenate_json(existing_data, data_json)
                    # Use an UPDATE statement to update the existing row
                    update_query = f"""
                    UPDATE `{dataset_id}.{table_id}`
                    SET `{column_name}` = @examples
                    WHERE explore_id = @explore_id
                    """
                    job_config = bigquery.QueryJobConfig(
                        query_parameters=[
                            bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id),
                            bigquery.ScalarQueryParameter("examples", "STRING", data_json)
                        ]
                    )
                    query_job = client.query(update_query, job_config=job_config)
                    query_job.result()  # Wait for the query to complete

                    # Check if the query resulted in any errors
                    if query_job.errors is None:
                        print("Data has been successfully updated.")
                    else:
                        print(f"Encountered errors while updating data: {query_job.errors}")
                    return
                else:
                    print(f"Existing data in column '{column_name}' is not valid JSON. Aborting update.")
                    return

    # Create a BigQuery SQL INSERT statement
    insert_query = f"""
    INSERT INTO `{dataset_id}.{table_id}` (explore_id, `{column_name}`)
    VALUES (@explore_id, @examples)
    """

    # Set up query parameters to prevent SQL injection
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id),
            bigquery.ScalarQueryParameter("examples", "STRING", data_json)
        ]
    )

    # Execute the query
    query_job = client.query(insert_query, job_config=job_config)
    query_job.result()  # Wait for the query to complete

    # Check if the query resulted in any errors
    if query_job.errors is None:
        print("Data has been successfully inserted.")
    else:
        print(f"Encountered errors while inserting data: {query_job.errors}")

def main():
    args = parse_arguments()

    # delete existing rows
    client = get_bigquery_client(args.project_id)
    if not args.concat:
        # Delete existing rows if not concatenating
        delete_existing_rows(client, args.project_id, args.dataset_id, args.table_id, args.explore_id)

    # load data from file and insert into BigQuery
    data = load_data_from_file(args.json_file, args.format)
    insert_data_into_bigquery(client, args.dataset_id, args.table_id, args.column_name, args.explore_id, data, args.concat)

if __name__ == '__main__':
    main()