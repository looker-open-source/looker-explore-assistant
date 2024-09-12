##This script will upload new examples from examples_outputfull to a selected bigquery dataset

#!/bin/sh

PROJECT_ID=”PROJECT_ID”
DATASET_ID=”DATASET_ID”
EXPLORE_ID=”MODEL:EXPLORE_ID”
TABLE_ID=”explore_assistant_examples”
JSON_FILE=”examples_outputfull.json”

python load_examples.py \
--project_id $PROJECT_ID \
--dataset_id $DATASET_ID \
--explore_id $EXPLORE_ID \
--table_id $TABLE_ID \
--json_file $JSON_FILE
