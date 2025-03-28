from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import uuid


class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: str = Field(primary_key=True)
    name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chats: List["Chat"] = Relationship(back_populates="user")

class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    chat_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id")
    explore_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="chats")
    messages: List["Message"] = Relationship(back_populates="chat")

class Message(SQLModel, table=True):
    __tablename__ = "messages"

    message_id: Optional[int] = Field(default=None, primary_key=True)

    
    chat_id: int = Field(foreign_key="chats.chat_id")
    contents: str
    prompt_type: Optional[str] = None
    current_explore_key: str
    raw_prompt: Optional[str]
    is_user: bool
    llm_response: Optional[str] = None
    user_id: str = Field(foreign_key="users.user_id")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    chat: "Chat" = Relationship(back_populates="messages")
    feedback: Optional["Feedback"] = Relationship(back_populates="message")


class Feedback(SQLModel, table=True):
    __tablename__ = "feedbacks"

    user_id: str = Field(foreign_key="users.user_id")
    feedback_id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="messages.message_id")
    feedback_text: str
    is_positive: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    message: Message = Relationship(back_populates="feedback")

# Request/Response Models
class LoginRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="User name")
    email: str = Field(..., description="User email")

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    explore_key: str = Field(..., description="Explore key")

class PromptRequest(BaseModel):
    contents: str = Field(..., description="The prompt contents")
    current_explore_key: str = Field(..., description="Current explore key")
    current_thread_id: Optional[int] = Field(None, description="Optional chat ID for existing conversations")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters for the prompt")
    prompt_type: str = Field(..., description="Type of prompt")
    raw_prompt: Optional[str] = Field("", description="Optional message")
    user_id: str = Field(..., description="User ID")
    message_id: Optional[int] = Field(None, description="the message ID sent from FE by either user or system.")
    is_user: bool = Field(..., description="flag indicating the message originates from user or system")

class FeedbackRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    message_id: int = Field(..., description="Message ID")
    feedback_text: str = Field(..., description="Feedback text")
    is_positive: bool = Field(..., description="Whether the feedback is positive")

class BaseResponse(BaseModel):
    """Base model for successful responses"""
    message: str
    data: Dict[str, Any]

class ErrorResponse(BaseModel):
    """Base model for error responses"""
    detail: str

class ChatHistoryResponse(BaseModel):
    data: List[Dict[str, Any]]

class SearchResponse(BaseModel):
    message: str
    data: Dict[str, Any] 