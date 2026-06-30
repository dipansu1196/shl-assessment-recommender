"""
Test script for FastAPI endpoints.

This tests the API without requiring the full FAISS index to be built.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the /health endpoint."""
    print("Testing GET /health...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("✅ Health check passed\n")

def test_chat_basic():
    """Test the /chat endpoint with a basic request."""
    print("Testing POST /chat with basic request...")
    
    payload = {
        "messages": [
            {"role": "user", "content": "I need help finding assessments for a senior developer role"}
        ]
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "recommendations" in data
    assert "end_of_conversation" in data
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["end_of_conversation"], bool)
    print("✅ Basic chat test passed\n")

def test_chat_turn_limit():
    """Test the 8-turn cap enforcement."""
    print("Testing POST /chat with 8-turn limit...")
    
    # Create 9 messages (9 user turns) to exceed the limit
    messages = []
    for i in range(9):
        messages.append({"role": "user", "content": f"Message {i+1}"})
        if i < 8:  # Add assistant responses for all but the last
            messages.append({"role": "assistant", "content": f"Response {i+1}"})
    
    payload = {"messages": messages}
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Reply: {data['reply'][:100]}...")
    print(f"End of conversation: {data['end_of_conversation']}")
    print()
    
    assert response.status_code == 200
    assert data["end_of_conversation"] is True
    print("✅ Turn limit test passed\n")

def test_chat_malformed():
    """Test malformed request handling."""
    print("Testing POST /chat with malformed request...")
    
    # Missing required field
    payload = {"messages": "not a list"}
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
    assert response.status_code == 422  # Validation error
    print("✅ Malformed request test passed\n")

if __name__ == "__main__":
    print("="*60)
    print("Testing SHL Assessment Recommender API")
    print("="*60)
    print()
    
    # Wait a moment for server to be ready
    print("Waiting for server to be ready...")
    time.sleep(2)
    
    try:
        test_health()
        test_chat_basic()
        test_chat_turn_limit()
        test_chat_malformed()
        
        print("="*60)
        print("All tests passed! ✅")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to server. Is it running on http://localhost:8000?")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
