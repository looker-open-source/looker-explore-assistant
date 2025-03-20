from database import create_db_and_tables, get_database_url
import sys
import os

# Add the root directory to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))

# Import models from cloud-run directory
sys.path.insert(0, os.path.join(root_dir, 'explore-assistant-cloud-run'))

def main():
    print("Creating database and tables...")
    print(f"Using database URL: {get_database_url()}")
    create_db_and_tables()
    print("Tables created successfully!")

if __name__ == "__main__":
    main() 