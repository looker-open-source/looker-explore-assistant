# BigQuery Data Loader

This folder includes two scripts. 
The first script (generate_examples.py) will create input/output example pairs for training or one-shot use. These are based on the top queries for a chosen model and explore. The script will also create measure and dimension lists for later use.

The loading script (load_examples.py) facilitates the loading of JSON data into Google BigQuery while managing data freshness by ensuring existing rows related to an `explore_id` are deleted before new data is inserted. The script employs a temporary table mechanism to circumvent limitations related to immediate updates or deletions in BigQuery's streaming buffer.

## Prerequisites

Before you run this script, you need to ensure that your environment is set up with the following requirements:

1. **Python 3.6 or higher** - Make sure Python is installed on your system.
2. **Google Cloud SDK** - Install and configure the Google Cloud SDK (gcloud).
3. **BigQuery API Access** - Ensure that the BigQuery API is enabled in your Google Cloud project.
4. **Google Cloud Authentication** - Set up authentication by downloading a service account key and setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to that key file.
5. **Looker SDK Initialization** - Set up authentication for the Looker SDK by specifying these variables:
`LOOKERSDK_BASE_URL`	A URL like https://my.looker.com:19999. No default value.
`LOOKERSDK_CLIENT_ID` API credentials client_id. This and client_secret must be provided in some fashion to the Node SDK, or no calls to the API will be authorized. No default value.
`LOOKERSDK_CLIENT_SECRET` API credentials client_secret. No default value.


## Setup

To run this script, you will need to install its dependencies. It is recommended to use a virtual environment at the top level of the repo:

```bash
python -m venv .venv
source .venv/bin/activate
cd ./explore-assistant-examples
pip install -r requirements.txt
```
## Usage

### Loading Script Parameters

The script accepts several command line arguments to specify the details required for loading data into BigQuery:

- `--project_id`: **Required.** The Google Cloud project ID where your BigQuery dataset resides.
- `--dataset_id`: The ID of the BigQuery dataset. Defaults to `explore_assistant`.
- `--table_id`: The ID of the BigQuery table where the data will be inserted. Defaults to `explore_assistant_examples`.
- `--explore_id`: **Required.** A unique identifier for the dataset rows related to a specific use case or query (used in deletion and insertion).
- `--json_file`: The path to the JSON file containing the data to be loaded. Defaults to `examples.json`.

### Running the Loading Script

 **Before Running:** make sure the .env file in this directory is updated to reference your project_id, dataset_id and explore_id

To run the script, use the following command format in your terminal:

Load the general examples:
>After modifying the load_examples.sh file, run the script below to modify the permissions for the file so it can be run via command line
```bash
chmod +x load_examples.sh
```
>This script will upload examples to a selected bigquery dataset
```bash
./load_examples.sh
```

Load the refinement examples:
>After modifying the update_refinements.sh file, run the script below to modify the permissions for the file so it can be run via command line
```bash
chmod +x update_refinements.sh
```
>This script will upload refinement_examples to a selected bigquery dataset
```bash
 ./update_refinements.sh
```

Load the samples:
>After modifying the update_samples.sh file, run the script below to modify the permissions for the file so it can be run via command line
```bash
chmod +x update_samples.sh
```
>This script will upload samples to a selected bigquery dataset
```bash
./update_samples.sh
```

Update the general examples:
>After modifying the update_examples.sh file, run the script below to modify the permissions for the file so it can be run via command line
```bash
chmod +x update_examples.sh
```
>This script will upload new examples from examples_outputfull to a selected bigquery dataset
```bash
./update_examples.sh
```


Load the trusted dashboard lookml

```bash
 python load_examples.py --project_id YOUR_PROJECT_ID --explore_id YOUR_EXPLORE_ID --table_id trusted_dashboards --json_file trusted_dashboards.lkml --format text --column_name lookml
=======
chmod +x update_examples.sh
```


### Description

The load_examples Python script is designed to manage data uploads from a JSON file into a Google BigQuery table, particularly focusing on scenarios where specific entries identified by an `explore_id` need to be refreshed or updated in the dataset.

1. **Command Line Interface (CLI)**:
   - The script uses `argparse` to define and handle command line inputs that specify the Google Cloud project, dataset, and table details, as well as the path to the JSON data file.

2. **BigQuery Client Initialization**:
   - It initializes a BigQuery client using the Google Cloud project ID provided through the CLI. This client facilitates interactions with BigQuery, such as running queries and managing data.

3. **Data Deletion**:
   - Before inserting new data, the script deletes existing rows in the specified BigQuery table that match the given `explore_id`. This is crucial for use cases where the data associated with an `explore_id` needs to be refreshed or updated without duplication.

4. **Data Loading from JSON**:
   - The script reads data from a specified JSON file. This data is expected to be in a format that BigQuery can ingest.

5. **Data Insertion into BigQuery**:
   - After deletion of old data, the script inserts the new data from the JSON file into the BigQuery table. It constructs a SQL `INSERT` statement and executes it using the BigQuery client. Proper parameterization of the query is utilized to safeguard against SQL injection.

6. **Error Handling**:
   - Throughout the data deletion and insertion processes, the script checks for and reports any errors that occur. This is vital for debugging and ensuring data integrity.

### Generation Script Parameters
The generate_examples.py script accepts several command line arguments to specify the details required for generating example files:

- `--model`: Required. Looker model name.
- `--explore`: Required. Looker explore name.
- `--project_id`: Required. Google Cloud project ID.
- `--location`: Required. Google Cloud location.

# Running the Generation Script
The generate_examples.py script fetches information about an explores' fields and top queries. It calls Gemini to generate sample questions that could be answered by the top queries. These can be tuned or used directly as examples to upload to the Explore Assistant.

```bash
python generate_examples.py --model YOUR_MODEL_NAME --explore YOUR_EXPLORE_NAME --project_id YOUR_GCP_PROJECT_ID --location YOUR_GCP_LOCATION
```
   
If desired, you can directly upload the files after generation by using the --chain_load argument.
```bash
python generate_examples.py --model YOUR_MODEL_NAME --explore YOUR_EXPLORE_NAME --project_id YOUR_GCP_PROJECT_ID --location YOUR_GCP_LOCATION --chain_load
```
