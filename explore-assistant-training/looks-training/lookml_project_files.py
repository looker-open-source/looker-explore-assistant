import os
import looker_sdk
from looker_sdk import error

# Initialize the Looker SDK
sdk = looker_sdk.init40("looker.ini")


def save_project_files(project_id):
    try:
        # Fetch all project files
        response = sdk.all_project_files(project_id)

        # Create a directory with the project name
        project_name = project_id  # Assuming the project_id is also the project name
        if not os.path.exists(project_name):
            os.makedirs(project_name)

        # Save each file to the directory
        for project_file in response:
            file_path = project_file.path

            # Fetch the file content
            file_content = sdk.get_project_file(project_id, file_path)

            save_path = os.path.join(project_name, file_path)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Write the file content to the file
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(file_content)

        print(
            f"All files from project '{project_id}' have been saved to the '{project_name}' folder."
        )
    except error.SDKError as e:
        print(f"An SDK error occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    # Replace 'your_project_id' with the actual project ID you want to fetch files from
    project_id = "cusa-nlp"
    save_project_files(project_id)
