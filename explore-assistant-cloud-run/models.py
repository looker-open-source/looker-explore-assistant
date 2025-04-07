from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import json
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.mysql import LONGTEXT

class User(SQLModel, table=True):
    __tablename__ = "users"

    user_id: str = Field(primary_key=True)
    name: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    threads: List["Thread"] = Relationship(back_populates="user")

class Thread(SQLModel, table=True):
    __tablename__ = "threads"

    thread_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.user_id")
    explore_key: Optional[str]
    explore_id: Optional[str]
    model_name: Optional[str]
    explore_url: Optional[str] = Field(sa_column=Column(LONGTEXT))
    summarized_prompt: Optional[str] = Field(
        description="""
        The last user prompt summarized by LLM.
        This is also the thread title shown on sidebar
        Gets updated with every new prompt from user.
        """,
        sa_column=Column(LONGTEXT)
        )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_deleted: bool = Field(default=False)
    
    
    # Store as LONGTEXT and handle JSON conversion manually
    prompt_list_str: Optional[str] = Field(
        sa_column=Column(LONGTEXT, name='prompt_list'), 
        default=None
        )

    @property
    def prompt_list(self) -> List[str]:
        """Get the prompt list as a Python list"""
        if not self.prompt_list_str:
            return []
        try:
            return json.loads(self.prompt_list_str)
        except:
            return []
    
    @prompt_list.setter
    def prompt_list(self, value: List[str]):
        """Set the prompt list from a Python list"""
        if value is None:
            self.prompt_list_str = None
        else:
            self.prompt_list_str = json.dumps(value)  



    
    user: User = Relationship(back_populates="threads")
    messages: List["Message"] = Relationship(back_populates="thread")

# const threadFieldMapping = {
#   // FE field name: BE field name
#   uuid: 'thread_id',
#   userId: 'user_id',
#   exploreKey: 'explore_key',
#   exploreId: 'explore_id',
#   modelName: 'model_name',
#   messages: 'messages',
#   exploreUrl: 'explore_url',
#   summarizedPrompt: 'summarized_prompt',
#   promptList: 'prompt_list',
#   createdAt: 'created_at'
# };

# class Message(SQLModel, table=True):
#     __tablename__ = "messages"

#     message_id: Optional[int] = Field(default=None, primary_key=True)
#     contents: str = Field(sa_column=Column(LONGTEXT))
#     prompt_type: Optional[str] = None
#     current_explore_key: str
#     raw_prompt: Optional[str] = Field(sa_column=Column(LONGTEXT))
#     thread_id: int = Field(foreign_key="threads.thread_id")
#     user_id: str = Field(foreign_key="users.user_id")
#     actor: Literal["user","system"]
#     llm_response: Optional[str] = Field(sa_column=Column(LONGTEXT))
#     timestamp: datetime = Field(default_factory=datetime.utcnow)
    
#     thread: "Thread" = Relationship(back_populates="messages")
#     feedback: Optional["Feedback"] = Relationship(back_populates="message")



class Message(SQLModel, table=True):
    __tablename__ = "messages"
    
    # general fields reused across Message and useSendVertexMessage requests
    message_id: Optional[int] = Field(
        default=None,
        primary_key=True,
        description="maps to uuid of FE message"
        )
    actor: str = Field(
        description="""
        Literal["user", "system"]
        The actor that invoked this message.
        'user' as input from user, 
        and 'system' as the multi turn prompt from the FE hook useSendVertexMessage.
        """
        )
    type: Optional[str] = Field(
        description="""
        The type of actual rendered message in FE thread view.
        Literal["text", "explore", "summarize"]
        'text' as the user input
        'explore' or 'summarize' as the LLM response
        NULL as the multi turn prompt to generate the final rendered assistant message; 
        NULL is Not visible in the thread FE
        """
        )
    
    # Fields for TextMessage
    message: Optional[str] = Field(
        description="""
        Rendered in UI. 
        The user input in FE thread view.
        """
    )
    
    # Fields for ExploreMessage and SummarizeMessage
    summarized_prompt: Optional[str] = Field(
        description="""
        Rendered in UI.
        The raw user input from TextMessage component, summarized by LLM. 
        """
    )
    explore_url: Optional[str] = Field(
        description="""
        Rendered in UI.
        The generated looker url LLM return for given summarized_prompt.
        """,
        sa_column=Column(LONGTEXT)
    )
    
    # Fields for SummarizeMessage only
    summary: Optional[str] = Field(
        description="""
        Rendered in UI.
        The LLM executive summary rendered in Thread UI.
        Used when user 'message_type' is 'summarize' i.e. 'show me the data'
        """,
        sa_column=Column(LONGTEXT)
    )


    # Fields for logging purpose i.e. comming from useSendVertexMessage hook
    prompt_type: Optional[str] = Field(
        description="""
        From useSendVertexMessage. 
        Indicates the original function that invoked this prompt
        i.e. generateExploreUrl, isSummarizationPrompt, summarizePrompt.
        """
    )
    contents: Optional[str] = Field(
        description="""
        From useSendVertexMessage.
        The prompt sent to LLM to generate required content for vertex related workflow.
        """,
        sa_column=Column(LONGTEXT)
    )
    raw_prompt: Optional[str] = Field(
        description="""
        From useSendVertexMessage.
        The context generated by useSendVertexMessage passed to the prompt 'contents'.
        """,
        sa_column=Column(LONGTEXT)
    )
    parameters_str: Optional[str] = Field(
        description="""
        From useSendVertexMessage.
        LLM Parameters passed to the LLM.
        Currently only generateExploreUrl uses this with default
        max_output_tokens = 1000
        """,
        sa_column=Column(LONGTEXT, name="param")
    )
    llm_response: Optional[str] = Field(
        description="""
        From useSendVertexMessage.
        The LLM response to the prompt from 'contents'.
        """
        ,sa_column=Column(LONGTEXT)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)


    # FKs
    thread_id: int = Field(foreign_key="threads.thread_id")
    user_id: str = Field(foreign_key="users.user_id")    

    thread: "Thread" = Relationship(back_populates="messages")
    feedback: Optional["Feedback"] = Relationship(back_populates="message")



    # converter for param str
    @property
    def parameters(self) -> Dict[str, Any]:
        if not self.parameters_str:
            return {}
        try:
            return json.loads(self.parameters_str)
        except:
            return {}

    @parameters.setter
    def parameters(self, value: Dict[str, Any]):
        if value is None:
            self.parameters_str = None
        else:
            self.parameters_str = json.dumps(value)



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

class ThreadRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    explore_key: str = Field(..., description="Explore key")

class MessageRequest(BaseModel):
    # PK 
    message_id: Optional[int] = Field(None,description="message id")

    # FK
    user_id: str = Field(..., description="User ID")
    thread_id: int = Field(..., description="Thread ID this message is created in")
    
    # remaining fields
    actor: Literal["user", "system"] = Field(..., description="Flag indicating the message originates from user or system")
    contents: str = Field(..., description="The message contents")
    prompt_type: str = Field(..., description="Type of prompt")
    raw_prompt: str = Field(..., description="Original prompt")
    parameters: Dict[str, Any] = Field(None, description="Optional parameters for the message")

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

class ThreadHistoryResponse(BaseModel):
    data: List[Dict[str, Any]]

class SearchResponse(BaseModel):
    message: str
    data: Dict[str, Any] 


class UserThreadsRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    limit: Optional[int] = Field(10, description="Maximum number of threads to return")
    offset: Optional[int] = Field(0, description="Offset for pagination")    

class UserThreadsResponse(BaseModel):
    # list of Dict instead of List[Thread] to include custom prop prompt_list
    threads: List[Dict]
    total_count: int

class ThreadMessagesRequest(BaseModel):
    thread_id: int = Field(..., description="Thread ID")
    limit: Optional[int] = Field(50, description="Maximum number of messages to return")
    offset: Optional[int] = Field(0, description="Offset for pagination")

class ThreadMessagesResponse(BaseModel):
    # List of Dict instead of List[Message] to include the custom prop "parameter"
    messages: List[Dict]
    total_count: int

class ThreadDeleteRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    thread_ids: List[int] = Field(..., description="List of thread IDs to mark as deleted")
