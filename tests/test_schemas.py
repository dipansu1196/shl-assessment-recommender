"""
Unit tests for Pydantic schemas.

These tests validate that the schemas match the API contract exactly
and handle validation correctly.
"""

import pytest
from pydantic import ValidationError
from app.schemas import (
    Recommendation,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    HealthResponse
)


class TestRecommendation:
    """Test Recommendation schema."""
    
    def test_valid_recommendation(self):
        """Test valid recommendation creation."""
        rec = Recommendation(
            name="Occupational Personality Questionnaire OPQ32r",
            url="https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
            test_type="P"
        )
        
        assert rec.name == "Occupational Personality Questionnaire OPQ32r"
        assert rec.url.startswith("https://")
        assert rec.test_type == "P"
    
    def test_recommendation_with_multiple_test_types(self):
        """Test recommendation with comma-separated test types."""
        rec = Recommendation(
            name="Some Test",
            url="https://example.com/test",
            test_type="K,S"
        )
        
        assert rec.test_type == "K,S"
    
    def test_recommendation_missing_field(self):
        """Test that missing required field raises validation error."""
        with pytest.raises(ValidationError):
            Recommendation(
                name="Test Name",
                url="https://example.com"
                # Missing test_type
            )
    
    def test_recommendation_serialization(self):
        """Test that recommendation can be serialized to dict."""
        rec = Recommendation(
            name="Test",
            url="https://example.com",
            test_type="A"
        )
        
        data = rec.model_dump()
        assert data == {
            "name": "Test",
            "url": "https://example.com",
            "test_type": "A"
        }


class TestChatMessage:
    """Test ChatMessage schema."""
    
    def test_valid_user_message(self):
        """Test valid user message."""
        msg = ChatMessage(role="user", content="I need a test for Java developers")
        
        assert msg.role == "user"
        assert msg.content == "I need a test for Java developers"
    
    def test_valid_assistant_message(self):
        """Test valid assistant message."""
        msg = ChatMessage(role="assistant", content="Here are some recommendations...")
        
        assert msg.role == "assistant"
        assert msg.content == "Here are some recommendations..."
    
    def test_invalid_role(self):
        """Test that invalid role raises validation error."""
        with pytest.raises(ValidationError):
            ChatMessage(role="system", content="Invalid role")
    
    def test_empty_content_allowed(self):
        """Test that empty content is allowed (edge case)."""
        msg = ChatMessage(role="user", content="")
        assert msg.content == ""


class TestChatRequest:
    """Test ChatRequest schema."""
    
    def test_valid_chat_request(self):
        """Test valid chat request with message history."""
        request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi, how can I help?"),
                ChatMessage(role="user", content="I need tests for Python developers")
            ]
        )
        
        assert len(request.messages) == 3
        assert request.messages[0].role == "user"
        assert request.messages[1].role == "assistant"
    
    def test_single_message_request(self):
        """Test request with single message."""
        request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="Hello")
            ]
        )
        
        assert len(request.messages) == 1
    
    def test_empty_messages_list(self):
        """Test that empty messages list is allowed but probably not useful."""
        request = ChatRequest(messages=[])
        assert len(request.messages) == 0
    
    def test_request_serialization(self):
        """Test that request can be created from dict (API input)."""
        data = {
            "messages": [
                {"role": "user", "content": "Test query"},
                {"role": "assistant", "content": "Test response"}
            ]
        }
        
        request = ChatRequest(**data)
        assert len(request.messages) == 2


class TestChatResponse:
    """Test ChatResponse schema."""
    
    def test_valid_response_with_recommendations(self):
        """Test response with recommendations."""
        response = ChatResponse(
            reply="Here are the recommended assessments:",
            recommendations=[
                Recommendation(
                    name="Test 1",
                    url="https://example.com/1",
                    test_type="K"
                ),
                Recommendation(
                    name="Test 2",
                    url="https://example.com/2",
                    test_type="P"
                )
            ],
            end_of_conversation=False
        )
        
        assert response.reply == "Here are the recommended assessments:"
        assert len(response.recommendations) == 2
        assert response.end_of_conversation is False
    
    def test_valid_response_without_recommendations(self):
        """Test clarifying response with empty recommendations."""
        response = ChatResponse(
            reply="Can you tell me more about the role?",
            recommendations=[],
            end_of_conversation=False
        )
        
        assert response.reply == "Can you tell me more about the role?"
        assert len(response.recommendations) == 0
        assert response.end_of_conversation is False
    
    def test_final_turn_response(self):
        """Test response marking end of conversation."""
        response = ChatResponse(
            reply="Those assessments should work well for your needs.",
            recommendations=[
                Recommendation(
                    name="Final Test",
                    url="https://example.com/final",
                    test_type="A"
                )
            ],
            end_of_conversation=True
        )
        
        assert response.end_of_conversation is True
    
    def test_response_missing_required_field(self):
        """Test that missing required field raises validation error."""
        with pytest.raises(ValidationError):
            ChatResponse(
                reply="Test",
                recommendations=[]
                # Missing end_of_conversation
            )
    
    def test_response_serialization(self):
        """Test that response serializes to correct JSON structure."""
        response = ChatResponse(
            reply="Test reply",
            recommendations=[],
            end_of_conversation=False
        )
        
        data = response.model_dump()
        assert "reply" in data
        assert "recommendations" in data
        assert "end_of_conversation" in data
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["end_of_conversation"], bool)


class TestHealthResponse:
    """Test HealthResponse schema."""
    
    def test_valid_health_response(self):
        """Test valid health response."""
        health = HealthResponse(status="ok")
        
        assert health.status == "ok"
    
    def test_health_serialization(self):
        """Test health response serialization."""
        health = HealthResponse(status="ok")
        data = health.model_dump()
        
        assert data == {"status": "ok"}
    
    def test_health_custom_status(self):
        """Test health response with custom status (e.g., degraded)."""
        health = HealthResponse(status="degraded")
        assert health.status == "degraded"


class TestAPIContractCompliance:
    """Test that schemas match the exact API contract from spec."""
    
    def test_chat_request_example_from_spec(self):
        """Test the exact example from SPEC.md Section 4."""
        # From spec: POST /chat Request
        request_data = {
            "messages": [
                {"role": "user", "content": "I need a Python test"},
                {"role": "assistant", "content": "Here's what I recommend..."}
            ]
        }
        
        request = ChatRequest(**request_data)
        assert len(request.messages) == 2
    
    def test_chat_response_example_from_spec(self):
        """Test the exact structure from SPEC.md Section 4."""
        # From spec: POST /chat Response
        response = ChatResponse(
            reply="Here are some recommendations",
            recommendations=[
                Recommendation(
                    name="Python Test",
                    url="https://example.com/python",
                    test_type="K"
                )
            ],
            end_of_conversation=False
        )
        
        data = response.model_dump()
        
        # Verify exact field names from spec
        assert "reply" in data
        assert "recommendations" in data
        assert "end_of_conversation" in data
        
        # Verify structure
        assert isinstance(data["reply"], str)
        assert isinstance(data["recommendations"], list)
        assert isinstance(data["end_of_conversation"], bool)
        
        # Verify recommendation structure
        if len(data["recommendations"]) > 0:
            rec = data["recommendations"][0]
            assert "name" in rec
            assert "url" in rec
            assert "test_type" in rec
    
    def test_health_response_example_from_spec(self):
        """Test the exact structure from SPEC.md Section 4."""
        # From spec: GET /health → 200 {"status": "ok"}
        health = HealthResponse(status="ok")
        data = health.model_dump()
        
        assert data == {"status": "ok"}


if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
