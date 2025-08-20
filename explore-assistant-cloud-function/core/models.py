"""
Data models and schemas for the Looker Explore Assistant

Contains Pydantic models and dataclasses used throughout the application.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class FieldMatch(BaseModel):
    """Represents a field match from vector search"""
    field_name: str = Field(..., description="Name of the matched field")
    field_location: str = Field(..., description="Location/table of the field")
    similarity_score: float = Field(..., description="Similarity score (0-1)")
    description: Optional[str] = Field(None, description="Field description")
    field_type: Optional[str] = Field(None, description="Field data type")


class VertexResponse(BaseModel):
    """Represents a response from Vertex AI"""
    text: str = Field(..., description="Response text from Vertex AI")
    candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Response candidates")
    usage_metadata: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    safety_ratings: Optional[List[Dict[str, Any]]] = Field(None, description="Safety ratings")


class ExploreInfo(BaseModel):
    """Information about a Looker explore"""
    explore_key: str = Field(..., description="Explore key in format 'model:explore'")
    model_name: str = Field(..., description="Model name")
    explore_name: str = Field(..., description="Explore name")
    description: Optional[str] = Field(None, description="Explore description")
    dimensions: List[Dict[str, Any]] = Field(default_factory=list, description="Available dimensions")
    measures: List[Dict[str, Any]] = Field(default_factory=list, description="Available measures")


class QueryParameters(BaseModel):
    """Looker query parameters"""
    model: str = Field(..., description="Looker model name")
    view: str = Field(..., description="Looker explore/view name")
    fields: List[str] = Field(default_factory=list, description="Fields to query")
    filters: Dict[str, str] = Field(default_factory=dict, description="Query filters")
    sorts: List[str] = Field(default_factory=list, description="Sort specifications")
    pivots: List[str] = Field(default_factory=list, description="Pivot specifications")
    limit: Optional[int] = Field(500, description="Query result limit")


class VectorSearchResult(BaseModel):
    """Result from vector search operation"""
    query: str = Field(..., description="Original search query")
    matches: List[FieldMatch] = Field(default_factory=list, description="Matching fields")
    search_type: str = Field(..., description="Type of search performed")
    total_results: int = Field(0, description="Total number of results")
    processing_time: float = Field(0.0, description="Search processing time in seconds")


class UserContext(BaseModel):
    """User context information"""
    email: Optional[str] = Field(None, description="User email address")
    user_id: Optional[str] = Field(None, description="User ID")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")


class AreaInfo(BaseModel):
    """Information about a business area"""
    area: str = Field(..., description="Area name")
    explore_key: str = Field(..., description="Associated explore key")
    description: str = Field(..., description="Area description")


class GenerationResult(BaseModel):
    """Result of parameter generation"""
    explore_params: QueryParameters = Field(..., description="Generated query parameters")
    explore_key: str = Field(..., description="Selected explore key")
    original_prompt: str = Field(..., description="Original user prompt")
    generation_method: str = Field(..., description="Method used for generation")
    vector_search_used: Optional[List[Dict[str, Any]]] = Field(None, description="Vector search operations performed")
    confidence_score: Optional[float] = Field(None, description="Generation confidence score")