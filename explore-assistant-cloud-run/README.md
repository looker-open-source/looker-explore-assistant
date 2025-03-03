# Looker Explore Assistant

A FastAPI-based service that provides an AI-powered assistant for Looker explores, helping users generate and understand Looker queries.

## Features

- User authentication and authorization
- Chat-based interface for Looker query generation
- Integration with Looker API
- Chat history management
- Feedback collection
- Search functionality for past conversations
- Vertex AI integration for query generation

## Prerequisites

- Python 3.11+
- MySQL database (Cloud SQL)
- Google Cloud Platform account with:
  - Vertex AI enabled
  - BigQuery enabled
  - Cloud Run access
  - Artifact Registry access
  - Cloud Build access
- Looker instance with API access
- Required IAM roles:
  - `roles/aiplatform.user`
  - `roles/cloudbuild.builds.editor`
  - `roles/run.admin`
  - `roles/iam.serviceAccountUser`
  - `roles/storage.objectViewer`
  - `roles/iam.serviceAccountTokenCreator`

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
PROJECT_NAME=your-gcp-project
REGION_NAME=your-gcp-region
LOOKER_API_URL=https://your-looker-instance/api/4.0
LOOKER_CLIENT_ID=your-looker-client-id
LOOKER_CLIENT_SECRET=your-looker-client-secret
CLOUD_SQL_HOST=your-cloud-sql-host
CLOUD_SQL_USER=your-db-user
CLOUD_SQL_PASSWORD=your-db-password
CLOUD_SQL_DATABASE=your-db-name
BIGQUERY_DATASET=your-bigquery-dataset
BIGQUERY_TABLE=your-bigquery-table
MODEL_NAME=gemini-1.0-pro-001
IS_DEV_SERVER=true/false
OAUTH_CLIENT_ID=your-oauth-client-id
VERTEX_CF_AUTH_TOKEN=your-vertex-auth-token
IMAGE_NAME=explore-assistant-api-ken  # For deployment
```

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the database:
```bash
# The database tables will be created automatically when the application starts
# Make sure your Cloud SQL instance is running and accessible
```

## Running the Application

### Local Development

```bash
python main.py
```

The application will be available at `http://localhost:8000`

### Using Docker

1. Build the Docker image:
```bash
docker build -t looker-explore-assistant .
```

2. Run the container:
```bash
docker run -p 8000:8000 --env-file .env looker-explore-assistant
```

## Testing

The project uses pytest for testing. To run the tests:

```bash
# Set environment variables and run tests
set -a && source .env && pytest test.py
```

### Test Coverage

The tests cover:
- User authentication
- Chat creation and management
- Message handling
- Feedback submission
- Search functionality
- Error handling
- API endpoints

## API Endpoints

### Authentication
- `POST /login` - Authenticate user and create/get user profile

### Chat Management
- `POST /chat` - Create a new chat thread
- `GET /chat/history` - Retrieve chat history
- `GET /chat/search` - Search through chat history

### Query Generation
- `POST /prompt` - Generate Looker queries or general responses
- `POST /feedback` - Submit feedback on generated responses

## Project Structure

```
explore-assistant-cloud-run/
├── main.py              # FastAPI application and routes
├── models.py            # Database and request/response models
├── helper_functions.py  # Business logic and utilities
├── database.py         # Database connection and session management
├── test.py             # Test cases
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
├── cloudrun_build.sh  # Build and push script for Cloud Run
└── .env              # Environment variables
```

## Development Workflow

1. Create a new branch for your feature/fix
2. Make your changes
3. Run tests to ensure everything works
4. Submit a pull request

## Deployment

The application is deployed using a combination of Docker, Cloud Run, and Terraform.

### Building and Pushing the Image

1. Make sure your `.env` file is properly configured with all required variables
2. Run the build script:
```bash
bash cloudrun_build.sh
```

This script will:
- Build the Docker image with AMD64 architecture compatibility
- Create an Artifact Registry repository if it doesn't exist
- Push the image to the registry
- Output the required variables for terraform deployment

### Terraform Deployment

1. After the image is pushed, copy the output variables to your `variables.tfvars`:
```hcl
image = "asia-southeast1-docker.pkg.dev/[PROJECT_ID]/looker-explore-assistant/explore-assistant-api-ken:latest"
use_cloud_run_backend = true
```

2. Run terraform to deploy in looker-explore-assistant/explore-assistant-backend/terraform/cloud_run:
```bash
terraform init
terraform plan -var-file="variables.tfvars"
terraform apply -var-file="variables.tfvars"
```

### Post-Deployment

After deployment, make sure to:
1. Assign the `roles/aiplatform.user` role to the Cloud Run service account
2. Verify the application is accessible and functioning correctly
3. Monitor logs for any issues

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Add your license information here]