from google.cloud import bigquery
import json


def get_bigquery_client(project_id):
    """Initialize and return a BigQuery client."""
    return bigquery.Client(project=project_id)


def delete_existing_rows(client, project_id, dataset_id, table_id):
    """Delete existing rows in the given table."""
    full_table_id = f"{project_id}.{dataset_id}.{table_id}"
    delete_query = f"DELETE FROM `{full_table_id}` WHERE 1=1"
    delete_job = client.query(delete_query)
    delete_job.result()  # Wait for the job to complete
    if delete_job.errors:
        print(
            f"Failed to delete existing rows for table_id {table_id}: {delete_job.errors}"
        )
    else:
        print(f"Successfully deleted rows for table_id {table_id}")


def load_data_from_file(json_file_path):
    """Load data from a JSON file."""
    with open(json_file_path, "r") as file:
        return json.load(file)


def insert_data_into_bigquery(
    client, dataset_id, table_id, explore_id, data, column_name
):
    """Insert data into BigQuery using a SQL INSERT statement."""
    data_json = json.dumps(data)
    insert_query = f"""
    INSERT INTO `{dataset_id}.{table_id}` (explore_id, {column_name})
    VALUES (@explore_id, @data)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("explore_id", "STRING", explore_id),
            bigquery.ScalarQueryParameter("data", "STRING", data_json),
        ]
    )
    query_job = client.query(insert_query, job_config=job_config)
    query_job.result()  # Wait for the query to complete
    if query_job.errors is None:
        print(f"Data has been successfully inserted for explore_id {explore_id}")
    else:
        print(
            f"Encountered errors while inserting data for explore_id {explore_id}: {query_job.errors}"
        )
