# Explore Assistant Data Generation and Loader for BigQuery

The script facilitates the generation and loading of example and sample data into the BigQuery `explore_assistant` dataset. The process supports multiple models and explores, relying on a set of looks for each explore in one or more folders in your Looker instance. The output is generated in a tree structure:

- examples
  - model
    - explore

Each look title from the defined folder creates an "input" from a pair of "input"/"output". The following query parameters from the Looker URL are included (only if they are non-empty):

- fields
- filters (f[])
- sorts
- limits
- dynamic_fields
- vis
  - type
  - hidden_fields
  - hidden_points_if_no
  - show_comparison
  - comparison_type
  - series_types

The following parameter is excluded:

- query_timezone
- filter_config
- fill_fields

Support for loading samples into BigQuery has been added to the `explore_assistant_samples` dataset.

## Table of Contents

- [How to Start](#how-to-start)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
  - [looker_project.ini](#looker-project-ini)
  - [looker.ini](#looker-ini)
    - [How to Create Looker API Credentials](#how-to-create-looker-api-credentials)
- [data Folder Structure](#data-folder-structure)
  - [Folder Descriptions](#folder-descriptions)
  - [JSON Files](#json-files)
- [Usage](#usage)
  - [looker_looks.py](#looker-lookspy)
  - [generate_examples.py](#generate-examplespy)
  - [load_examples.py](#load-examplespy)
  - [load_samples.py](#load-samplespy)

## How to start

1. **Decide on Explores**: Choose the explores you want to include in the Explore Assistant.
2. **Organize Looks**: Build or move Looks that will serve for generating input/output examples into dedicated folder(s). There can be more than one folder per `explore_id` (model:explore name). The title of the explore serves as the input query/question.
3. **Create ini files** [looker_project.ini](#looker-project-ini) and [looker.ini](#looker-ini).
4. **Complete the Configuration**: Fill in folder structure described in [data Folder Structure](#data-folder-structure)
5. **Start generating**: Go to [Usage](#usage)

## Prerequisites

Before running these scripts, ensure your environment is set up with the following:

1. **Python 3.6 or higher**: Make sure Python is installed on your system.
2. **Google Cloud SDK**: Install and configure the Google Cloud SDK (gcloud).
3. **Google Cloud Authentication**: Set up authentication by either:
   - Using a personal account: `gcloud auth application-default login`
   - Downloading a service account key and setting the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to that key file.

## Setup

Unless y've set up python virtual env on the higher level in the repo, it's time to satisfy dependencies.
To run these scripts, install the required dependencies. It's recommended to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
```

### looker_project.ini

1. Create a file named `looker_project.ini` with the following variables:

```
[looker_project]
project_id=<Your project_id>
location=<Explore assistant dataset location, for example us-central1>
dataset_id=<Explore assistant dataset, for example explore_assistant>
examples_table_id=<Explore assistant dataset examples table name, explore_assistant_examples>
samples_table_id=<Explore assistant dataset samples table name, explore_assistant_samples>
folder_ids=<A dictionary of `explore_id` keys and looker folder_ids arrays as their values, e.g. {'model:explore': ['folder_id1', 'folder_id2', 'folder_id3'], 'abd:xxx': ['10', '12', '67']}>
samples_folder=<Samples input folder, default: data/samples>
additional_prompts_folder=<Additional prompts input folder: data/additional_prompts>
examples_folder=<Examples output folder, default: data/examples>
looks_folder=<Looks definitions output folder, default: data/looks>
```

Folder IDs can be found in the Looker URL by opening the specific folder in the Looker UI.

### looker.ini

Steps for configuring the Looker Python SDK:

1.  Create a file named `looker.ini`
2.  Using the example below, fill in the variables as they are for your environment. **_You will need Looker API credentials for a user that has at least `explore` level permissions._** How to is described in [How to Create Looker API Credentials](#how-to-create-looker-api-credentials).

`looker_example.ini`

```
[Looker]
base_url=<Your company looker url, for example https://company.cloud.looker.com>
client_id=<user client id>
client_secret=<user client secret>
verify_ssl=true
```

#### How to Create Looker API Credentials

To create Looker API credentials for a user, follow these steps:

##### Step 1: Log in to Looker

1. Open your web browser and navigate to your Looker instance.
2. Log in with your Looker admin credentials.

##### Step 2: Navigate to the User Administration Page

1. Click on the **Main Menu** icon (usually represented by a hamburber icon) in the top-left corner of the Looker interface.
2. From the dropdown menu, select **Admin**.
3. In the Admin panel, click on **Users** under the **Users** section.

##### Step 3: Select or Create a User

1. If the user already exists, find the user in the list and click on their name to open their user details page.
2. If the user does not exist, create a new user:
   - Click the **+ Add User** button.
   - Fill in the user's details (First Name, Last Name, Email, etc.).
   - Click **Save** to create the user.

##### Step 4: Generate API Credentials

1. On the user's details page, scroll down to the **API Keys** section.
2. Click the **Edit Keys** button.
3. Click **New API Keys\*** buttton. This will generate a new API client ID and client secret for the user.

## "data" Folder Structure

The `data` directory has the following folder structure:

```
data/
├── additional_prompts/
│   └── abc/
│       └── xxx.json
├── examples/
├── looks/
├── refinement_examples/
└── samples/
    └── abc/
        └── xxx.json
        └── yyy.json
```

You can customize the folder names, but they must remain consistent with the looker_project.ini file.

### Folder Descriptions

- **additional_prompts/**: Contents of this folder is optional (but folder has to exits). It's used to provide additional examples (not only from looks in looker folders) for specific models (abc - model name) and explores (xxx - explore name). Users can create their own subdirectories and JSON files as needed, reflecting folders_id property of looker_project.ini. These additional prompts will be appended to the final example files generated in the `examples` folder:

  - **abc/**: An example model folder. Replace `abc` with your own model name.
    - **xxx.json**: An example explore file. Replace `xxx.json` with your own explore file.

- **examples/**: Output folder for the final example files generated by the process. model / explore tree structer will be automatically created.

- **looks/**: Output folder for looks definition, stored as jsons. model / explore tree structer will be automatically created.

- **refinement_examples/**: The folder contains examples specifically for refinement purposes. Generation of refinement_examples is not implemented yet.

- **samples/**: Contents of this folder is optional (but folder has to exits). It contains sample files dedicated to specific models and explores. Folder structure reflects **additional_prompts/**.

### JSON Files

#### Additional Prompts Files

Below is an example of the content in an additional sample file:

```json
[
  {
    "input": "Customer who are currently active and made an order in the last day 90 days",
    "output": "fields=users.email,order_items.created_date&f[user_order_facts.currently_active_customer]=Yes&f[order_items.created_date]=last 90 days&sorts=order_items.created_date desc"
  }
]
```

#### Sample Files

Below is an example of the content in the `samples/model_abc/explore_xyz.json` file:

```json
[
  {
    "category": "Cohorting",
    "prompt": "Count of Users by first purchase date",
    "color": "blue"
  },
  {
    "category": "Audience Building",
    "prompt": "Users who have purchased more than 100 dollars worth of Calvin Klein products and have purchased in the last 30 days",
    "color": "green"
  }
]
```

## Usage

All the scripts below read the configuration from `looker_project.ini`, so there is no need to set up additional parameters to execute them.

**🟡 Note**
As of now, refinement examples are not included in looks_training. While scripts can be easily adjusted if necessary, explore_assistant_refinement_examples must not be left empty. Please load dummy refinement examples for your key explore_id using [using these instructions.](../../explore-assistant-examples/README.md) This action is required only during the initial setup of the explore assistant solution, not for ongoing training.

### looker_looks.py

**🔵 Optional**

This script exports Looker looks definitions as JSON files. Looks are taken from `folder_ids` defined in `looker_project.ini`. The output is saved in the `looks_folder` path, with model folders and explore subfolders within the model folders. This helps in investigating individual look structures for debugging and examining available properties.

#### How It Works

- Fetches looks from specified folder IDs.
- Converts look objects to dictionaries.
- Saves each look's details as a JSON file in a structured folder hierarchy.

### generate_examples.py

**🔴 Necessary**

This script generates prompt examples by combining Looker looks and additional prompts, saving them in a structured folder hierarchy: model subfolders and explores as JSON files, with an array of input/output examples. The files serve as the contents to populate the `explore_assistant_examples` table.

#### How It Works

- Reads configuration from `looker_project.ini`.
- Fetches looks from specified folder IDs.
- Processes each look and additional prompts to generate prompt examples.
- Saves combined prompt examples as JSON files in the `examples_folder`.

### load_examples.py

**🔴 Necessary**

This script loads example prompts from JSON files in a structured folder hierarchy (model subfolders and explore files) and inserts them into the `explore_assistant_examples` table in BigQuery. The script is designed to populate the table with arrays of input/output examples for each `explore_id` (model:explore).

#### How It Works

- Reads configuration from `looker_project.ini`.
- Iterates through the model folders in the `examples_folder`.
- Loads data from JSON files in each model folder.
- Inserts the loaded data into the specified BigQuery table.

### load_samples.py

**🔵 Optional**

This script loads samples displayed in the UI under the prompt text box. It takes contents from JSON files in a structured folder hierarchy (model subfolders and explore files) and inserts them into the `explore_assistant_samples` table in BigQuery. The table's DDL is available in the `ddl` folder.

#### Sample JSON Format

The JSON files should contain an array of objects with the following keys:

- **category**: Describes the category of analysis/data question (e.g., "Lifecycle State").
- **prompt**: The text of the prompt that should fill the prompt text box when clicked (e.g., "Customers by lifecycle state in the last two years").
- **color**: Specifies the color associated with the prompt (e.g., "blue").

#### How It Works

- Reads configuration from `looker_project.ini`.
- Iterates through the model folders in the `samples_folder`.
- Loads data from JSON files in each model folder.
- Inserts the loaded data into the specified BigQuery table.
