# Looker Explore Assistant

This is an extension or plugin for Looker that integrates LLM's hosted on Vertex AI into a natural language experience powered by Looker's modeling layer.

![explore assistant](https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExeTU2b2l1ajc5ZGk2Mnc3OGtqaXRyYW9jejUwa2NzdGhoMmV1cXI0NCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/TQvvei5kuc8uQgMqSw/giphy.gif)

## Description

The Explore Assistant allows a user to generate a Looker Explore Query via natural language outputted into a visualization. As opposed to writing the raw SQL itself, the LLM is optimized to translate a text input into a Looker explore query. This is important as the LLM does what it's great at, **generative content**, and Looker powers it with all the **underlying data context, metadata and nuances** that come with business data and analytics.

Additionally, the extension provides:

 - Question History (*this is stored in the browser with IndexDB*)
 - Categorized Prompts (*these can be customized by the use cases of your organization*)

Upcoming capabilities on the roadmap:

 - Historical questions (*broken down by user, ranked by popularity/frequency, and categorized by type*)
 - LLM suggested questions (*iterative suggestions for follow up queries*)
 - Refinement (*refining the visualization returned by the LLM through natural language*)

### Technologies Used
#### Frontend
- [React](https://reactjs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [Webpack](https://webpack.js.org/).
- [Styled components](https://www.styled-components.com/docs)

#### Looker
- [Looker Extension SDK](https://github.com/looker-open-source/sdk-codegen/tree/main/packages/extension-sdk-react)
- [Looker Embed SDK](https://cloud.google.com/looker/docs/embed-sdk)
- [Looker Components](https://cloud.google.com/looker/docs/components)

#### Backend API
- [Google Cloud Platform](https://cloud.google.com/)
- [Vertex AI](https://cloud.google.com/vertex-ai)
- [Cloud Functions](https://cloud.google.com/functions)
- ---

## Setup
### 1. Generative AI Endpoint

This section describes how to set up the Gen AI endpoint for the Explore Assistant. TLDR; We use a 2nd Gen Cloud Function to call the foundational model and return the results to the frontend.

#### Getting Started for Development

![simple-architecture](./static/simple-architecture.png)

1. Clone or download a copy of this repository to your development machine.

   ```bash
   # cd ~/ Optional. your user directory is usually a good place to git clone to.
   git clone git@github.com:LukaFontanilla/looker-explore-assistant.git
   ```

2. Navigate (`cd`) to the template directory on your system

   ```bash
   cd looker-explore-assistant/cloud-function/terraform
   ```

3. Replace defaults in the `variables.tf` file for project and region.

4. Deploy resources.

   ```terraform
   terraform init

   terraform plan

   terraform apply
   ```

5. Save Deployed Cloud Function URL Endpoints

#### Optionally, deploy regional endpoints and load balance traffic from Looker

![global-architecture](./static/global-architecture.png)

Please see this resource for more information on how to deploy regional endpoints and load balance traffic from Looker: https://cloud.google.com/load-balancing/docs/https/setting-up-https-serverless



### 2. Looker Extension Framework Setup


#### Getting Started for Development

1. Navigate (`cd`) to the template directory on your system

   ```bash
   cd looker-explore-assistant
   ```

1. Install the dependencies with [NPM](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm).

   ```bash
   npm install
   ```

   > You may need to update your Node version or use a [Node version manager](https://github.com/nvm-sh/nvm) to change your Node version.

1. Ensure all the appropriate environment variables are set.

   ```
   VERTEX_AI_ENDPOINT=
   LOOKER_MODEL=
   LOOKER_EXPLORE=
   ```

1. Start the development server

   ```bash
   npm start
   ```

   Great! Your extension is now running and serving the JavaScript at https://localhost:8080/bundle.js.

1. Now log in to Looker and create a new project.

   This is found under **Develop** => **Manage LookML Projects** => **New LookML Project**.

   You'll want to select "Blank Project" as your "Starting Point". You'll now have a new project with no files.

   1. In your copy of the extension project you have a `manifest.lkml` file.

   You can either drag & upload this file into your Looker project, or create a `manifest.lkml` with the same content. Change the `id`, `label`, or `url` as needed.

   ```lookml
   application: explore_assistant {
    label: "Explore Assistant"
    url: "https://localhost:8080/bundle.js"
    # file: "bundle.js"
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

1. Create a `model` LookML file in your project. The name doesn't matter. The model and connection won't be used, and in the future this step may be eliminated.

   - Add a connection in this model. It can be any connection, it doesn't matter which.
   - [Configure the model you created](https://docs.looker.com/data-modeling/getting-started/create-projects#configuring_a_model) so that it has access to some connection.

1. Connect your new project to Git. You can do this multiple ways:

   - Create a new repository on GitHub or a similar service, and follow the instructions to [connect your project to Git](https://docs.looker.com/data-modeling/getting-started/setting-up-git-connection)
   - A simpler but less powerful approach is to set up git with the "Bare" repository option which does not require connecting to an external Git Service.

1. Commit your changes and deploy your them to production through the Project UI.

1. Reload the page and click the `Browse` dropdown menu. You should see your extension in the list.
   - The extension will load the JavaScript from the `url` provided in the `application` definition. By default, this is https://localhost:8080/bundle.js. If you change the port your server runs on in the package.json, you will need to also update it in the manifest.lkml.
   - Refreshing the extension page will bring in any new code changes from the extension template, although some changes will hot reload.

#### Deployment

The process above requires your local development server to be running to load the extension code. To allow other people to use the extension, a production build of the extension needs to be run. As the kitchensink uses code splitting to reduce the size of the initially loaded bundle, multiple JavaScript files are generated.

1. In your extension project directory on your development machine, build the extension by running the command `npm build`.
2. Drag and drop ALL of the generated JavaScript files contained in the `dist` directory into the Looker project interface.
3. Modify your `manifest.lkml` to use `file` instead of `url` and point it at the `bundle.js` file.

Note that the additional JavaScript files generated during the production build process do not have to be mentioned in the manifest. These files will be loaded dynamically by the extension as and when they are needed. Note that to utilize code splitting, the Looker server must be at version 7.21 or above.

---

### Recommendations for fine tuning the model

This app uses a one shot prompt technique for fine tuning a model, meaning that all the metadata for the model is contained in the prompt. This is a good technique for a small dataset, but for a larger dataset, you may want to use a more traditional fine tuning approach. In this repo we check the prompt token limit and if it is greater than 3000, we use the `text-bison32k` model otherwise `text-bison` is used. You can change this limit in the `cloud-function/src/main.py` file. This is a simple implementation, but you can also use a more sophisticated approach that involves generating embeddings for explore metadata and leveraging a vector database for indexing.

To best optimize the one shot prompt accuracy, please update the example input output string in the Cloud Function code to be a representative sample of the data you are trying to model. For example, if you are trying to model a dataset of sales data, you may want to use a prompt like "What is the total sales for each region?" and follow that with the output using Looker's expanded url syntax. 20-100 examples is a good starting point for a one shot prompt and can drastically improve the accuracy of the model.

We recommend using Looker System Activity, filtering queries for the model and explore you plan on using the assistant with, and then using the top 20-100 queries as your example input output string with their expanded url syntax.
