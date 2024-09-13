#!/bin/sh

##This script will upload refinement_examples to a selected bigquery dataset

PROJECT_ID=”PROJECT_ID”                           ##Required. The Google Cloud project ID where your BigQuery dataset resides.
DATASET_ID=”DATASET_ID”                           ##The ID of the BigQuery dataset. Defaults to explore_assistant.
EXPLORE_ID=”MODEL:EXPLORE_ID”                     ##Required. A unique identifier for the dataset rows related to a specific use case or query (used in deletion and insertion).
TABLE_ID=”explore_assistant_refinement_examples”  ##The ID of the BigQuery table where the data will be inserted. Set to explore_assistant_refinement_examples.
JSON_FILE=”refinement_examples.json”              ##The path to the JSON file containing the data to be loaded. Set to refinement_examples.json.

python load_examples.py \
--project_id $PROJECT_ID \
--dataset_id $DATASET_ID \
--explore_id $EXPLORE_ID \
--table_id $TABLE_ID \
--json_file $JSON_FILE
