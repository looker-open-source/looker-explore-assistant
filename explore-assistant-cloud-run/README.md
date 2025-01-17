# CLOUD RUN BACKEND
the main.py is now wrapped around a python container that will be deployed to cloud run.

## pre requisites
- make `.env` file from the `.env_example` file.
- venv and installing the requirements.txt

- for local dev you will need a service_account.json file with the following permissions
    - roles/aiplatform.user

- for cloud build deployment you will need 
    - gcloud CLI
    - these IAM roles
        - roles/cloudbuild.builds.editor
        - roles/run.admin
        - roles/iam.serviceAccountUser
        - roles/storage.objectViewer
        - roles/iam.serviceAccountTokenCreator
    - after deployment, assign the the `roles/aiplatform.user` role to the generated cloud run's service account.



## local dev
- creates a local docker container
- run `docker compose up`
- test : `set -a && source .env && python test.py`

## deployment
- deployment is handled by terraform which will pick up the image.
- we wil need to build the image & upload to registry : 
- run `bash cloudrun_build.sh` & wait till image is pushed
- set the appropriate vars in variables.tfvars for cloud run, i.e.

```
cloud_run_service_name     = "explore-assistant-endpoint-kendev"
image                      = "asia-southeast1-docker.pkg.dev/joon-sandbox/looker-explore-assistant/explore-assistant-api-ken:latest"
use_cloud_run_backend      = true
```