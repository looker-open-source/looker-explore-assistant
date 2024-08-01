from looker_looks import sdk
from looker_sdk import error


def listAllFolders():
    try:
        # Fetch all folders
        folders = sdk.all_folders()
        return folders
    except error.SDKError as e:
        print(e.message)
        return []


if __name__ == "__main__":
    folders = listAllFolders()
    for folder in folders:
        print(
            f"Folder ID: {folder.id}, Name: {folder.name}, Parent ID: {folder.parent_id}"
        )
