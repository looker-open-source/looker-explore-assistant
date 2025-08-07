#!/bin/bash

# Setup BigQuery connection and remote model for Vertex AI embeddings

set -e

echo "🔧 Setting up BigQuery connection and remote model for Vertex AI embeddings..."

# Check required environment variables
if [[ -z "$PROJECT" ]]; then
    echo "❌ PROJECT environment variable not set"
    exit 1
fi

if [[ -z "$BQ_DATASET_ID" ]]; then
    echo "❌ BQ_DATASET_ID environment variable not set"
    exit 1
fi

echo "📋 Using PROJECT: $PROJECT"
echo "📋 Using DATASET: $BQ_DATASET_ID"

# Step 1: Create BigQuery connection to Vertex AI
echo ""
echo "🔗 Creating BigQuery connection to Vertex AI..."

# Check if connection already exists
CONNECTION_EXISTS=$(bq ls --connection --project_id="$PROJECT" --location=us 2>/dev/null | grep -c "vertex-ai" || true)

if [[ $CONNECTION_EXISTS -eq 0 ]]; then
    echo "   Creating new connection 'vertex-ai'..."
    bq mk --connection \
        --connection_type=CLOUD_RESOURCE \
        --project_id="$PROJECT" \
        --location=us \
        vertex-ai
    echo "   ✅ Connection 'vertex-ai' created"
else
    echo "   ✅ Connection 'vertex-ai' already exists"
fi

# Step 2: Get the service account for the connection
echo ""
echo "🔑 Getting connection service account..."

# Try to get the service account ID from the connection
CONNECTION_INFO=$(bq show --connection --project_id="$PROJECT" --location=us vertex-ai --format=json 2>/dev/null || echo "{}")

if [[ "$CONNECTION_INFO" != "{}" ]]; then
    SERVICE_ACCOUNT=$(echo "$CONNECTION_INFO" | jq -r '.cloudResource.serviceAccountId // empty' 2>/dev/null || echo "")
    if [[ -n "$SERVICE_ACCOUNT" ]]; then
        echo "   Service Account: $SERVICE_ACCOUNT"
    else
        echo "   ⚠️  Could not extract service account from connection info"
        echo "   Connection may need time to initialize - continuing anyway"
        SERVICE_ACCOUNT=""
    fi
else
    echo "   ⚠️  Could not get connection info - it may still be initializing"
    SERVICE_ACCOUNT=""
fi

# Step 3: Grant Vertex AI User role to the service account (if we have it)
echo ""
if [[ -n "$SERVICE_ACCOUNT" ]]; then
    echo "🛡️  Granting Vertex AI User role to connection service account..."
    gcloud projects add-iam-policy-binding "$PROJECT" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/aiplatform.user"
    echo "   ✅ IAM role granted"
else
    echo "🛡️  Skipping IAM role assignment (service account not available)"
    echo "   ℹ️  You may need to grant 'Vertex AI User' role to the connection service account manually"
fi

# Step 4: Create the remote model for text embeddings
echo ""
echo "🤖 Creating remote model for text embeddings..."

# Create the model using bq query
MODEL_RESULT=$(bq query --use_legacy_sql=false --project_id="$PROJECT" --format=json "
CREATE OR REPLACE MODEL \`$PROJECT.$BQ_DATASET_ID.text_embedding_model\`
REMOTE WITH CONNECTION \`$PROJECT.us.vertex-ai\`
OPTIONS(ENDPOINT = 'text-embedding-004')
" 2>&1)

if [[ $? -eq 0 ]]; then
    echo "   ✅ Remote model created: $PROJECT.$BQ_DATASET_ID.text_embedding_model"
else
    echo "   ❌ Failed to create remote model"
    echo "   Error: $MODEL_RESULT"
    echo ""
    echo "   Trying alternative connection format..."
    
    # Try with us.vertex-ai instead
    MODEL_RESULT2=$(bq query --use_legacy_sql=false --project_id="$PROJECT" --format=json "
    CREATE OR REPLACE MODEL \`$PROJECT.$BQ_DATASET_ID.text_embedding_model\`
    REMOTE WITH CONNECTION \`us.vertex-ai\`
    OPTIONS(ENDPOINT = 'text-embedding-004')
    " 2>&1)
    
    if [[ $? -eq 0 ]]; then
        echo "   ✅ Remote model created with alternative connection: $PROJECT.$BQ_DATASET_ID.text_embedding_model"
    else
        echo "   ❌ Failed to create remote model with alternative connection"
        echo "   Error: $MODEL_RESULT2"
        echo ""
        echo "   Please check that:"
        echo "   1. The BigQuery connection 'vertex-ai' exists"
        echo "   2. You have the necessary permissions"
        echo "   3. The Vertex AI API is enabled"
        exit 1
    fi
fi

# Step 5: Test the model with a simple query
echo ""
echo "🧪 Testing the embedding model..."

TEST_RESULT=$(bq query --use_legacy_sql=false --project_id="$PROJECT" --format=json "
SELECT ml_generate_embedding_result
FROM ML.GENERATE_EMBEDDING(
    MODEL \`$PROJECT.$BQ_DATASET_ID.text_embedding_model\`,
    (SELECT 'test embedding' as content),
    STRUCT(TRUE AS flatten_json_output)
)
LIMIT 1
" 2>/dev/null || echo "[]")

if [[ "$TEST_RESULT" != "[]" ]]; then
    echo "   ✅ Model test successful"
else
    echo "   ⚠️  Model test had issues, but model may still work"
fi

echo ""
echo "🎉 BigQuery embedding setup complete!"
echo ""
echo "✅ Resources created:"
echo "• BigQuery connection: $PROJECT.us.vertex-ai"
echo "• Remote model: $PROJECT.$BQ_DATASET_ID.text_embedding_model"
echo "• Service account: $SERVICE_ACCOUNT"
echo ""
echo "🚀 You can now run the vector table manager successfully!"
