#!/bin/bash
set -a  # automatically export all variables
source .env
set +a

# Validate required environment variables
if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set in .env file"
    exit 1
fi

if [ -z "$DATASET_ID" ]; then
    echo "Error: DATASET_ID is not set in .env file"
    exit 1
fi

if [ -z "$EXPLORE_ID" ]; then
    echo "Error: EXPLORE_ID is not set in .env file"
    exit 1
fi

TABLE_ID="explore_assistant_examples"       ##The ID of the BigQuery table where the data will be inserted. Set to explore_assistant_examples.
JSON_FILE="nabc_examples.json"                   ##The path to the JSON file containing the data to be loaded. Set to examples.json.

python load_examples.py \
--project_id "$PROJECT_ID" \
--dataset_id "$DATASET_ID" \
--explore_id "$EXPLORE_ID" \
--table_id "$TABLE_ID" \
--json_file "$JSON_FILE"
