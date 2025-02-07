import os

# List of explore IDs to process
explore_ids = [
    "sample_project:explore_id_1",  # Example explore ID 1
    "sample_project:explore_id_2",  # Example explore ID 2
    "sample_project:explore_id_3"   # Example explore ID 3
]

# Common command template
base_command_template = (
    "python load_examples.py "
    "--project_id {project_id} "
    "--explore_id {explore_id} "
    "--table_id {table_id} "
    "--json_file {json_file} "
)

# Command configurations for different tables and JSON files
commands = [
    {"table_id": "example_table_1", "json_file": "example_file_1.json"},
    {"table_id": "example_table_2", "json_file": "example_file_2.json"},
    {"table_id": "example_table_3", "json_file": "example_file_3.json", "column_name": "example_column"}
]

# Define the project ID (replace with your project ID)
project_id = "sample_project_id"

# Iterate over explore IDs and commands
for explore_id in explore_ids:
    for cmd in commands:
        command = base_command_template.format(
            project_id=project_id,
            explore_id=explore_id,
            table_id=cmd["table_id"],
            json_file=cmd["json_file"]
        )
        # Add column_name if available
        if "column_name" in cmd:
            command += f"--column_name {cmd['column_name']} "
        
        print(f"Running: {command}")
        os.system(command)
