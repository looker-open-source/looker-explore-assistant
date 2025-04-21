# Explore Assistant Extension Frontend Deployment

This documentation outlines the steps required to deploy the Explore Assistant Extension. The backend no longer requires Cloud Functions or Terraform. Instead, the setup involves creating BigQuery tables and configuring OAuth in GCP.

## Prerequisites

- A GCP project with BigQuery tables created for examples, samples, and refinements.
- OAuth consent and app configured in GCP.
- A Looker connection to BigQuery.

## Setup Steps

1. **Create BigQuery Tables**
   Follow the instructions in the [Backend README](../explore-assistant-backend/README.md) to create the necessary BigQuery tables.

2. **Configure OAuth in GCP**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/).
   - Navigate to **APIs & Services** > **OAuth consent screen**.
   - Configure the consent screen with the required details.
   - Create an OAuth 2.0 Client ID under **Credentials**.
   - Note the Client ID and Secret for use in the Looker Explore Assistant.

3. **Set Up Looker Project**
   - Log in to Looker and create a new project or use an existing project.
   - Upload the `manifest.lkml` file from this directory into your Looker project.
   - Update the `manifest.lkml` file to include your BigQuery connection name and OAuth details.

4. **Deploy the Extension**
   - Commit your changes and deploy them to production through the Looker Project UI.
   - Reload the page and click the `Browse` dropdown menu. You should see your extension in the list.

## Notes

- The extension fetches examples, samples, and refinements directly from BigQuery.
- Ensure the Looker connection has access to the `explore_assistant` dataset.
