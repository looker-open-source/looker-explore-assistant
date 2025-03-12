from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

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
    content: str
    is_user: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    chat: Chat = Relationship(back_populates="messages")
    feedback: Optional["Feedback"] = Relationship(back_populates="message")

class Feedback(SQLModel, table=True):
    __tablename__ = "feedbacks"

    feedback_id: Optional[int] = Field(default=None, primary_key=True)
    message_id: int = Field(foreign_key="messages.message_id")
    feedback_text: str
    is_positive: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    message: Message = Relationship(back_populates="feedback")