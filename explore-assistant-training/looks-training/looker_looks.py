import os
import looker_sdk
from looker_sdk import error
from looker_project_vars import folder_ids, looks_folder
import json
from datetime import datetime

sdk = looker_sdk.init40("looker.ini")


def fetchLooksInFolder(folder_id):
    try:
        looks = sdk.search_looks(folder_id=folder_id)
        return looks
    except error.SDKError as e:
        print(e.message)
        return []


def fetchLookDetails(look_id):
    try:
        look = sdk.look(look_id)
        return look
    except error.SDKError as e:
        print(e.message)
        return None


def object_to_dict(obj):
    """
    Recursively convert an object into a dictionary.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: object_to_dict(value) for key, value in obj.items()}
    elif hasattr(obj, "__dict__"):
        return {key: object_to_dict(value) for key, value in obj.__dict__.items()}
    elif isinstance(obj, list):
        return [object_to_dict(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(object_to_dict(item) for item in obj)
    elif isinstance(obj, set):
        return {object_to_dict(item) for item in obj}
    else:
        return obj


def saveLooks(folder_id, save_path):
    looks_dict = []
    looks = fetchLooksInFolder(folder_id)
    for look in looks:
        look_details = fetchLookDetails(look.id)
        looks_dict.append(object_to_dict(look_details))
    with open(save_path, "w") as f:
        json.dump(looks_dict, f, indent=4)


if __name__ == "__main__":
    for key, ids in folder_ids.items():
        base_folder, sub_folder = key.split(":")
        folder_path = os.path.join(looks_folder, base_folder, sub_folder)
        os.makedirs(folder_path, exist_ok=True)
        for folder_id in ids:
            save_path = os.path.join(folder_path, f"looks_{folder_id}.json")
            saveLooks(folder_id, save_path)
