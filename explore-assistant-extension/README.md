# Explore Assistant Extension Frontend Deployment
This documentation outlines the steps required to deploy the Explore Assistant Extension with the desired backend for generating Explore URL's based on Natural Language. It assumes a Looker Instance is available with a suitable LookML Model and Explore configured.

## 1. LLM Integration

This section describes how to set up the LLM Integration for the Explore Assistant.

### Getting Started for Development

1. Install a backend using terraform by [following the instructions](../explore-assistant-backend/README.md)

2. Save the backend details for use by the extension framework:
   
   * The BigQuery example dataset and table name
   * If you're using the BigQuery backend, the model id that allows communication with Gemini
   * If you're using the Cloud Function backend, the url of the endpoint

### Optional: Setup Log Sink to BQ for LLM Cost Estimation and Request Logging (used for Cloud Function Backend)

Please see [Google Cloud's docs](https://cloud.google.com/logging/docs/export/configure_export_v2#creating_sink) on setting up a log sink to BQ, using the below filter for Explore Assistant Logs:

```
(resource.type = "cloud_function"
resource.labels.function_name = "Insert service name"
resource.labels.region = "<Insert location>")
 OR 
(resource.type = "cloud_run_revision"
resource.labels.service_name = "<Insert service name>"
resource.labels.location = "<Insert location>")
 severity>=DEFAULT
jsonPayload.component="explore-assistant-metadata"
```

## 2. Looker Extension Framework Setup
**Important** If you are not familiar with the Looker Extension Framework, please review [this documentation](https://developers.looker.com/extensions/overview/) first before moving forward.


### Getting Started for Development

1. From the Explore Assistant root directory (`cd`) to the Explore Assistant Extension folder. *If deploying from Cloudshell, you should already be in this folder*.

   ```bash
   cd explore-assistant-extension
   ```

2. Install the dependencies with [NPM](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm). *Please follow the hyperlinked directions for installing node and npm on your machine. Skip this step if deploying from Cloud Shell method above.* Additionally if you need to work across multiple Node versions, `nvm` can be used switch between and install different node versions. When installing node, you need to install a version less than 17.

   ```bash
   npm install
   ```

   > You may need to update your Node version or use a [Node version manager](https://github.com/nvm-sh/nvm) to change your Node version. You can print your version number in terminal with the following command:
   
   ```bash
   $ node -v
   ```

3. Create a new BigQuery connection in Looker that will allow us to get the examples from the database. You will use that in the VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME below.

4. Ensure all the appropriate environment variables are set in the `.env_example` file. Also rename the `.env_example` file to `.env`.

   Regardless of the backend, you're going to need:

   ```
   VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME=<This is the connection name in Looker with the BQ project that has access to the remote connection and model>
   BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME=<The BQ connection name in Looker that has query access to example prompts. This may be the same as the Vertex Connection Name if using just one gcp project>
   BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME=<This is the dataset and project that contain the Example prompt data, assuming that differs from the Looker connection>
   ```

   Optionally, include and specify the below variable if your BQ project housing the example prompts for Explore Assistant (see [Examples folder](../explore-assistant-examples/README.md)) is different than the project set by default in your BQ connection to Looker. If unspecified, it defaults to the current BigQuery project in your Looker connection & `explore_assistant` as the dataset name.

   ```
   BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME=<This is the dataset and/or project that contain the Example prompt data, assuming that differs from the dataset and/or project specified as default in the Looker connection above>
   ```

   If you're using the Cloud Function backend, replace the defaults:

   ```
   VERTEX_AI_ENDPOINT=<This is your Deployed Cloud Function Endpoint>
   VERTEX_CF_AUTH_TOKEN=<This is the token used to communicate with the cloud function>
   ```

   If you're using the BigQuery Backend replace the default:

   ```
   VERTEX_BIGQUERY_MODEL_ID=<This is the model id that you want to use for prediction>
   ```

4. If you're utilizing Looker Core (Looker instance hosted in Google Cloud), adjust the `embed_domain` variable within the `useEffect()` function in ExploreEmbed.tsx to reflect the `hostUrl` instead of `window.origin`.

   ```typescript
   //embed.domain: window.origin // Looker Original
   embed_domain: hostUrl, // Looker Core
   ```

5. Start the development server
   **IMPORTANT** If you are running the extension from a VM or another remote machine, you will need to Port Forward to the machine where you are accessing the Looker Instance from (ie. If you are accessing Looker from your local machine, run the following command there.). Here's a boilerplate example for port forwarding the remote port 8080 to the local port 8080:
   `ssh username@host -L 8080:localhost:8080`.

   ```bash
   npm run start
   ```

   Great! Your extension is now running and serving the JavaScript at https://localhost:8080/bundle.js.

6. Now log in to Looker and create a new project or use an existing project.

   This is found under **Develop** => **Manage LookML Projects** => **New LookML Project**.

   You'll want to select "Blank Project" as your "Starting Point". You'll now have a new project with no files.

   1. In your copy of the extension project you have a `manifest.lkml` file.

   You can either drag & upload this file into your Looker project, or create a `manifest.lkml` with the same content. Change the `id`, `label`, or `url` as needed. 
   **IMPORTANT** please paste in the deployed Cloud Function URL into the `external_api_urls` list and uncomment that line if you are using the Cloud Function backend deployment. This will allowlist it in Looker for fetch requests.

   ```lookml
   application: explore_assistant {
    label: "Explore Assistant"
    url: "https://localhost:8080/bundle.js"
    # file: "bundle.js"
    entitlements: {
      core_api_methods: ["lookml_model_explore","create_sql_query","run_sql_query","run_query","create_query"]
      navigation: yes
      use_embeds: yes
      use_iframes: yes
      new_window: yes
      new_window_external_urls: ["https://developers.generativeai.google/*"]
      local_storage: yes
      # external_api_urls: ["cloud function url"]
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
   - The extension will load the JavaScript from the `url` provided in the `application` definition. By default, this is https://localhost:8080/bundle.js. If you change the port your server runs on in the package.json, you will need to also update it in the manifest.lkml.
   - Refreshing the extension page will bring in any new code changes from the extension template, although some changes will hot reload.

### Deployment

The process above requires your local development server to be running to load the extension code. To allow other people to use the extension, a production build of the extension needs to be run. As the kitchensink uses code splitting to reduce the size of the initially loaded bundle, multiple JavaScript files are generated.

1. In your extension project directory on your development machine, build the extension by running the command `npm run build`.
1. Drag and drop ALL of the generated JavaScript file (ie. `bundle.js`) contained in the `dist` directory into the Looker project interface.
1. Modify your `manifest.lkml` to use `file` instead of `url` and point it at the `bundle.js` file.

Note that the additional JavaScript files generated during the production build process do not have to be mentioned in the manifest. These files will be loaded dynamically by the extension as and when they are needed. Note that to utilize code splitting, the Looker server must be at version 7.21 or above.

---
