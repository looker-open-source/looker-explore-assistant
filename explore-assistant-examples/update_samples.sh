##This script will upload samples to a selected bigquery dataset

source .env
TABLE_ID="explore_assistant_samples"         ##The ID of the BigQuery table where the data will be inserted. Set to explore_assistant_samples.
JSON_FILE="samples.json"                     ##The path to the JSON file containing the data to be loaded. Set to samples.json.

python load_examples.py \
--project_id $PROJECT_ID \
--dataset_id $DATASET_ID \
--explore_id $EXPLORE_ID \
--table_id $TABLE_ID \
--column_name samples \
--json_file $JSON_FILE
