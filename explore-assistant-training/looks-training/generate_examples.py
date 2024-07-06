import json
import os
from looker_looks import fetchLooksInFolder, fetchLookDetails
from looker_project_vars import folder_ids, additional_prompts_folder, examples_folder
from looker_url import process_url


def generate_prompts(folder_ids, additional_prompts_folder, examples_folder):
    explore_ids = set(folder_ids.keys())

    # Build explore_ids by browsing folders and files in additional_prompts
    for model_folder in os.listdir(additional_prompts_folder):
        model_path = os.path.join(additional_prompts_folder, model_folder)
        if os.path.isdir(model_path):
            for filename in os.listdir(model_path):
                if filename.endswith(".json"):
                    explore_name = filename[:-5]  # Remove .json extension
                    explore_id = f"{model_folder}:{explore_name}"
                    explore_ids.add(explore_id)

    print(f"explore_ids: {explore_ids}")
    for explore_id in explore_ids:
        look_prompts = []

        # Process Looker folder IDs
        if explore_id in folder_ids:
            for folder_id in folder_ids[explore_id]:
                looks = fetchLooksInFolder(folder_id)
                for look in looks:
                    look_details = fetchLookDetails(look.id)
                    processed_url = process_url(look_details.query.url)
                    prompt = {"input": look_details.title, "output": processed_url}
                    look_prompts.append(prompt)

        # Load additional prompts if available
        additional_prompts = []
        model, explore = explore_id.split(":")
        additional_prompts_path = os.path.join(
            additional_prompts_folder, model, f"{explore}.json"
        )
        if os.path.exists(additional_prompts_path):
            with open(additional_prompts_path, "r") as file:
                additional_prompts = json.load(file)

        # Combine prompts and write to file
        prompts = additional_prompts + look_prompts
        output_folder = os.path.join(examples_folder, model)
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, f"{explore}.json")

        with open(output_path, "w") as f:
            json.dump(prompts, f, indent=4)

        print(f"Data has been successfully generated for explore_id {explore_id}")


if __name__ == "__main__":
    generate_prompts(folder_ids, additional_prompts_folder, examples_folder)
