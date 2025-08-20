"""
Unit tests for core.models module
"""

import pytest
from pydantic import ValidationError
from datetime import datetime

from core.models import (
    FieldMatch,
    VertexResponse,
    ExploreInfo,
    QueryParameters,
    VectorSearchResult,
    UserContext,
    AreaInfo,
    GenerationResult
)


class TestFieldMatch:
    """Test FieldMatch model"""
    
    def test_valid_field_match(self):
        field_match = FieldMatch(
            field_name="test_field",
            field_location="test_table.test_field",
            similarity_score=0.85,
            description="Test field description",
            field_type="string"
        )
        
        assert field_match.field_name == "test_field"
        assert field_match.similarity_score == 0.85
        assert field_match.description == "Test field description"
    
    def test_required_fields_only(self):
        field_match = FieldMatch(
            field_name="test_field",
            field_location="test_table.test_field",
            similarity_score=0.85
        )
        
        assert field_match.field_name == "test_field"
        assert field_match.description is None
        assert field_match.field_type is None
    
    def test_invalid_similarity_score(self):
        # Pydantic should allow any float, but let's test edge cases
        field_match = FieldMatch(
            field_name="test_field",
            field_location="test_table.test_field",
            similarity_score=1.5  # This should still be valid
        )
        
        assert field_match.similarity_score == 1.5


class TestVertexResponse:
    """Test VertexResponse model"""
    
    def test_valid_vertex_response(self):
        response = VertexResponse(
            text="Test response text",
            candidates=[{"content": {"parts": [{"text": "Test"}]}}],
            usage_metadata={"tokens": 100}
        )
        
        assert response.text == "Test response text"
        assert len(response.candidates) == 1
        assert response.usage_metadata["tokens"] == 100
    
    def test_minimal_vertex_response(self):
        response = VertexResponse(text="Test response")
        
        assert response.text == "Test response"
        assert response.candidates == []
        assert response.usage_metadata is None


class TestQueryParameters:
    """Test QueryParameters model"""
    
    def test_valid_query_parameters(self):
        params = QueryParameters(
            model="test_model",
            view="test_explore",
            fields=["field1", "field2"],
            filters={"field1": "value1"},
            sorts=["field1 desc"],
            pivots=["field2"],
            limit=100
        )
        
        assert params.model == "test_model"
        assert params.view == "test_explore"
        assert len(params.fields) == 2
        assert params.filters["field1"] == "value1"
        assert params.limit == 100
    
    def test_default_values(self):
        params = QueryParameters(
            model="test_model",
            view="test_explore"
        )
        
        assert params.fields == []
        assert params.filters == {}
        assert params.sorts == []
        assert params.pivots == []
        assert params.limit == 500


class TestVectorSearchResult:
    """Test VectorSearchResult model"""
    
    def test_valid_search_result(self):
        field_match = FieldMatch(
            field_name="test_field",
            field_location="test_table.test_field",
            similarity_score=0.85
        )
        
        result = VectorSearchResult(
            query="test query",
            matches=[field_match],
            search_type="semantic",
            total_results=1,
            processing_time=0.5
        )
        
        assert result.query == "test query"
        assert len(result.matches) == 1
        assert result.search_type == "semantic"
        assert result.total_results == 1
        assert result.processing_time == 0.5


class TestUserContext:
    """Test UserContext model"""
    
    def test_user_context_defaults(self):
        context = UserContext()
        
        assert context.email is None
        assert context.user_id is None
        assert context.permissions == []
        assert context.preferences == {}
    
    def test_user_context_with_data(self):
        context = UserContext(
            email="test@example.com",
            user_id="user123",
            permissions=["read", "write"],
            preferences={"theme": "dark"}
        )
        
        assert context.email == "test@example.com"
        assert context.user_id == "user123"
        assert "read" in context.permissions
        assert context.preferences["theme"] == "dark"


class TestAreaInfo:
    """Test AreaInfo model"""
    
    def test_valid_area_info(self):
        area = AreaInfo(
            area="Sales & Revenue",
            explore_key="sales_demo:order_items",
            description="Sales and revenue metrics"
        )
        
        assert area.area == "Sales & Revenue"
        assert area.explore_key == "sales_demo:order_items"
        assert area.description == "Sales and revenue metrics"
    
    def test_missing_required_field(self):
        with pytest.raises(ValidationError):
            AreaInfo(
                area="Sales & Revenue"
                # Missing explore_key and description
            )


class TestGenerationResult:
    """Test GenerationResult model"""
    
    def test_valid_generation_result(self):
        query_params = QueryParameters(
            model="test_model",
            view="test_explore",
            fields=["field1"]
        )
        
        result = GenerationResult(
            explore_params=query_params,
            explore_key="test_model:test_explore",
            original_prompt="test prompt",
            generation_method="vector_search_enhanced"
        )
        
        assert result.explore_params.model == "test_model"
        assert result.explore_key == "test_model:test_explore"
        assert result.original_prompt == "test prompt"
        assert result.generation_method == "vector_search_enhanced"
        assert result.vector_search_used is None
        assert result.confidence_score is None