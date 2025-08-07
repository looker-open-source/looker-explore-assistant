#!/usr/bin/env python3
"""Quick script to check the actual table schema"""

import os
from google.cloud import bigquery

BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "ml-accelerator-dbarr")
DATASET_ID = os.environ.get("BQ_DATASET_ID", "explore_assistant")
TABLE_NAME = "field_values_for_vectorization"

client = bigquery.Client(project=BQ_PROJECT_ID)

# Get table schema
table_ref = client.dataset(DATASET_ID).table(TABLE_NAME)
table = client.get_table(table_ref)

print("Table Schema:")
for field in table.schema:
    print(f"  {field.name}: {field.field_type}")

print(f"\nTotal rows: {table.num_rows}")

# Get a sample of the data
query = f"""
SELECT * FROM `{BQ_PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}` 
LIMIT 3
"""

result = client.query(query).result()
print(f"\nSample data:")
for i, row in enumerate(result):
    print(f"Row {i+1}:")
    for key, value in row.items():
        print(f"  {key}: {value}")
    print()
