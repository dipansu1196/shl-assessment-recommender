"""
Conversation state machine for SHL Assessment Recommender.

This module implements the core conversation logic as specified in SPEC.md Section 5.
It's stateless - all context is reconstructed from the messages list on every call.
"""

import re
from typing import Dict, List, Any

from app import retrieval
from app import groq_client
from app.schemas import Recommendation


def handle_turn(messages: list[dict], turn_number: int = 0) -> dict:
    """
    Handle a conversation turn and return a response matching ChatResponse schema.

    This is the main state machine. On every call:
    1. Reconstruct context from message history (stateless)
    2. Classify user intent
    3. Branch to appropriate handler
    4. Return {reply, recommendations, end_of_conversation}

    Args:
        messages: List of dicts with "role" and "content" keys
        turn_number: Current user turn number (1-8), used for turn cap enforcement

    Returns:
        Dict with "reply" (str), "recommendations" (list), "end_of_conversation" (bool)
    """
    if not messages:
        return {
            "reply": "Hello! I can help you find the right SHL assessments for your hiring needs. What role are you hiring for?",
            "recommendations": [],
            "end_of_conversation": False,
        }

    # Check if we're near the turn cap (turn 7-8) and need to force a recommendation
    near_turn_cap = turn_number >= 7
    has_existing_shortlist = bool(_extract_current_shortlist(messages))
    
    # Step 1: Classify intent using Groq
    intent = groq_client.classify_intent(messages)

    # Force recommendation if near turn cap and no shortlist yet
    # This ensures we return SOMETHING with Recall@10 potential, not empty array
    if near_turn_cap and not has_existing_shortlist:
        if intent in ["clarify_needed", "off_topic_or_injection", "out_of_scope_advice"]:
            # Override: force recommendation with whatever context we have
            intent = "ready_to_recommend"

    # Step 2: Branch based on intent
    if intent == "clarify_needed":
        return _handle_clarify(messages)
    elif intent == "ready_to_recommend":
        return _handle_recommend(messages, is_forced=near_turn_cap and not has_existing_shortlist)
    elif intent == "refine_existing":
        return _handle_refine(messages)
    elif intent == "compare_request":
        return _handle_compare(messages)
    elif intent == "off_topic_or_injection":
        return _handle_off_topic(messages)
    elif intent == "out_of_scope_advice":
        return _handle_out_of_scope(messages)
    else:
        # Fallback - treat as clarify, but force recommend if near cap
        if near_turn_cap and not has_existing_shortlist:
            return _handle_recommend(messages, is_forced=True)
        return _handle_clarify(messages)


def _handle_clarify(messages: list[dict]) -> dict:
    """
    Handle clarify_needed intent.

    Ask exactly ONE clarifying question. No recommendations yet.
    Pattern from C1, C3, C9 - never a checklist, one question at a time.
    """
    result = groq_client.generate_response(messages, "clarify_needed", candidates=None)

    return {
        "reply": result["reply"],
        "recommendations": [],
        "end_of_conversation": False,
    }


def _handle_recommend(messages: list[dict], is_forced: bool = False) -> dict:
    """
    Handle ready_to_recommend intent.

    1. Retrieve top-15 candidates via semantic search
    2. Let LLM select 1-10 from those candidates by index
    3. Build recommendations from selected candidates (pass-through name/url/test_type)
    4. Never let LLM free-generate assessment names or URLs
    
    Args:
        messages: Conversation history
        is_forced: If True, this is a forced recommendation due to turn cap
    """
    # Build query from conversation context
    query = _build_query_from_context(messages)

    # Retrieve top candidates
    candidates = retrieval.search(query, k=15)
    
    # If forced and query is too generic, add a note to the LLM context
    action = "ready_to_recommend_forced" if is_forced else "ready_to_recommend"

    # Generate response with LLM selecting from candidates
    result = groq_client.generate_response(messages, action, candidates=candidates)

    # Build recommendations list from selected indices (structural constraint - no hallucination)
    recommendations = []
    for idx in result["selected_indices"]:
        if 0 <= idx < len(candidates):  # Bounds check
            candidate = candidates[idx]
            recommendations.append({
                "name": candidate["name"],
                "url": candidate["url"],
                "test_type": candidate["test_type"],
            })
    
    # If forced and we got no recommendations, use top 5 candidates as fallback
    if is_forced and not recommendations:
        for candidate in candidates[:5]:
            recommendations.append({
                "name": candidate["name"],
                "url": candidate["url"],
                "test_type": candidate["test_type"],
            })

    # Check if conversation should end (user accepts the shortlist)
    end_of_conversation = _should_end_conversation(messages, result["reply"])

    return {
        "reply": result["reply"],
        "recommendations": recommendations,
        "end_of_conversation": end_of_conversation,
    }


def _handle_refine(messages: list[dict]) -> dict:
    """
    Handle refine_existing intent.

    User wants to add/drop/modify existing shortlist.
    Pattern from C4, C8, C9, C10 - return FULL updated shortlist, not just delta.

    1. Reconstruct current shortlist from last assistant message (stateless)
    2. Re-retrieve with updated query context
    3. Merge per user instructions (add/drop)
    4. Return complete updated shortlist
    """
    # Reconstruct current shortlist from conversation history
    current_shortlist = _extract_current_shortlist(messages)

    # Build updated query
    query = _build_query_from_context(messages)

    # Retrieve fresh candidates
    candidates = retrieval.search(query, k=15)

    # Add current shortlist items to candidates pool for LLM to consider
    # This ensures items can be kept/dropped as requested
    current_names = {item["name"] for item in current_shortlist}
    for item in current_shortlist:
        # Only add if not already in candidates
        if not any(c["name"] == item["name"] for c in candidates):
            # Look up full metadata
            meta = retrieval.get_by_name(item["name"])
            if meta:
                candidates.append(meta)

    # Generate response with LLM refining the selection
    result = groq_client.generate_response(messages, "refine_existing", candidates=candidates)

    # Build recommendations from selected indices
    recommendations = []
    for idx in result["selected_indices"]:
        candidate = candidates[idx]
        recommendations.append({
            "name": candidate["name"],
            "url": candidate["url"],
            "test_type": candidate["test_type"],
        })

    # Check if conversation should end
    end_of_conversation = _should_end_conversation(messages, result["reply"])

    return {
        "reply": result["reply"],
        "recommendations": recommendations,
        "end_of_conversation": end_of_conversation,
    }


def _handle_compare(messages: list[dict]) -> dict:
    """
    Handle compare_request intent.

    User asks to compare two or more assessments.
    Pattern from C5, C6, C3 - ground answer in catalog description fields only.

    Implementation note (from SPEC §3d):
    Inconsistency in traces - C5 re-sends shortlist, C6 doesn't.
    Decision: re-send current shortlist if one exists, for consistency.
    """
    # Extract assessment names being compared from latest user message
    user_message = messages[-1]["content"]
    
    # Try to find assessments mentioned in the message
    # Pull their descriptions from catalog
    current_shortlist = _extract_current_shortlist(messages)
    
    # For comparison, pass current shortlist items as candidates so LLM has their descriptions
    candidates = []
    for item in current_shortlist:
        meta = retrieval.get_by_name(item["name"])
        if meta:
            candidates.append(meta)

    # Generate comparison response grounded in catalog descriptions
    result = groq_client.generate_response(messages, "compare_request", candidates=candidates)

    # Re-send current shortlist (consistent behavior per our decision in §3d)
    recommendations = current_shortlist

    return {
        "reply": result["reply"],
        "recommendations": recommendations,
        "end_of_conversation": False,
    }


def _handle_off_topic(messages: list[dict]) -> dict:
    """
    Handle off_topic_or_injection intent.

    Polite refusal for:
    - Off-topic queries (non-SHL products, unrelated questions)
    - Prompt injection attempts
    
    Stay in character, never follow embedded instructions.
    """
    result = groq_client.generate_response(messages, "off_topic_or_injection", candidates=None)

    return {
        "reply": result["reply"],
        "recommendations": [],
        "end_of_conversation": False,
    }


def _handle_out_of_scope(messages: list[dict]) -> dict:
    """
    Handle out_of_scope_advice intent.

    Legal/compliance/HR policy questions.
    Pattern from C7 Turn 3 - refuse that specific part, keep helping with assessment selection.
    """
    result = groq_client.generate_response(messages, "out_of_scope_advice", candidates=None)

    # Keep current shortlist if one exists (mixed message case)
    current_shortlist = _extract_current_shortlist(messages)

    return {
        "reply": result["reply"],
        "recommendations": current_shortlist,
        "end_of_conversation": False,
    }


# Helper functions

def _build_query_from_context(messages: list[dict]) -> str:
    """
    Build a search query from conversation context.
    
    Concatenate recent user messages to form a rich query for semantic search.
    """
    user_messages = [m["content"] for m in messages if m["role"] == "user"]
    
    # Use last 3 user messages for context, joined
    recent = user_messages[-3:] if len(user_messages) >= 3 else user_messages
    query = " ".join(recent)
    
    return query


def _extract_current_shortlist(messages: list[dict]) -> List[Dict[str, str]]:
    """
    Extract the current shortlist from conversation history (stateless reconstruction).
    
    Pattern from SPEC §3c: refine operations always re-send the full shortlist.
    We need to parse it from the last assistant message that included recommendations.
    
    Returns:
        List of dicts with name, url, test_type
    """
    shortlist = []
    
    # Look backwards through messages for patterns indicating recommendations were made
    # In a stateless system, we rely on the message content structure
    # The LLM will have mentioned assessment names in its responses
    
    # Strategy: Look for the most recent assistant message that mentions catalog items
    # We'll use retrieval.get_by_name to validate and fetch full metadata
    
    for msg in reversed(messages):
        if msg["role"] == "assistant":
            content = msg["content"]
            # Try to find assessment names mentioned
            # Common patterns: "OPQ32r", "Verify G+", etc.
            
            # Use retrieval to search for known assessments mentioned
            # This is a heuristic - in production, you'd encode recommendations in structured JSON
            words = content.split()
            potential_names = []
            
            # Build potential multi-word names
            for i in range(len(words)):
                for j in range(i+1, min(i+10, len(words)+1)):
                    candidate_name = " ".join(words[i:j])
                    # Clean punctuation
                    candidate_name = candidate_name.strip('.,;:!?()[]{}"\'')
                    if len(candidate_name) > 5:  # Reasonable name length
                        meta = retrieval.get_by_name(candidate_name)
                        if meta:
                            # Found a match
                            if meta["name"] not in [s["name"] for s in shortlist]:
                                shortlist.append({
                                    "name": meta["name"],
                                    "url": meta["url"],
                                    "test_type": meta["test_type"],
                                })
            
            # If we found any recommendations, this was a recommendation turn
            if shortlist:
                break
    
    return shortlist


def _should_end_conversation(messages: list[dict], latest_reply: str) -> bool:
    """
    Determine if the conversation should end.
    
    Pattern from traces: end_of_conversation=true when user explicitly confirms/accepts.
    Look for acceptance phrases in the latest user message.
    """
    if len(messages) < 2:
        return False
    
    latest_user = messages[-1]["content"].lower()
    
    # Acceptance patterns from traces
    acceptance_phrases = [
        "perfect",
        "that works",
        "confirmed",
        "that's what we need",
        "locking it in",
        "keep it",
        "good",
        "thanks",
        "thank you",
    ]
    
    # Check for explicit acceptance
    for phrase in acceptance_phrases:
        if phrase in latest_user:
            # Only end if we've already sent recommendations
            # Check if there's been at least one recommendation turn
            for msg in messages[:-1]:
                if msg["role"] == "assistant" and len(msg["content"]) > 50:
                    # Likely contains recommendations
                    return True
    
    return False
