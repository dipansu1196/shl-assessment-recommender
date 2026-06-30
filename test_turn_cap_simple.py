"""
Simple test script to verify turn cap forces recommendations.
Doesn't require pytest - can run directly with python.
"""

import sys
from unittest.mock import patch, MagicMock

# Add app to path
sys.path.insert(0, 'd:\\SHL Assignment')

from app.conversation import handle_turn


def test_turn_cap_forces_recommendation():
    """
    Test that when turn cap (7-8) is reached without a shortlist,
    the system forces a recommendation instead of returning empty array.
    """
    print("Testing turn cap forcing recommendation...")
    
    # Setup mocks
    with patch('app.conversation.groq_client') as mock_groq, \
         patch('app.conversation.retrieval') as mock_retrieval:
        
        # First 7 turns: classify as clarify_needed (vague conversation)
        mock_groq.classify_intent.return_value = "clarify_needed"
        
        # On turn 8 (forced), should switch to recommend
        mock_groq.generate_response.return_value = {
            "reply": "Based on what you've told me, here are some general recommendations:",
            "selected_indices": [0, 1, 2, 3, 4]  # Force top 5
        }
        
        mock_retrieval.search.return_value = [
            {
                "name": "SHL Verify Interactive G+",
                "url": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/",
                "test_type": "A",
                "description": "General reasoning test...",
                "score": 0.90
            },
            {
                "name": "Occupational Personality Questionnaire OPQ32r",
                "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
                "test_type": "P",
                "description": "Personality questionnaire...",
                "score": 0.88
            },
            {
                "name": "Graduate Scenarios",
                "url": "https://www.shl.com/products/product-catalog/view/graduate-scenarios/",
                "test_type": "B",
                "description": "Situational judgment...",
                "score": 0.85
            },
            {
                "name": "Financial Accounting (New)",
                "url": "https://www.shl.com/products/product-catalog/view/financial-accounting-new/",
                "test_type": "K",
                "description": "Finance knowledge...",
                "score": 0.82
            },
            {
                "name": "Core Java (Advanced Level) (New)",
                "url": "https://www.shl.com/products/product-catalog/view/core-java-advanced-level-new/",
                "test_type": "K",
                "description": "Java programming...",
                "score": 0.80
            }
        ]
        
        # Important: Mock get_by_name to return None (no existing shortlist in these messages)
        mock_retrieval.get_by_name.return_value = None

        # Simulate an 8-turn conversation that never converges
        messages = [
            {"role": "user", "content": "I need assessments."},
            {"role": "assistant", "content": "What role?"},
            {"role": "user", "content": "Developers."},
            {"role": "assistant", "content": "What level?"},
            {"role": "user", "content": "Senior."},
            {"role": "assistant", "content": "What technology stack?"},
            {"role": "user", "content": "General."},
            {"role": "assistant", "content": "Any specific skills?"},
            {"role": "user", "content": "Just general."},
            {"role": "assistant", "content": "What about personality tests?"},
            {"role": "user", "content": "Maybe."},
            {"role": "assistant", "content": "What's your priority?"},
            {"role": "user", "content": "Not sure."},
            {"role": "assistant", "content": "Let me know when you're ready."},
            # Turn 8: Should force recommendation
            {"role": "user", "content": "Recommend something now."}
        ]
        
        # Call with turn_number=8 to trigger force
        result = handle_turn(messages, turn_number=8)

        # CRITICAL ASSERTION: Must return non-empty recommendations
        print(f"Result: {len(result['recommendations'])} recommendations")
        
        if len(result["recommendations"]) < 1:
            print("FAILED: Turn cap reached without shortlist - must force recommendation, not return empty array")
            print(f"Debug - Intent classified as: {mock_groq.classify_intent.return_value}")
            print(f"Debug - Generate response called with action: {mock_groq.generate_response.call_args}")
            return False
        
        if len(result["recommendations"]) > 10:
            print("FAILED: Must not exceed max 10 recommendations")
            return False
        
        # Verify all recommendations have required fields
        for rec in result["recommendations"]:
            if "name" not in rec:
                print(f"FAILED: Missing 'name' in recommendation: {rec}")
                return False
            if "url" not in rec:
                print(f"FAILED: Missing 'url' in recommendation: {rec}")
                return False
            if "test_type" not in rec:
                print(f"FAILED: Missing 'test_type' in recommendation: {rec}")
                return False
            if not rec["url"].startswith("https://www.shl.com/"):
                print(f"FAILED: Invalid URL in recommendation: {rec['url']}")
                return False
        
        # Should have called retrieval to get candidates
        if not mock_retrieval.search.called:
            print("FAILED: Retrieval was not called")
            return False
        
        print(f"PASSED: Forced recommendation returned {len(result['recommendations'])} valid assessments")
        print("Recommendations:")
        for i, rec in enumerate(result["recommendations"], 1):
            print(f"  {i}. {rec['name']} ({rec['test_type']})")
        
        return True


if __name__ == "__main__":
    try:
        success = test_turn_cap_forces_recommendation()
        if success:
            print("\nALL TESTS PASSED")
            sys.exit(0)
        else:
            print("\nTEST FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"\nTEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
