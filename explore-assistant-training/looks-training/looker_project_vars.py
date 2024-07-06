import configparser
import ast

# Read the configurations from the looker_project.ini file
config = configparser.ConfigParser()
config.read("looker_project.ini")

project_id = config["looker_project"]["project_id"]
location = config["looker_project"]["location"]
dataset_id = config["looker_project"]["dataset_id"]
examples_table_id = config["looker_project"]["examples_table_id"]
samples_table_id = config["looker_project"]["samples_table_id"]
folder_ids_str = config["looker_project"]["folder_ids"]
folder_ids = ast.literal_eval(folder_ids_str)
examples_folder = config["looker_project"]["examples_folder"]
samples_folder = config["looker_project"]["samples_folder"]
additional_prompts_folder = config["looker_project"]["additional_prompts_folder"]
looks_folder = config["looker_project"]["looks_folder"]
