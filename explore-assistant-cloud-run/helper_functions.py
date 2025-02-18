# helper_functions.py

import os
import logging
import mysql.connector
import requests
import vertexai
from requests.auth import HTTPBasicAuth
from google.cloud import bigquery
from contextlib import contextmanager
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig

# Configuration (Best practice: use a dedicated config management library)
PROJECT = os.getenv("PROJECT_NAME")
REGION = os.getenv("REGION_NAME")
LOOKER_API_URL = os.getenv("LOOKER_API_URL", "https://looker.example.com/api/4.0")
LOOKER_CLIENT_ID = os.getenv("LOOKER_CLIENT_ID")
LOOKER_CLIENT_SECRET = os.getenv("LOOKER_CLIENT_SECRET")
CLOUD_SQL_HOST = os.getenv("CLOUD_SQL_HOST")
CLOUD_SQL_USER = os.getenv("CLOUD_SQL_USER")
CLOUD_SQL_PASSWORD = os.getenv("CLOUD_SQL_PASSWORD")
CLOUD_SQL_DATABASE = os.getenv("CLOUD_SQL_DATABASE")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "beck_explore_assistant")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "_prompts")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.0-pro-001")
IS_DEV_SERVER = os.getenv("IS_DEV_SERVER")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")

if (
    not PROJECT or
    not REGION or
    not OAUTH_CLIENT_ID or 
    not LOOKER_CLIENT_ID or 
    not LOOKER_CLIENT_SECRET
):
    raise ValueError("Missing required environment variables.")

logging.basicConfig(level=logging.INFO)

# Initialize the Vertex AI model globally
vertexai.init(project=PROJECT, location=REGION)
model = GenerativeModel(MODEL_NAME)

@contextmanager
def mysql_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=CLOUD_SQL_HOST, user=CLOUD_SQL_USER, password=CLOUD_SQL_PASSWORD, database=CLOUD_SQL_DATABASE
        )
        yield connection
    finally:
        if connection is not None and connection.is_connected():
            connection.close()

def validate_bearer_token(request):
    
    if IS_DEV_SERVER:
        # bypass for local development server
        return True
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logging.error("Missing or malformed Authorization header")
        return False

    token = auth_header.split(' ')[1]
    try:
        # Validate access token using Google's tokeninfo endpoint
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')

        if response.status_code == 200:
            token_info = response.json()
            # Verify the token was issued for our client ID
            expected_client_id = OAUTH_CLIENT_ID
            if token_info.get('azp') != expected_client_id:
                logging.error(f"Token was issued for different client ID: {token_info.get('azp')}")
                return False

            logging.info(f"Token verification successful. Info: {token_info}")
            return True

        logging.error(f"Token validation failed with status code: {response.status_code}")
        logging.error(f"Response content: {response.text}")
        return False

    except Exception as e:
        logging.error(f"Token validation failed with unexpected error: {str(e)}")
        return False

def get_response_headers():
    return {
        "Access-Control-Allow-Origin": "*",  # Be cautious in production!
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Signature, Authorization",
    }


def log_request(data: dict | str, caller: str):
    # Check if the input data is a string
    if isinstance(data, str):
        # If it's a string, create a JSON object with the caller and message
        log_data = {"caller": caller, "message": data}
    else:
        log_data = data
        log_data.update({"caller": caller})    
    with open("request.log", "a") as f:
        f.write("\n\n\n\n" + "=" * 100 + "\n\n\n\n")
        f.write(json.dumps(log_data,indent=4))
        f.write("\n\n\n\n" + "=" * 100 + "\n\n\n\n")

if IS_DEV_SERVER:
    with open("request.log", 'w') as log_file:
        log_file.write('')  # Truncate the file

def verify_looker_user(user_id):
    looker_api_url = f"{LOOKER_API_URL}/user/{user_id}"
    auth = HTTPBasicAuth(LOOKER_CLIENT_ID, LOOKER_CLIENT_SECRET)
    response = requests.get(looker_api_url, auth=auth)

    if response.status_code == 200:
        return True

    logging.warning(
        f"Looker user verification failed for user {user_id}: {response.status_code} {response.text}"
    )
    return False
def get_user_from_db(user_id):
    try:
        with mysql_connection() as connection:
            with connection.cursor(dictionary=True) as cursor:
                query = "SELECT user_id, name, email FROM users WHERE user_id = %s"
                cursor.execute(query, (user_id,))
                user_data = cursor.fetchone()
                return user_data
    except mysql.connector.Error as e:
        logging.error(f"Database error in get_user_from_db: {e}")
        return None

def create_new_user(user_id, name, email):
    try:
        with mysql_connection() as connection:
            with connection.cursor() as cursor:
                query = "INSERT INTO users (user_id, name, email) VALUES (%s, %s, %s)"
                cursor.execute(query, (user_id, name, email))
                connection.commit()
                return {"user_id": user_id, "status": "created"}
    except mysql.connector.Error as e:
        # logging.error(f"Database error in create_new_user: {e}")
        raise Exception(f"Failed to create user: {e}")

def create_chat_thread(user_id, explore_key):
    try:
        with mysql_connection() as connection:
            with connection.cursor() as cursor:
                query = "INSERT INTO chats (explore_key, user_id) VALUES (%s, %s)"
                cursor.execute(query, (explore_key, user_id))
                connection.commit()
                chat_id = cursor.lastrowid
                return chat_id
    except mysql.connector.Error as e:
        # logging.error(f"Database error in create_chat_thread: {e}")
        raise Exception(f"Database error in create_chat_thread: {e}")

def add_message(chat_id, user_id, content, is_user_message=1):
    try:
        with mysql_connection() as connection:
            with connection.cursor() as cursor:
                query = "INSERT INTO messages (chat_id, user_id, content, is_user_message) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (chat_id, user_id, content, is_user_message))
                connection.commit()
                message_id = cursor.lastrowid
                return message_id
    except mysql.connector.Error as e:
        logging.error(f"Database error in add_message: {e}")
        return None

def add_feedback(user_id, message_id, feedback_text, is_positive):
    try:
        with mysql_connection() as connection:
            with connection.cursor() as cursor:
                query = "INSERT INTO feedback (user_id, message_id, feedback_text, is_positive) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (user_id, message_id, feedback_text, is_positive))
                connection.commit()
                feedback_id = cursor.lastrowid
                update_query = "UPDATE messages SET feedback_id = %s WHERE message_id = %s"
                cursor.execute(update_query, (feedback_id, message_id))
                connection.commit()
                return True
    except mysql.connector.Error as e:
        logging.error(f"Database error in add_feedback: {e}")
        return False

def generate_looker_query(contents, parameters=None):
    default_parameters = {"temperature": 0.2, "max_output_tokens": 500, "top_p": 0.8, "top_k": 40}
    if parameters:
        default_parameters.update(parameters)

    response = model.generate_content(
        contents=contents,
        generation_config=GenerationConfig(**default_parameters),
    )

    metadata = response._raw_response.usage_metadata
    log_entry = {
        "severity": "INFO",
        "message": {
            "request": contents,
            "response": response.text,
            "input_characters": metadata.prompt_token_count,
            "output_characters": metadata.candidates_token_count,
        },
        "component": "explore-assistant-metadata",
    }
    logging.info(log_entry)
    return response.text

def generate_response(contents, parameters=None):
    default_parameters = {"temperature": 0.3, "max_output_tokens": 600, "top_p": 0.9, "top_k": 50}
    if parameters:
        default_parameters.update(parameters)

    response = model.generate_content(
        contents=contents,
        generation_config=GenerationConfig(**default_parameters)
    )

    metadata = response._raw_response.usage_metadata

    entry = {
        "severity": "INFO",
        "message": {"request": contents, "response": response.text,
                    "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count},
        "component": "prompt-response-metadata",
    }
    logging.info(entry)
    return response.text

def record_prompt(data):
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
    table_ref = f"{PROJECT}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    try:
      load_job = client.load_table_from_json(data, table_ref, job_config=job_config)
      load_job.result()  # Wait for the job to complete
      logging.info(f"Loaded {load_job.output_rows} prompts into {table_ref}")
    except Exception as e:
      logging.error(f"BigQuery load job failed: {e}")
