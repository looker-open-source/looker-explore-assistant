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
from typing import Dict, Any, List, Optional, Tuple, Sequence
from sqlmodel import Session, select, func, desc, asc
from models import User, Thread, Message, Feedback
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

def create_chat_thread(user_id: str, explore_key: str) -> int | None:
    try:
        with Session(engine) as session:
            thread = Thread(user_id=user_id, explore_key=explore_key)
            session.add(thread)
            session.commit()
            session.refresh(thread)
            return thread.thread_id
    except Exception as e:
        raise DatabaseError("Failed to create thread", str(e))

def retrieve_thread_history(thread_id: int) -> Dict:
    try:
        with Session(engine) as session:
            messages = session.exec(
                select(Message)
                .where(Message.thread_id == thread_id)
                .order_by(desc(Message.created_at))
            ).all()
            
            thread_history = []
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
                    
                thread_history.append(message_data)
                
            return {"data": thread_history}
    except Exception as e:
        raise DatabaseError("Failed to retrieve thread history", str(e))

def _get_user_threads(
    user_id: str,
    limit: Optional[int] = 10,
    offset: Optional[int] = 0,
    ) -> Tuple:
    try:
        with Session(engine) as session:
            count_query = (select(func.count())
                           .select_from(Thread)
                           .where(Thread.user_id == user_id)
                           .where(Thread.is_deleted == False)
                           )
            total_count = session.exec(count_query).one()
            
            
            # Get thread summaries
            threads_query = (
                select(Thread)
                .where(Thread.user_id == user_id)
                .where(Thread.is_deleted == False)
                .order_by(desc(Thread.created_at))
                .offset(offset)
                .limit(limit)
            )    
            thread_results = session.exec(threads_query).all()
            # manually get prompt_list list from  prompt_list_str
            thread_response = [
                {
                    **thread.model_dump(), 
                    "prompt_list": thread.prompt_list
                }
                for thread in thread_results
            ]
            return thread_response, total_count
    except Exception as e:
        raise DatabaseError("Failed to retrieve user threads", str(e))


def _get_thread_messages(
        thread_id: int,
        limit: Optional[int] = 50,
        offset: Optional[int] = 0,
        ) -> Tuple:
    try: 
        with Session(engine) as session:
            count_query = select(func.count()).select_from(Message).where(Message.thread_id == thread_id)
            total_count = session.exec(count_query).one()            
            message_results = (
                session.exec(
                    select(Message)
                    .where(Message.thread_id == thread_id)
                    # filter only relevant messages for FE to load thread content
                    .where(Message.prompt_type == 'chatMessage') 
                    .limit(limit)
                    .offset(offset)
                    .order_by(desc(Message.created_at))
                ).all()
            )
            
            # manually get parameters from parameters_str
            message_response = [
                {
                    **message.model_dump(),
                    "parameters": message.parameters
                }
                for message in message_results
            ] 
            return message_response, total_count
    except Exception as e:
        raise DatabaseError("Failed to retrieve thread history", str(e))        
        
def soft_delete_specific_threads(user_id: str, thread_ids: List[int]) -> Dict[str, Any]:
    """
    Mark specific threads for a user as deleted (soft delete)
    
    Parameters:
    - user_id: The ID of the user
    - thread_ids: List of thread IDs to mark as deleted
    
    Returns:
    - Dictionary with count of affected threads
    """
    try:
        with Session(engine) as session:
            # Find all specified threads for the user that aren't already deleted
            threads = session.query(Thread).filter(
                Thread.user_id == user_id,
                Thread.thread_id.in_(thread_ids),
                Thread.is_deleted == False
            ).all()
            
            # Mark them as deleted
            count = 0
            for thread in threads:
                thread.is_deleted = True
                count += 1
            
            session.commit()
            return {"affected_count": count, "thread_ids": thread_ids}
    except Exception as e:
        raise DatabaseError("Failed to soft delete threads", {str(e)})

def add_message(**kwargs) -> int | None:
    try:
        with Session(engine) as session:
            message = Message(**kwargs)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message.message_id
    except Exception as e:
        raise DatabaseError("Failed to add message", str(e))

def _update_message(**kwargs) -> Message:
    try:
        with Session(engine) as session:
            message = session.get(Message, kwargs['message_id'])
            if not message:
                raise DatabaseError("Failed to update message", "Message not found")
            
            for key, value in kwargs.items():
                setattr(message, key, value)
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
    except Exception as e:
        raise DatabaseError("Failed to update message", str(e))


def add_feedback(user_id: str, message_id: int, feedback_text: str, is_positive: bool) -> Feedback:
    try:
        with Session(engine) as session:
            feedback = Feedback(
                user_id=user_id,
                message_id=message_id,
                feedback_text=feedback_text,
                is_positive=is_positive
            )
            session.add(feedback)
            session.commit()
            return feedback
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

def record_message(data):
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
    table_ref = f"{PROJECT}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"
    try:
      load_job = client.load_table_from_json(data, table_ref, job_config=job_config)
      load_job.result()  # Wait for the job to complete
      logging.info(f"Loaded {load_job.output_rows} messages into {table_ref}")
    except Exception as e:
      logging.error(f"BigQuery load job failed: {e}")

def search_thread_history(user_id: str, search_query: str, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    """
    Search through thread history for messages containing the search keywords.
    
    Args:
        user_id (str): The ID of the user whose thread history to search
        search_query (str): Keywords to search for
        limit (int, optional): Maximum number of results to return. Defaults to 10.
        offset (int, optional): Number of results to skip. Defaults to 0.
    
    Returns:
        Dict containing:
            - total (int): Total number of matching threads
            - matches (List[Dict]): List of matching threads with messages
    """
    try:
        with Session(engine) as session:
            # Get total count
            total_count = session.exec(
                select([Thread])
                .join(Message)
                .where(Thread.user_id == user_id)
                .where(Message.content.contains(search_query))
                .distinct()
            ).count()
            
            # Get matching threads with messages
            threads = session.exec(
                select(Thread)
                .join(Message)
                .where(Thread.user_id == user_id)
                .where(Message.content.contains(search_query))
                .distinct()
                .order_by(Thread.created_at.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            
            matches = []
            for thread in threads:
                thread_data = {
                    'thread_id': thread.thread_id,
                    'explore_key': thread.explore_key,
                    'created_at': thread.created_at.isoformat(),
                    'messages': []
                }
                
                for message in thread.messages:
                    thread_data['messages'].append({
                        'message_id': message.message_id,
                        'content': message.content,
                        'timestamp': message.created_at.isoformat(),
                        'is_user': message.is_user_message,
                        'matches_search': search_query.lower() in message.content.lower()
                    })
                    
                matches.append(thread_data)
                
            return {
                "total": total_count,
                "matches": matches
            }

    except Exception as e:
        logging.error(f"Database error in search_thread_history: {e}")
        raise DatabaseError("Failed to search thread history", str(e))




def _update_thread(**kwargs) -> Thread:
    """
    Update an existing thread in the database.
    
    Args:
        thread_id: The ID of the thread to update
        update_fields: Fields to update (explore_key, etc.)
        
    Returns:
        Thread
        
    Raises:
        DatabaseError: If the thread doesn't exist
    """
    try:
        with Session(engine) as session:
            # Get the thread
            thread = session.get(Thread, kwargs['thread_id'])
            
            if not thread:
                raise DatabaseError("Failed to update message",f"Thread with ID {kwargs['thread_id']} not found")
                
            
            # Update fields
            for key, value in kwargs.items():
                setattr(thread, key, value)
            
            session.add(thread)
            session.commit()
            session.refresh(thread)
            
            # Return updated thread data
            return thread


    except Exception as e:
        logging.error(f"Error updating thread: {str(e)}")
        raise DatabaseError("Failed to update thread", str(e))
