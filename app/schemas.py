"""
Pydantic models matching the API contract exactly.

Field names are fixed and must match the specification in Section 4 of SHL_PROJECT_SPEC.md.
The grader's harness depends on exact schema match.
"""

from typing import Literal
from pydantic import BaseModel


class Recommendation(BaseModel):
    """A single recommended assessment."""

    name: str
    url: str
    test_type: str


class ChatMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """POST /chat request body."""

    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    """POST /chat response body."""

    reply: str
    recommendations: list[Recommendation]
    end_of_conversation: bool


class HealthResponse(BaseModel):
    """GET /health response body."""

    status: str
