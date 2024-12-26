# Looker Explore Assistant Backend Service

This is an automatic installer of the GCP Cloud Run backend service.
This is intended to be installed in an empty google project. 
To begin, please execute:
```
cd explore-assistant-backend/terraform && ./init.sh
```

# Caution
If resources will be deleted or destroyed by Terraform, please abort the process to avoid destroying existing resources. It is recommended to start with an empty project instead.

# Looker
After this deployment, it will be necessary to grant a service account access to the datasets created, then use that service account in a Looker Connection. The looker connection can be specified during marketplace deployment, or by setting a override_constant in the remote_dependency like this:

## manifest.lkml snippet 
```
remote_dependency: explore_assistant_marketplace {
  url: "https://github.com/bytecodeio/explore-assistant-lookml"
  
  override_constant: LOOKER_BIGQUERY_CONNECTION_NAME {
   value: "your_looker_connection_name"
  }
  
  # BQML_REMOTE_CONNECTION_MODEL_ID is the ID of a remote connection to Vertex in BigQuery
  # Only necessary for the BigQuery Backend install type.
  # Can be left as an empty string for Cloud Function backend installs.
  override_constant: BQML_REMOTE_CONNECTION_MODEL_ID {
   value: ""
  }
}
