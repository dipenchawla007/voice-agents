# Google Cloud Platform Deployment Guide

This guide provides instructions for deploying the Voice Agent Multi-Tenant System on Google Cloud Platform (GCP) using Cloud Run, Cloud SQL for PostgreSQL, and Cloud Storage.

## Prerequisites

1. A Google Cloud Platform account
2. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
3. Required GCP APIs enabled:
   - Cloud Run
   - Cloud SQL
   - Cloud Storage
   - Secret Manager (optional, for secure API key storage)

## Step 1: Create a GCP Project

If you don't already have a project:

```bash
# Create a new project
gcloud projects create voice-agent-system --name="Voice Agent System"

# Set it as the default project
gcloud config set project voice-agent-system
```

## Step 2: Set up Cloud SQL (PostgreSQL)

1. Create a PostgreSQL instance:

```bash
gcloud sql instances create voice-agents-db \
  --database-version=POSTGRES_15 \
  --cpu=2 \
  --memory=4GB \
  --region=us-central1 \
  --root-password=SECURE_PASSWORD
```

2. Create a database:

```bash
gcloud sql databases create voice_agents --instance=voice-agents-db
```

3. Create a user:

```bash
gcloud sql users create voice_agent_user \
  --instance=voice-agents-db \
  --password=SECURE_USER_PASSWORD
```

Note the connection details as you'll need them later:
- Instance connection name: `voice-agent-system:us-central1:voice-agents-db`

## Step 3: Set up Cloud Storage

1. Create a bucket for knowledge base files:

```bash
gsutil mb -l us-central1 gs://voice-agent-knowledge-base
```

2. Set appropriate permissions (adjust based on your security needs):

```bash
# Make the bucket accessible only to your service account
gsutil iam ch serviceAccount:SERVICE_ACCOUNT_EMAIL:objectAdmin gs://voice-agent-knowledge-base
```

## Step 4: Create Service Account

Create a service account with the necessary permissions:

```bash
# Create service account
gcloud iam service-accounts create voice-agent-service \
  --description="Service account for Voice Agent system" \
  --display-name="Voice Agent Service"

# Get the service account email
SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Voice Agent Service" \
  --format='value(email)')

# Grant necessary roles
gcloud projects add-iam-policy-binding voice-agent-system \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/cloudsql.client"

gcloud projects add-iam-policy-binding voice-agent-system \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"
```

## Step 5: Store Secrets (Optional but Recommended)

Use Secret Manager to store sensitive configuration values:

```bash
# Create secrets
gcloud secrets create openai-api-key --replication-policy="automatic"
gcloud secrets create pinecone-api-key --replication-policy="automatic"
gcloud secrets create jwt-secret --replication-policy="automatic"
gcloud secrets create livekit-api-key --replication-policy="automatic"
gcloud secrets create livekit-api-secret --replication-policy="automatic"

# Set secret values
echo -n "your_openai_api_key" | gcloud secrets versions add openai-api-key --data-file=-
echo -n "your_pinecone_api_key" | gcloud secrets versions add pinecone-api-key --data-file=-
echo -n "your_jwt_secret" | gcloud secrets versions add jwt-secret --data-file=-
echo -n "your_livekit_api_key" | gcloud secrets versions add livekit-api-key --data-file=-
echo -n "your_livekit_api_secret" | gcloud secrets versions add livekit-api-secret --data-file=-

# Grant access to the service account
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding pinecone-api-key \
  --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

# Repeat for other secrets
```

## Step 6: Build and Push Docker Image

1. Build the Docker image:

```bash
# Navigate to your project directory
cd voice-agent-multi-tenant-system

# Build the image
gcloud builds submit --tag gcr.io/voice-agent-system/voice-agent-api
```

## Step 7: Deploy to Cloud Run

```bash
gcloud run deploy voice-agent-api \
  --image gcr.io/voice-agent-system/voice-agent-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --add-cloudsql-instances voice-agent-system:us-central1:voice-agents-db \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="DATABASE_URL=postgresql+pg8000://voice_agent_user:SECURE_USER_PASSWORD@/voice_agents?unix_sock=/cloudsql/voice-agent-system:us-central1:voice-agents-db/.s.PGSQL.5432" \
  --set-env-vars="GCP_PROJECT_ID=voice-agent-system" \
  --set-env-vars="GCP_STORAGE_BUCKET=voice-agent-knowledge-base" \
  --set-env-vars="PINECONE_ENVIRONMENT=your-pinecone-environment" \
  --set-env-vars="PINECONE_INDEX=voice-agent-kb" \
  --set-env-vars="LIVEKIT_URL=wss://your-livekit-server.livekit.cloud"
```

If you used Secret Manager, add these flags to securely access the secrets:

```bash
  --set-secrets="OPENAI_API_KEY=openai-api-key:latest" \
  --set-secrets="PINECONE_API_KEY=pinecone-api-key:latest" \
  --set-secrets="JWT_SECRET=jwt-secret:latest" \
  --set-secrets="LIVEKIT_API_KEY=livekit-api-key:latest" \
  --set-secrets="LIVEKIT_API_SECRET=livekit-api-secret:latest"
```

## Step 8: Initialize the Database

Run the database initialization script:

```bash
gcloud run jobs create init-db \
  --image gcr.io/voice-agent-system/voice-agent-api \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --add-cloudsql-instances voice-agent-system:us-central1:voice-agents-db \
  --set-env-vars="DATABASE_URL=postgresql+pg8000://voice_agent_user:SECURE_USER_PASSWORD@/voice_agents?unix_sock=/cloudsql/voice-agent-system:us-central1:voice-agents-db/.s.PGSQL.5432" \
  --command python \
  --args "manage.py,init-db"
```

Then execute the job:

```bash
gcloud run jobs execute init-db
```

## Step 9: Set up a Custom Domain (Optional)

If you want to use a custom domain:

1. Map your domain to your Cloud Run service:

```bash
gcloud beta run domain-mappings create \
  --service voice-agent-api \
  --domain api.your-domain.com \
  --region us-central1
```

2. Follow the instructions to verify domain ownership and update DNS records.

## Security Considerations

- Always use environment variables or Secret Manager for sensitive credentials
- Configure appropriate IAM permissions for your service accounts
- Set up VPC Service Controls for additional security if needed
- Consider implementing API key authentication for your endpoints
- Enable audit logging for all services
- Set up appropriate firewall rules

## Scaling Considerations

- Cloud Run automatically scales based on traffic
- Consider setting min/max instances for consistent performance
- Set appropriate memory and CPU limits based on your workload
- For batch processing (document processing), consider using Cloud Run jobs

## Monitoring and Maintenance

- Set up Cloud Monitoring for observability
- Configure alerts for high CPU/memory usage
- Set up Error Reporting for application errors
- Use Cloud Logging for centralized logs
- Create regular database backups

## Cost Optimization

- Use Cloud Run's scale-to-zero feature for dev/test environments
- Set appropriate CPU/memory limits to avoid overprovisioning
- Consider using preemptible instances for batch processing
- Set up budget alerts to monitor costs
- Use Cloud Storage lifecycle policies for old files 