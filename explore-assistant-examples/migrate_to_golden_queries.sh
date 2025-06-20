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

# Configuration
SOURCE_TABLE="explore_assistant_examples"
TARGET_TABLE="golden_queries"

echo "=== Looker Explore Assistant Data Migration ==="
echo "Project: $PROJECT_ID"
echo "Dataset: $DATASET_ID"
echo "Source Table: $SOURCE_TABLE"
echo "Target Table: $TARGET_TABLE"
echo ""

# Check if user wants dry run first
if [ "$1" != "--execute" ]; then
    echo "Running DRY RUN first (no actual changes will be made)..."
    echo "Add --execute flag to actually perform the migration"
    echo ""
    
    python migrate_to_golden_queries.py \
    --project_id "$PROJECT_ID" \
    --dataset_id "$DATASET_ID" \
    --source_table "$SOURCE_TABLE" \
    --target_table "$TARGET_TABLE" \
    --dry_run
    
    echo ""
    echo "To execute the migration, run:"
    echo "$0 --execute"
else
    echo "EXECUTING MIGRATION..."
    echo "This will modify your BigQuery tables!"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python migrate_to_golden_queries.py \
        --project_id "$PROJECT_ID" \
        --dataset_id "$DATASET_ID" \
        --source_table "$SOURCE_TABLE" \
        --target_table "$TARGET_TABLE" \
        --clear_target
    else
        echo "Migration cancelled"
        exit 1
    fi
fi