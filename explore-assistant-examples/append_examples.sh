##This script will upload new examples from examples_outputfull to a selected bigquery dataset

source .env
TABLE_ID="golden_queries"             ##The ID of the BigQuery table where the data will be inserted. Set to golden_queries.
JSON_FILE="examples_outputfull.json"              ##The path to the JSON file containing the data to be loaded. Set to examples_outputfull.json.

python load_examples.py \
--project_id $PROJECT_ID \
--dataset_id $DATASET_ID \
--explore_id $EXPLORE_ID \
--table_id $TABLE_ID \
--json_file $JSON_FILE \
--concat
