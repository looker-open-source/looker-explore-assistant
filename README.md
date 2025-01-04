# Looker Explore Assistant

This is an extension or API plugin for Looker that integrates LLM's hosted on Vertex AI into a natural language experience powered by Looker's modeling layer.

![explore assistant](./static/explore-assistant.gif)

## Description

The Explore Assistant allows a user to generate a Looker Explore Query via natural language outputted into a visualization. As opposed to writing the raw SQL itself, the LLM is optimized to translate a text input into a Looker explore query. This is important as the LLM does what it's great at, **generative content**, and Looker powers it with all the **underlying data context, metadata and nuances** that come with business data and analytics.

Additionally, the extension provides:

 - Question History (*this is stored in the browser's localstorage*)
 - Categorized Prompts (*these can be customized by the use cases of your organization*)
 - Cached Explore URL's when clicking from History
 - Structured Logging with Input & Output Token Counts (*enables a workflow of log sink to BQ for cost estimation & tracking*)
 - Flexible Deployment Options
 - Multi-turn
 - Insight Summarization
 - Dynamic Explore Selection

### Technologies Used
#### Frontend
- [React](https://reactjs.org/)
- [TypeScript](https://www.typescriptlang.org/)
- [Webpack](https://webpack.js.org/).
- [Tailwind CSS](https://tailwindcss.com/)

#### Looker
- [Looker Extension SDK](https://github.com/looker-open-source/sdk-codegen/tree/main/packages/extension-sdk-react)
- [Looker Embed SDK](https://cloud.google.com/looker/docs/embed-sdk)
- [Looker Components](https://cloud.google.com/looker/docs/components)

#### Backend API
- [Google Cloud Platform](https://cloud.google.com/)
- [Vertex AI](https://cloud.google.com/vertex-ai)
- [Cloud Functions](https://cloud.google.com/functions)

## Get Started

Getting started involves (*in this order*):
1. Clone or download a copy of this repository to your development machine.
   If you have a git ssh_config:
   ```bash
   # cd ~/ Optional. your user directory is usually a good place to git clone to.
   git clone git@github.com:looker-open-source/looker-explore-assistant.git
   ```

   If not:
   ```bash
   # cd ~/ Optional. your user directory is usually a good place to git clone to.
   git clone https://github.com/looker-open-source/looker-explore-assistant.git
   ```
   Alternatively, open up this repository in: &nbsp;
   [![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/editor?cloudshell_git_repo=https://github.com/looker-open-source/looker-explore-assistant.git&cloudshell_workspace=explore-assistant-extension)
2. Make sure [pip](https://pip.pypa.io/en/stable/cli/pip_install/) is installed on your computer to run the `pip install -r requirements.txt` command line in the setup section.     
3. Install [`google-cloud-sdk`](https://cloud.google.com/sdk/docs/install) in the looker-explore-assistant directory to install Google Cloud SDK before the backend setup. 
        >To install google-cloud-sdk, you can use this command `brew install —cask google-cloud-sdk`. Ensure you have [Homebrew](https://brew.sh/) installed first
4. Create a GCP Project (you’ll need the ID later). It does not have to be the same project as the prompt tables but it is recommended for simplicity
5. Create a Looker connection for that BigQuery project
6. Create an empty Looker project
       - Add the connection name to the model file
       - Configure git
       - That’s all you need to do for now. This is where the extension framework will be deployed. The connection should be the same as the one that holds the prompts

The local cloud function backend and example generation require some python packages. It is recommended to create a python virtual environment and install the dependencies:

```bash
# Use python3 on Mac OS
python -m venv .venv
source .venv/bin/activate 
pip install -r ./explore-assistant-examples/requirements.txt
pip install -r ./explore-assistant-cloud-function/requirements.txt 
```
> If you hit a blocker with directory permissions, use `chmod +x <FILE NAME>` to allow write permissions.

## Setup

1. Backend Setup - setup the GCP backend for communicating with the Vertex API [using these instructions.](./explore-assistant-backend/README.md)
2. Example generation - generate a list of examples and upload them to BigQuery [using these instructions.](./explore-assistant-examples/README.md)
3. Frontend Setup - setup Looker Extension Framework Applications by following [these instructions](./explore-assistant-extension/README.md).

## Recommendations for fine tuning the model

This app uses a one shot prompt technique for fine tuning a model, meaning that all the metadata for the model is contained in the prompt. It's a good technique for a small dataset, but for a larger dataset, you may want to use a more traditional fine tuning approach. This is a simple implementation, but you can also use a more sophisticated approach that involves generating embeddings for explore metadata and leveraging a vector database for indexing.

Any `json` file you see in this repo is used to train the llm with representative Looker Explore Query examples. These examples are used to help the understand how to create different variations of Looker Explore Queries to account for requests that might result in pivots, relative date filters, includes string syntax, etc. For convenience and customization we recommend using Looker System Activity, filtering queries for the model and explore you plan on using the assistant with, and then using the top 20-30 queries as your example input output string with their expanded url syntax. Please see the [Explore Assistant Training Notebook](./explore-assistant-training/) for creating query examples for new datasets via an automated process.
