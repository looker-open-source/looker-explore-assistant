# Looker Explore Assistant

This app demonstrates how you could use a foundational language model on GCP to turn a natural language query into an embedded Looker Explore query output in a visualization.

![explore assistant](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTU2b2l1ajc5ZGk2Mnc3OGtqaXRyYW9jejUwa2NzdGhoMmV1cXI0NCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/TQvvei5kuc8uQgMqSw/giphy.gif)

### Recommendations for fine tuning the model

This app uses a one shot prompt technique for fine tuning a model, meaning that all the metadata for the model is contained in the prompt. This is a good technique for a small dataset, but for a larger dataset, you may want to use a more traditional fine tuning approach.

To best optimize the one shot prompt accuracy, please update the example input output string in the Cloud Function code to be a representative sample of the data you are trying to model. For example, if you are trying to model a dataset of sales data, you may want to use a prompt like "What is the total sales for each region?" and follow that with the output using Looker's expanded url syntax. 20-100 examples is a good starting point for a one shot prompt and can drastically improve the accuracy of the model.

We recommend using Looker System Activity, filtering queries for the model and explore you plan on using the assistant with, and then using the top 20-100 queries as your example input output string with their expanded url syntax.

---
#### Frontend
- [React](https://reactjs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [React Extension SDK](https://github.com/looker-open-source/sdk-codegen/tree/main/packages/extension-sdk-react)
- [Webpack](https://webpack.js.org/).
- [Styled components](https://www.styled-components.com/docs)

#### Looker
- [Looker Extension SDK]()
- [Looker Embed SDK]()
- [Looker Components]()

#### Backend API
- [Google Cloud Platform](https://cloud.google.com/)
- [Vertex AI](https://cloud.google.com/vertex-ai)
- [Cloud Functions](https://cloud.google.com/functions)
---
## Explore Assistant: Gen AI Endpoint

This section describes how to set up the Gen AI endpoint for the Explore Assistant. TLDR; We use a 2nd Gen Cloud Function to call the foundational model and return the results to the frontend.

### Getting Started for Development

1. Clone or download a copy of this repository to your development machine.

   ```bash
   # cd ~/ Optional. your user directory is usually a good place to git clone to.
   git clone git@github.com:looker-open-source/extension-examples.git
   ```

2. Navigate (`cd`) to the template directory on your system

   ```bash
   cd cloud-function/terraform
   ```

3. Replace defaults in the `variables.tf` file for project and region.

4. Deploy resources.

   ```terraform
   terraform init

   terraform plan

   terraform apply
   ```

5. Save Deployed Cloud Function URL Endpoints

### Optionally, deploy regional endpoints and load balance traffic from Looker

Please see this resource for more information on how to deploy regional endpoints and load balance traffic from Looker: https://cloud.google.com/load-balancing/docs/https/setting-up-https-serverless



## Explore Assistant: Looker Extension Framework


### Getting Started for Development

1. Clone or download a copy of this repository to your development machine.

   ```bash
   # cd ~/ Optional. your user directory is usually a good place to git clone to.
   git clone git@github.com:looker-open-source/extension-examples.git
   ```

2. Navigate (`cd`) to the template directory on your system

   ```bash
   cd dashboard_demo
   ```

3. Install the dependencies with [NPM](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm).

   ```bash
   npm install
   ```

   > You may need to update your Node version or use a [Node version manager](https://github.com/nvm-sh/nvm) to change your Node version.

4. Start the development server

   ```bash
   npm start
   ```

   Great! Your extension is now running and serving the JavaScript at https://localhost:8080/bundle.js.

5. Now log in to Looker and create a new project.

   This is found under **Develop** => **Manage LookML Projects** => **New LookML Project**.

   You'll want to select "Blank Project" as your "Starting Point". You'll now have a new project with no files.

   1. In your copy of the extension project you have a `manifest.lkml` file.

   You can either drag & upload this file into your Looker project, or create a `manifest.lkml` with the same content. Change the `id`, `label`, or `url` as needed.

   ```lookml
   application: explore_assistant {
    label: "Explore Assistant"
    url: "https://localhost:8080/bundle.js"
    file: "bundle.js"
    entitlements: {
      core_api_methods: ["lookml_model_explore"]
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

6. Create a `model` LookML file in your project. The name doesn't matter. The model and connection won't be used, and in the future this step may be eliminated.

   - Add a connection in this model. It can be any connection, it doesn't matter which.
   - [Configure the model you created](https://docs.looker.com/data-modeling/getting-started/create-projects#configuring_a_model) so that it has access to some connection.

7. Connect your new project to Git. You can do this multiple ways:

   - Create a new repository on GitHub or a similar service, and follow the instructions to [connect your project to Git](https://docs.looker.com/data-modeling/getting-started/setting-up-git-connection)
   - A simpler but less powerful approach is to set up git with the "Bare" repository option which does not require connecting to an external Git Service.

8. Commit your changes and deploy your them to production through the Project UI.

9. Reload the page and click the `Browse` dropdown menu. You should see your extension in the list.
   - The extension will load the JavaScript from the `url` provided in the `application` definition. By default, this is https://localhost:8080/bundle.js. If you change the port your server runs on in the package.json, you will need to also update it in the manifest.lkml.

- Refreshing the extension page will bring in any new code changes from the extension template, although some changes will hot reload.

10. Ensure All the Appropriate Environment Variables are set.

```
VERTEX_AI_ENDPOINT=
LOOKER_EXPLORE_ID=
LOOKER_MODEL=
LOOKER_EXPLORE=
```

### Deployment

The process above requires your local development server to be running to load the extension code. To allow other people to use the extension, a production build of the extension needs to be run. As the kitchensink uses code splitting to reduce the size of the initially loaded bundle, multiple JavaScript files are generated.

1. In your extension project directory on your development machine, build the extension by running the command `yarn build`.
2. Drag and drop ALL of the generated JavaScript files contained in the `dist` directory into the Looker project interface.
3. Modify your `manifest.lkml` to use `file` instead of `url` and point it at the `bundle.js` file.

Note that the additional JavaScript files generated during the production build process do not have to be mentioned in the manifest. These files will be loaded dynamically by the extension as and when they are needed. Note that to utilize code splitting, the Looker server must be at version 7.21 or above.