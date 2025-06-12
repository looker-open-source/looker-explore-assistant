# Google Cloud Run Deployment Guide

This guide provides scripts and instructions for deploying the Looker Explore Assistant MCP Server to Google Cloud Run.

## Prerequisites

Before deploying, ensure you have:

1. **Google Cloud CLI** installed and configured
   ```bash
   # Install gcloud CLI (if not already installed)
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   
   # Authenticate with Google Cloud
   gcloud auth login
   ```

2. **Docker** installed on your local machine

3. **Required permissions** in your GCP project:
   - Cloud Run Admin
   - Cloud Build Editor
   - Artifact Registry Admin
   - Service Account User

## Files Overview

- `Dockerfile` - Container configuration for the MCP server
- `deploy_to_cloudrun.sh` - Main deployment script
- `update_env_vars.sh` - Script to update environment variables after deployment
- `.dockerignore` - Files to exclude from Docker build context

## Deployment Steps

### 1. Configure the Deployment Script

Edit `deploy_to_cloudrun.sh` and set your project ID:

```bash
PROJECT_ID="your-actual-project-id"  # Replace with your GCP project ID
REGION="us-central1"  # Optional: change to your preferred region
```

### 2. Run the Deployment Script

```bash
./deploy_to_cloudrun.sh
```

This script will:
- Enable required GCP APIs
- Create an Artifact Registry repository
- Build the container image using Cloud Build
- Deploy to Cloud Run with placeholder environment variables

### 3. Configure Environment Variables

After deployment, run the environment variable update script:

```bash
./update_env_vars.sh
```

This script will prompt you for the required configuration values:

#### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MCP_SHARED_SECRET` | Secure secret for MCP authentication | `your-secure-secret-123` |
| `LOOKER_API_CLIENT_ID` | Looker API client ID | `abc123def456` |
| `LOOKER_API_CLIENT_SECRET` | Looker API client secret | `xyz789uvw012` |
| `LOOKER_BASE_URL` | Looker instance URL | `https://your-instance.looker.com` |
| `LOOKERSDK_VERIFY_SSL` | SSL verification (true/false) | `true` |

#### Automatically Set Variables

These are set automatically by the deployment script:

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `PROJECT` | GCP Project ID | Your project ID |
| `REGION` | GCP Region | `us-central1` |
| `VERTEX_MODEL` | Vertex AI model name | `gemini-2.0-flash-001` |
| `PORT` | Service port | `8080` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `FLASK_ENV` | Flask environment | `production` |

## Manual Environment Variable Updates

You can also update individual environment variables manually:

```bash
gcloud run services update looker-explore-assistant-mcp \
    --region=us-central1 \
    --set-env-vars "KEY=VALUE"
```

## Service Management

### View Service Status
```bash
gcloud run services describe looker-explore-assistant-mcp --region=us-central1
```

### View Logs
```bash
gcloud run logs read looker-explore-assistant-mcp --region=us-central1 --follow
```

### Test the Service
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe looker-explore-assistant-mcp --region=us-central1 --format='value(status.url)')

# Test health endpoint
curl $SERVICE_URL/health
```

### Scale the Service
```bash
gcloud run services update looker-explore-assistant-mcp \
    --region=us-central1 \
    --min-instances=1 \
    --max-instances=10
```

## Security Considerations

### Authentication

The service is deployed with `--allow-unauthenticated` for simplicity. For production:

1. **Remove unauthenticated access:**
   ```bash
   gcloud run services remove-iam-policy-binding looker-explore-assistant-mcp \
       --region=us-central1 \
       --member="allUsers" \
       --role="roles/run.invoker"
   ```

2. **Add specific users/service accounts:**
   ```bash
   gcloud run services add-iam-policy-binding looker-explore-assistant-mcp \
       --region=us-central1 \
       --member="user:your-email@domain.com" \
       --role="roles/run.invoker"
   ```

### Secrets Management

For production deployments, consider using Google Secret Manager instead of environment variables for sensitive data:

```bash
# Create a secret
gcloud secrets create looker-api-secret --data-file=secret.txt

# Update the service to use the secret
gcloud run services update looker-explore-assistant-mcp \
    --region=us-central1 \
    --update-secrets="LOOKER_API_CLIENT_SECRET=looker-api-secret:latest"
```

## Troubleshooting

### Common Issues

1. **Build failures:** Check Cloud Build logs in the GCP Console
2. **Service startup failures:** Check Cloud Run logs with `gcloud run logs read`
3. **Authentication errors:** Verify Looker credentials are correct
4. **Permission errors:** Ensure your account has the required IAM roles

### Debugging Commands

```bash
# View recent logs
gcloud run logs read looker-explore-assistant-mcp --region=us-central1 --limit=50

# View service configuration
gcloud run services describe looker-explore-assistant-mcp --region=us-central1

# Test with verbose output
curl -v $SERVICE_URL/health
```

## Cost Optimization

Cloud Run charges for CPU and memory usage. To optimize costs:

1. **Set appropriate resource limits:**
   ```bash
   gcloud run services update looker-explore-assistant-mcp \
       --region=us-central1 \
       --memory=512Mi \
       --cpu=0.5
   ```

2. **Use minimum instances carefully:** Setting `--min-instances=0` saves money but increases cold start time.

3. **Monitor usage:** Use Cloud Monitoring to track service usage and optimize accordingly.

## Development vs Production

### Development Configuration
- `--min-instances=0` (save costs)
- `--allow-unauthenticated` (easier testing)
- `LOG_LEVEL=DEBUG` (detailed logging)

### Production Configuration
- `--min-instances=1` (reduce cold starts)
- IAM-based authentication
- `LOG_LEVEL=INFO` or `WARN`
- Use Secret Manager for sensitive data
- Enable VPC connector if needed for internal resources
