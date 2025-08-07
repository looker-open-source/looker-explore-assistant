#!/bin/bash

# Quick Demo Setup Script
# Ensures the vector search demo environment is ready

set -e

echo "🎬 Vector Search Demo - Pre-flight Check"
echo "=" * 45

# Check current directory
if [[ ! -f "demo_vector_search.py" ]]; then
    echo "❌ Please run this script from explore-assistant-cloud-function directory"
    echo "   cd explore-assistant-cloud-function"
    exit 1
fi

# Check Python dependencies
echo "🐍 Checking Python dependencies..."
python3 -c "import google.cloud.bigquery; print('✅ BigQuery client available')" || {
    echo "❌ Missing google-cloud-bigquery"
    echo "   pip install google-cloud-bigquery"
    exit 1
}

# Check environment variables
required_vars=("PROJECT" "BQ_DATASET_ID")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "❌ Missing environment variable: $var"
        exit 1
    fi
    echo "✅ $var = ${!var}"
done

# Quick table check
echo "🔍 Checking vector search table..."
python3 -c "
from google.cloud import bigquery
import os

client = bigquery.Client(project=os.environ.get('PROJECT'))
dataset_id = os.environ.get('BQ_DATASET_ID', 'explore_assistant')

try:
    table = client.get_table(f'{os.environ.get(\"PROJECT\")}.{dataset_id}.field_values_for_vectorization')
    print(f'✅ Vector table exists with {table.num_rows:,} rows')
    
    if table.num_rows == 0:
        print('⚠️  Table is empty - run vector setup first:')
        print('   python vector_table_manager.py --action setup')
    elif table.num_rows < 1000:
        print('⚠️  Table has limited data - consider indexing more explores')
    
except Exception as e:
    print(f'❌ Vector table not found: {e}')
    print('   Run setup first: ./setup_field_discovery.sh')
    exit(1)
" || exit 1

echo ""
echo "🎯 Demo Environment Ready!"
echo "Run the demo with:"
echo "   python3 demo_vector_search.py"
echo ""
echo "Or run individual test scripts:"
echo "   python3 test_semantic_search.py"
echo "   python3 test_vector_search.py"
echo ""
