from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    user_id: str = Field(primary_key=True)
    name: str
    email: str
    
    # Relationships
    chats: List["Chat"] = Relationship(back_populates="user")

class Chat(SQLModel, table=True):
    __tablename__ = "chats"
    
    chat_id: Optional[int] = Field(default=None, primary_key=True)
    explore_key: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(foreign_key="users.user_id")
    
    # Relationships
    user: User = Relationship(back_populates="chats")
    messages: List["Message"] = Relationship(back_populates="chat")

class Message(SQLModel, table=True):
    __tablename__ = "messages"
    
    message_id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    chat_id: int = Field(foreign_key="chats.chat_id")
    is_user_message: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_possitive_feedback: Optional[bool] = None
    feedback_message_id: Optional[int] = None
    
    # Relationships
    chat: Chat = Relationship(back_populates="messages")

class Feedback(SQLModel, table=True):
    __tablename__ = "feedbacks"
    
    feedback_message_id: Optional[int] = Field(default=None, primary_key=True)
    feedback_message: str
    is_possitive: bool 