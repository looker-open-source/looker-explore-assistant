# PORTING THE CLOUD FUNCTION AS CLOUD RUN IMG
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
- run `bash deploy_cloud_run.sh`
- wait till output returns the public url 
- test : 
    - update the CLOUDRUN_ENDPOINT with the public url
    - `set -a && source .env && python test.py`