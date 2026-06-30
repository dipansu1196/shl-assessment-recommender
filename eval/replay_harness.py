"""
Replay conversation traces against a running API and compute Recall@10.

For each trace:
1. Extract turns from parsed fixture
2. Replay user turns against http://localhost:8000/chat
3. Feed back full conversation history (stateless contract)
4. After final turn, compute Recall@10 against expected shortlist

Recall@10 = intersection(predicted, expected) / len(expected)
where match is case-insensitive by name
"""

import requests
import json
from typing import List, Dict, Tuple, Set
from pathlib import Path
from eval.parse_traces import load_all_traces


API_BASE_URL = "http://localhost:8000"


def compute_recall_at_10(predicted: List[Dict[str, str]], expected: List[Dict[str, str]]) -> float:
    """
    Compute Recall@10 between predicted and expected recommendations.
    
    Recall = |intersection| / |expected|
    Matching by name (case-insensitive)
    
    Args:
        predicted: List of recommendations from API (max 10 items)
        expected: List of expected recommendations from trace
        
    Returns:
        Recall score (0.0 to 1.0)
    """
    if not expected:
        # If no expected recommendations, perfect score if we didn't recommend
        return 1.0 if not predicted else 0.0
    
    # Normalize names for comparison
    predicted_names = {rec["name"].lower().strip() for rec in predicted}
    expected_names = {rec["name"].lower().strip() for rec in expected}
    
    # Compute intersection
    intersection = predicted_names & expected_names
    
    # Recall = |intersection| / |expected|
    recall = len(intersection) / len(expected)
    
    return recall


def replay_trace(trace_id: str, turns: List[Dict[str, str]], expected: List[Dict[str, str]]) -> Tuple[float, str]:
    """
    Replay a single trace against the API.
    
    Args:
        trace_id: Trace identifier (e.g., "C1")
        turns: List of turn dicts with "role" and "content"
        expected: Expected recommendations for this trace
        
    Returns:
        (recall_score, analysis_string)
    """
    messages = []
    final_predictions = []
    analysis = []
    
    analysis.append(f"\n{'='*70}")
    analysis.append(f"Trace: {trace_id}")
    analysis.append(f"Expected recommendations: {len(expected)}")
    for rec in expected:
        analysis.append(f"  ✓ {rec['name']} ({rec['test_type']})")
    analysis.append("")
    
    # Replay each user turn, feeding back the full conversation history
    user_turn_count = 0
    for i, turn in enumerate(turns):
        if turn["role"] == "user":
            user_turn_count += 1
            analysis.append(f"Turn {user_turn_count}: User > {turn['content'][:70]}")
            
            # Add user message to conversation history
            messages.append({
                "role": "user",
                "content": turn["content"]
            })
        else:
            # Agent turn - call API with full message history
            try:
                response = requests.post(
                    f"{API_BASE_URL}/chat",
                    json={"messages": messages},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract predictions from this turn
                    predictions = result.get("recommendations", [])
                    final_predictions = predictions  # Keep updating to get final
                    
                    reply_preview = result.get("reply", "")[:70].replace("\n", " ")
                    analysis.append(f"         Agent > {reply_preview}")
                    analysis.append(f"         Predictions: {len(predictions)} items")
                    
                    for rec in predictions:
                        analysis.append(f"           - {rec['name']} ({rec['test_type']})")
                    
                    # Add agent response to history for next turn
                    messages.append({
                        "role": "assistant",
                        "content": result.get("reply", "")
                    })
                else:
                    analysis.append(f"         ✗ API Error: {response.status_code}")
                    return 0.0, "\n".join(analysis)
                    
            except requests.exceptions.RequestException as e:
                analysis.append(f"         ✗ Connection Error: {str(e)}")
                return 0.0, "\n".join(analysis)
    
    # Compute Recall@10
    recall = compute_recall_at_10(final_predictions, expected)
    
    analysis.append("")
    analysis.append(f"Final Predictions ({len(final_predictions)}):")
    predicted_names = set()
    for rec in final_predictions:
        analysis.append(f"  {rec['name']} ({rec['test_type']})")
        predicted_names.add(rec["name"].lower().strip())
    
    expected_names = {rec["name"].lower().strip() for rec in expected}
    intersection = predicted_names & expected_names
    
    analysis.append("")
    analysis.append(f"Recall@10: {recall:.2%}")
    analysis.append(f"  Matched: {len(intersection)}/{len(expected)}")
    
    if intersection:
        analysis.append("  Correct:")
        for name in sorted(intersection):
            analysis.append(f"    ✓ {name}")
    
    missed = expected_names - predicted_names
    if missed:
        analysis.append("  Missed:")
        for name in sorted(missed):
            analysis.append(f"    ✗ {name}")
    
    analysis.append(f"{'='*70}")
    
    return recall, "\n".join(analysis)


def run_harness(api_url: str = API_BASE_URL) -> Dict[str, float]:
    """
    Run the full evaluation harness against a running API.
    
    Args:
        api_url: Base URL of the API (default: http://localhost:8000)
        
    Returns:
        Dict mapping trace_id to recall score
    """
    global API_BASE_URL
    API_BASE_URL = api_url
    
    print("Loading traces...")
    traces = load_all_traces()
    
    if not traces:
        print("✗ No traces loaded")
        return {}
    
    print(f"\nReplaying {len(traces)} traces against {api_url}")
    print("This may take a minute...\n")
    
    results = {}
    analysis_results = []
    
    for trace_id in sorted(traces.keys()):
        turns, expected = traces[trace_id]
        recall, analysis = replay_trace(trace_id, turns, expected)
        results[trace_id] = recall
        analysis_results.append(analysis)
    
    # Print all analysis
    for analysis in analysis_results:
        print(analysis)
    
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")
    
    recalls = list(results.values())
    mean_recall = sum(recalls) / len(recalls) if recalls else 0
    
    for trace_id in sorted(results.keys()):
        recall = results[trace_id]
        status = "✓" if recall >= 0.8 else "⚠" if recall >= 0.5 else "✗"
        print(f"{status} {trace_id}: {recall:.2%}")
    
    print(f"\nMean Recall@10: {mean_recall:.2%}")
    
    # Identify low performers
    low_performers = {tid: recall for tid, recall in results.items() if recall < 0.8}
    if low_performers:
        print(f"\nLow performers (< 80%):")
        for trace_id in sorted(low_performers.keys()):
            print(f"  - {trace_id}: {low_performers[trace_id]:.2%}")
    
    return results


if __name__ == "__main__":
    import sys
    
    api_url = sys.argv[1] if len(sys.argv) > 1 else API_BASE_URL
    
    print(f"Testing API at: {api_url}")
    print("Make sure the server is running: python -m uvicorn app.main:app --port 8000\n")
    
    try:
        # Test connectivity
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is running\n")
        else:
            print(f"✗ API returned status {response.status_code}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to API: {e}")
        print(f"Start the server with: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Run harness
    results = run_harness(api_url)
