# helper_functions.py

import os
import logging
import requests
import vertexai
from requests.auth import HTTPBasicAuth
import time
from google.cloud import bigquery
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional
from sqlmodel import Session, select
from models import User, Chat, Message, Feedback
from database import engine


load_dotenv()
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
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
VERTEX_CF_AUTH_TOKEN = os.environ.get("VERTEX_CF_AUTH_TOKEN")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")

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


class DatabaseError(Exception):
    def __init__(self, message, details):
        super().__init__(message)
        self.details = details

def validate_bearer_token(token: str) -> bool:
    if not token:
        logging.error("Empty token provided")
        return False
    if token == ADMIN_TOKEN:
        return True
    try:
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')

        if response.status_code == 200:
            token_info = response.json()
            if token_info.get('azp') != OAUTH_CLIENT_ID:
                logging.error(f"Token was issued for different client ID: {token_info.get('azp')}")
                return False
            if int(token_info['exp']) < int(time.time()):
                logging.error("Token has expired")
                return False
            return True
        
    except Exception as e:
        logging.error(f"Token validation failed with unexpected error: {str(e)}")
    return False

def verify_looker_user(user_id: str) -> bool:
    looker_api_url = f"{LOOKER_API_URL}/user/{user_id}"
    auth = HTTPBasicAuth(LOOKER_CLIENT_ID, LOOKER_CLIENT_SECRET)
    response = requests.get(looker_api_url, auth=auth)
    
    if response.status_code == 200:
        return True
        
    logging.warning(f"Looker user verification failed for user {user_id}: {response.status_code} {response.text}")
    return False

def get_user_from_db(user_id: str) -> Optional[Dict]:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            return {"user_id": user.user_id, "name": user.name, "email": user.email}
    return None

def create_new_user(user_id: str, name: str, email: str) -> Dict:
    try:
        with Session(engine) as session:
            user = User(user_id=user_id, name=name, email=email)
            session.add(user)
            session.commit()
            return {"user_id": user_id, "status": "created"}
    except Exception as e:
        raise DatabaseError("Failed to create user", str(e))

def create_chat_thread(user_id: str, explore_key: str) -> int:
    try:
        with Session(engine) as session:
            chat = Chat(user_id=user_id, explore_key=explore_key)
            session.add(chat)
            session.commit()
            session.refresh(chat)
            return chat.chat_id
    except Exception as e:
        raise DatabaseError("Failed to create chat thread", str(e))

def retrieve_chat_history(chat_id: int) -> Dict:
    try:
        with Session(engine) as session:
            messages = session.exec(
                select(Message)
                .where(Message.chat_id == chat_id)
                .order_by(Message.created_at)
            ).all()
            
            chat_history = []
            for msg in messages:
                message_data = {
                    "message_id": msg.message_id,
                    "content": msg.content,
                    "is_user_message": msg.is_user_message,
                    "created_at": msg.created_at,
                    "feedback_text": None,
                    "is_positive": None
                }
                
                if msg.feedback:
                    message_data.update({
                        "feedback_text": msg.feedback.feedback_text,
                        "is_positive": msg.feedback.is_positive
                    })
                    
                chat_history.append(message_data)
                
            return {"data": chat_history}
    except Exception as e:
        raise DatabaseError("Failed to retrieve chat history", str(e))

def add_message(chat_id: int, user_id: str, content: str, is_user: bool = True) -> str:
    try:
        with Session(engine) as session:
            message = Message(
                chat_id=chat_id,
                user_id=user_id,
                content=content,
                is_user=is_user
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message.message_id
    except Exception as e:
        raise DatabaseError("Failed to add message", str(e))

def add_feedback(user_id: str, message_id: int, feedback_text: str, is_positive: bool) -> bool:
    try:
        with Session(engine) as session:
            feedback = Feedback(
                user_id=user_id,
                message_id=message_id,
                feedback_text=feedback_text,
                is_positive=is_positive
            )
            session.add(feedback)
            
            # Update message with feedback
            message = session.get(Message, message_id)
            if message:
                message.feedback_id = feedback.feedback_id
                
            session.commit()
            return True
    except Exception as e:
        raise DatabaseError("Failed to add feedback", str(e))

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
    default_parameters = {"temperature": 0.2, "max_output_tokens": 500, "top_p": 0.8, "top_k": 40}
    if parameters:
        default_parameters.update(parameters)

    response = model.generate_content(
        contents=contents,
        generation_config=GenerationConfig(**default_parameters)
    )

    metadata = response._raw_response.usage_metadata

    entry = {
        "severity": "INFO",
        "message": {
            "request": contents, 
            "response": response.text,
            "input_characters": metadata.prompt_token_count, 
            "output_characters": metadata.candidates_token_count
            },
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

def search_chat_history(user_id: str, search_query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """
    Search through chat history for messages containing the search keywords.
    
    Args:
        user_id (str): The ID of the user whose chat history to search
        search_query (str): Keywords to search for
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        offset (int, optional): Number of results to skip. Defaults to 0.
    
    Returns:
        Dict containing:
            - total (int): Total number of matching chats
            - matches (List[Dict]): List of matching chats with messages
    """
    try:
        with Session(engine) as session:
            # Get total count
            total_count = session.exec(
                select([Chat])
                .join(Message)
                .where(Chat.user_id == user_id)
                .where(Message.content.contains(search_query))
                .distinct()
            ).count()
            
            # Get matching chats with messages
            chats = session.exec(
                select(Chat)
                .join(Message)
                .where(Chat.user_id == user_id)
                .where(Message.content.contains(search_query))
                .distinct()
                .order_by(Chat.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            
            matches = []
            for chat in chats:
                chat_data = {
                    'chat_id': chat.chat_id,
                    'explore_key': chat.explore_key,
                    'created_at': chat.created_at.isoformat(),
                    'messages': []
                }
                
                for message in chat.messages:
                    chat_data['messages'].append({
                        'message_id': message.message_id,
                        'content': message.content,
                        'timestamp': message.created_at.isoformat(),
                        'is_user': message.is_user_message,
                        'matches_search': search_query.lower() in message.content.lower()
                    })
                    
                matches.append(chat_data)
                
            return {
                "total": total_count,
                "matches": matches
            }

    except Exception as e:
        logging.error(f"Database error in search_chat_history: {e}")
        raise DatabaseError("Failed to search chat history", str(e))
