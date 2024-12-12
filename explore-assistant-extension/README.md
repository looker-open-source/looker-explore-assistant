# Explore Assistant Extension Frontend Deployment
This documentation outlines the steps required to deploy the Explore Assistant Extension with the desired backend for generating Explore URL's based on Natural Language. It is intended to be installed via the Looker marketplace.

## 1. Deployment

1. Clone this repo locally

2. Install a backend using terraform by [following the instructions](../explore-assistant-backend/README.md)

3. Save the backend details for use by the extension framework:
   
   * The BigQuery example dataset and table name
   * If you're using the BigQuery backend, the model id that allows communication with Gemini
   * If you're using the Cloud Function backend, the url of the endpoint

4. Create a new BigQuery connection in Looker that will allow us to get the examples from the database. 

5. Now log in to Looker and create a new project or use an existing project.

   This is found under **Develop** => **Manage LookML Projects** => **New LookML Project**.

   You'll want to select "Blank Project" as your "Starting Point". You'll now have a new project with no files.

6. In your copy of the extension project you have a `manifest.lkml` file.

   You can either drag & upload this file into your Looker project, or create a `manifest.lkml` with the same content. Change the `id`, `label`, or `url` as needed. 
   **IMPORTANT** please paste in the deployed Cloud Function URL into the `external_api_urls` list and uncomment that line if you are using the Cloud Function backend deployment. This will allowlist it in Looker for fetch requests.

   ```lookml
   application: explore_assistant {
    label: "Explore Assistant"
    # url: "https://localhost:8080/explore_assistant.js"
    file: "explore_assistant.js"
    entitlements: {
      core_api_methods: ["lookml_model_explore","create_sql_query","run_sql_query","run_query","create_query"]
      navigation: yes
      use_embeds: yes
      use_iframes: yes
      new_window: yes
      new_window_external_urls: ["https://developers.generativeai.google/*"]
      local_storage: yes
      external_api_urls: ["cloud function url"]
    }
   }
   ```

7. Create a `model` LookML file in your project. The name doesn't matter. The model and connection won't be used, and in the future this step may be eliminated.

   - Add a connection in this model. It can be any connection, it doesn't matter which.
   - [Configure the model you created](https://docs.looker.com/data-modeling/getting-started/create-projects#configuring_a_model) so that it has access to some connection.

8. Connect your new project to Git. You can do this multiple ways:

   - Create a new repository on GitHub or a similar service, and follow the instructions to [connect your project to Git](https://docs.looker.com/data-modeling/getting-started/setting-up-git-connection)
   - A simpler but less powerful approach is to set up git with the "Bare" repository option which does not require connecting to an external Git Service.

9. Commit your changes and deploy your them to production through the Project UI.

10. Reload the page and click the `Browse` dropdown menu. You should see your extension in the list.
   - The extension will load the JavaScript from the `file` provided in the `application` definition. 
   - Refreshing the extension page will bring in any new code changes from the extension template, although some changes will hot reload.
