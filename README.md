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

## Setup

Getting started involves:

- Frontend Setup - setup Looker Extension Framework Applications by following [these instructions](./explore-assistant-extension/README.md).
- Backend Setup - setup the GCP backend for communicating with the Vertex API [using these instructions.](./explore-assistant-backend/README.md)
- Example generation - generate a list of examples and upload them to BigQuery [using these instructions.](./explore-assistant-examples/README.md)

The local cloud function backend and example generation require some python packages. It is recommended to create a python virtual environment and install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate 
pip3 install -r ./explore-assistant-examples/requirements.txt
pip3 install -r ./explore-assistant-cloud-function/requirements.txt 
```

## Recommendations for fine tuning the model

This app uses a one shot prompt technique for fine tuning a model, meaning that all the metadata for the model is contained in the prompt. It's a good technique for a small dataset, but for a larger dataset, you may want to use a more traditional fine tuning approach. This is a simple implementation, but you can also use a more sophisticated approach that involves generating embeddings for explore metadata and leveraging a vector database for indexing.

Any `jsonl` file you see in this repo is used to train the llm with representative Looker Explore Query examples. These examples are used to help the understand how to create different variations of Looker Explore Queries to account for requests that might result in pivots, relative date filters, includes string syntax, etc. For convenience and customization we recommend using Looker System Activity, filtering queries for the model and explore you plan on using the assistant with, and then using the top 20-30 queries as your example input output string with their expanded url syntax. Please see the [Explore Assistant Training Notebook](./explore-assistant-training/) for creating query examples for new datasets via an automated process.
