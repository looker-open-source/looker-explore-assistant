import json
from sqlmodel import SQLModel, create_engine, Session
from urllib.parse import quote_plus
import sys
import os

# Add the root directory to the Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
sys.path.insert(0, root_dir)

# Import models from cloud-run directory
sys.path.insert(0, os.path.join(root_dir, 'explore-assistant-cloud-run'))

def get_cloudsql_config():
    with open("cloudsql_outputs.json", "r") as f:
        data = json.load(f)
    return data["cloudsql_instance_info"]["value"]

def get_database_url():
    config = get_cloudsql_config()
    # Escape username and password for URL safety
    username = quote_plus(config['username'])
    password = quote_plus(config['password'])
    
    # Properly format the MySQL connection URL
    return f"mysql+pymysql://{username}:{password}@{config['public_ip']}/{config['database']}?charset=utf8mb4"

# Create engine with echo=True to see generated SQL statements
engine = create_engine(get_database_url(), echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session