"""
Task 8 Evaluation Harness - Demonstration

This demonstrates how the evaluation harness works with the actual traces
and API calls. Due to catalog JSON encoding issues, we show the expected
flow with sample data.
"""

import requests
import json
from typing import List, Dict, Tuple
from pathlib import Path

# Sample expected results for demonstration
SAMPLE_TRACES = {
    "C1": {
        "expected": [
            {"name": "Occupational Personality Questionnaire OPQ32r", "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/", "test_type": "P"},
            {"name": "OPQ Universal Competency Report 2.0", "url": "https://www.shl.com/products/product-catalog/view/opq-universal-competency-report-2-0/", "test_type": "P"},
            {"name": "OPQ Leadership Report", "url": "https://www.shl.com/products/product-catalog/view/opq-leadership-report/", "test_type": "P"}
        ],
        "turns": 4
    },
    "C2": {
        "expected": [
            {"name": "Smart Interview Live Coding", "url": "https://www.shl.com/products/product-catalog/view/smart-interview-live-coding/", "test_type": "K"},
            {"name": "Linux Programming (General)", "url": "https://www.shl.com/products/product-catalog/view/linux-programming-general/", "test_type": "K"},
            {"name": "Networking and Implementation (New)", "url": "https://www.shl.com/products/product-catalog/view/networking-and-implementation-new/", "test_type": "K"},
            {"name": "SHL Verify Interactive G+", "url": "https://www.shl.com/products/product-catalog/view/shl-verify-interactive-g/", "test_type": "A"},
            {"name": "Occupational Personality Questionnaire OPQ32r", "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/", "test_type": "P"}
        ],
        "turns": 3
    },
    "C3": {
        "expected": [
            {"name": "SVAR Spoken English (US) (New)", "url": "https://www.shl.com/products/product-catalog/view/svar-spoken-english-us-new/", "test_type": "K"},
            {"name": "Contact Center Call Simulation (New)", "url": "https://www.shl.com/products/product-catalog/view/contact-center-call-simulation-new/", "test_type": "S"},
            {"name": "Entry Level Customer Serv - Retail & Contact Center", "url": "https://www.shl.com/products/product-catalog/view/entry-level-customer-serv-retail-and-contact-center/", "test_type": "P"},
            {"name": "Customer Service Phone Simulation", "url": "https://www.shl.com/products/product-catalog/view/customer-service-phone-simulation/", "test_type": "B"}
        ],
        "turns": 5
    },
}

API_URL = "http://localhost:8000"


def compute_recall_at_10(predicted: List[Dict[str, str]], expected: List[Dict[str, str]]) -> float:
    """
    Compute Recall@10 between predicted and expected recommendations.
    
    Recall = |intersection| / |expected|
    Matching by name (case-insensitive)
    """
    if not expected:
        return 1.0 if not predicted else 0.0
    
    predicted_names = {rec["name"].lower().strip() for rec in predicted}
    expected_names = {rec["name"].lower().strip() for rec in expected}
    
    intersection = predicted_names & expected_names
    recall = len(intersection) / len(expected)
    
    return recall


def test_api_connectivity():
    """Test that the API is running."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("[OK] API is running at http://localhost:8000")
            return True
        else:
            print(f"[ERROR] API returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Cannot connect to API: {e}")
        print("Start the server with: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return False


def demonstrate_trace_replay(trace_id: str, num_turns: int):
    """
    Demonstrate how a trace would be replayed against the API.
    """
    print(f"\n{'='*70}")
    print(f"Trace: {trace_id} ({num_turns} turns)")
    print(f"{'='*70}")
    
    # For demonstration, we'll show the expected flow
    # In real execution, we'd parse actual traces and call the API
    
    print("\nExpected Flow:")
    print(f"1. Parse trace file: {trace_id}.md")
    print(f"2. Extract {num_turns} conversation turns")
    print(f"3. For each user turn:")
    print(f"   - Send POST /chat with full message history")
    print(f"   - Receive ChatResponse with recommendations")
    print(f"   - Accumulate into conversation history")
    print(f"4. After final turn, compute Recall@10 against expected shortlist")
    
    expected = SAMPLE_TRACES[trace_id]["expected"]
    print(f"\nExpected Recommendations ({len(expected)}):")
    for rec in expected:
        print(f"  ✓ {rec['name']} ({rec['test_type']})")
    
    # In real evaluation, we'd call the API here
    # result = requests.post(API_URL + "/chat", json={"messages": [...]})
    # predictions = result.json()["recommendations"]
    # recall = compute_recall_at_10(predictions, expected)
    
    print(f"\n[In real evaluation, API would be called here]")
    print(f"Example: recall would be computed as intersection/expected_count")


def print_evaluation_summary():
    """Print summary of how Task 8 evaluation works."""
    print("\n" + "="*70)
    print("TASK 8: EVALUATION HARNESS STRUCTURE")
    print("="*70)
    
    print("""
The evaluation harness (Task 8) consists of two components:

1. PARSE_TRACES (eval/parse_traces.py)
   - Load C1.md through C10.md from GenAI_SampleConversations/
   - Extract conversation turns (user, assistant messages)
   - Parse final recommendation tables into structured data
   - Return: List[turns], List[expected_recommendations]

2. REPLAY_HARNESS (eval/replay_harness.py)
   - For each trace:
     a) Replay user turns against http://localhost:8000/chat
     b) Build conversation history incrementally (stateless)
     c) Feed full history to API on each call
     d) Collect final predictions from last turn
     e) Compute Recall@10 = |intersection| / |expected|
   - Print per-trace recall and mean recall
   - Identify low performers

RECALL@10 METRIC:
   - Match recommendations by name (case-insensitive)
   - Intersection = recommendations in both predicted and expected
   - Recall = |intersection| / |expected|
   - Range: 0.0 (no matches) to 1.0 (perfect match)

EXAMPLE TRACES (10 total):
    """)
    
    for trace_id in sorted(SAMPLE_TRACES.keys()):
        info = SAMPLE_TRACES[trace_id]
        print(f"  {trace_id}: {info['turns']} turns, {len(info['expected'])} expected items")


def main():
    """Main evaluation flow."""
    print("\n" + "="*70)
    print("SHL Assessment Recommender - Task 8 Evaluation")
    print("="*70)
    
    # Check API connectivity
    if not test_api_connectivity():
        print("\nEvaluation harness requires running API.")
        print("Use: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return
    
    # Show structure
    print_evaluation_summary()
    
    # Demonstrate trace replay
    print("\nDEMONSTRATION:")
    for trace_id in ["C1", "C2", "C3"]:
        demonstrate_trace_replay(trace_id, SAMPLE_TRACES[trace_id]["turns"])
    
    print("\n" + "="*70)
    print("RUNNING FULL EVALUATION")
    print("="*70)
    print("""
To run the full evaluation harness with actual traces:

1. First, ensure the catalog is valid (fix encoding if needed):
   python clean_catalog.py

2. Build the FAISS index:
   cd data && python build_index.py

3. Start the API server:
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

4. Run the evaluation harness:
   python eval/replay_harness.py

Expected output will include:
- Per-trace Recall@10 scores
- Mean Recall@10 across all traces
- Analysis of which items were matched/missed
- Identification of low-performing traces
    """)


if __name__ == "__main__":
    main()
