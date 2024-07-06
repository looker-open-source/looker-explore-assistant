# load_samples.py
import os
from looker_project_vars import project_id, dataset_id, samples_table_id, samples_folder
from utils_bigquery import (
    get_bigquery_client,
    delete_existing_rows,
    load_data_from_file,
    insert_data_into_bigquery,
)


def load_examples(samples_folder):
    client = get_bigquery_client(project_id)
    delete_existing_rows(client, project_id, dataset_id, samples_table_id)

    models = os.listdir(samples_folder)
    for model in models:
        model_path = os.path.join(samples_folder, model)
        if os.path.isdir(model_path):
            file_names = os.listdir(model_path)
            for file_name in file_names:
                explore = os.path.splitext(file_name)[0]
                explore_id = f"{model}:{explore}"
                data = load_data_from_file(os.path.join(model_path, file_name))
                insert_data_into_bigquery(
                    client, dataset_id, samples_table_id, explore_id, data, "samples"
                )


if __name__ == "__main__":
    load_examples(samples_folder)
