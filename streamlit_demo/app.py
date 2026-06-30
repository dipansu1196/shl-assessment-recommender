"""
Streamlit Demo Client for SHL Assessment Recommender API.

Thin client that:
- Maintains conversation history in st.session_state
- Calls the /chat endpoint
- Displays agent replies and recommendations in a table
- Allows configuration of API endpoint

Task 10 - Not graded, just for demonstration.
"""

import streamlit as st
import requests
import json
from typing import List, Dict
import os


# Page configuration
st.set_page_config(
    page_title="SHL Assessment Recommender",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)


def initialize_session_state():
    """Initialize Streamlit session state."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_url" not in st.session_state:
        st.session_state.api_url = os.getenv("API_URL", "https://shl-assessment-recommender-0wam.onrender.com")


def get_api_url():
    """Get API URL from session state."""
    return st.session_state.get("api_url", "http://localhost:8000")


def call_chat_api(messages: List[Dict[str, str]]) -> Dict:
    """
    Call the /chat endpoint.
    
    Args:
        messages: Conversation history
        
    Returns:
        Response dict with reply, recommendations, end_of_conversation
    """
    try:
        api_url = get_api_url()
        response = requests.post(
            f"{api_url}/chat",
            json={"messages": messages},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "reply": f"Error: API returned status {response.status_code}",
                "recommendations": [],
                "end_of_conversation": False
            }
    except requests.exceptions.ConnectionError:
        return {
            "reply": f"Error: Could not connect to API at {get_api_url()}. Make sure the server is running.",
            "recommendations": [],
            "end_of_conversation": False
        }
    except Exception as e:
        return {
            "reply": f"Error: {str(e)}",
            "recommendations": [],
            "end_of_conversation": False
        }


def render_recommendations(recommendations: List[Dict]) -> None:
    """Render recommendations as a table."""
    if not recommendations:
        return
    
    st.subheader("Recommendations")
    
    # Create table data
    table_data = []
    for i, rec in enumerate(recommendations, 1):
        table_data.append({
            "#": i,
            "Assessment": rec.get("name", ""),
            "Type": rec.get("test_type", ""),
            "URL": rec.get("url", "")
        })
    
    # Display as columns for better readability
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "#": st.column_config.NumberColumn(width="small"),
            "Assessment": st.column_config.TextColumn(width="large"),
            "Type": st.column_config.TextColumn(width="small"),
            "URL": st.column_config.LinkColumn(width="medium")
        }
    )


def render_chat_history() -> None:
    """Render chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])


def main():
    """Main Streamlit app."""
    # Initialize session state
    initialize_session_state()
    
    # Header
    st.title("🎯 SHL Assessment Recommender")
    st.markdown(
        "Conversational AI assistant for selecting the right SHL assessments for your hiring needs."
    )
    
    # Sidebar: Configuration
    with st.sidebar:
        st.header("Configuration")
        
        # API URL configuration
        st.subheader("API Endpoint")
        api_url_input = st.text_input(
            "API URL",
            value=get_api_url(),
            help="URL of the SHL Assessment Recommender API",
            key="api_url_input"
        )
        
        if api_url_input != get_api_url():
            st.session_state.api_url = api_url_input
            st.success("API URL updated")
        
        st.caption(f"Current: {get_api_url()}")
        
        # Health check
        if st.button("Check Connection", key="health_check"):
            try:
                response = requests.get(f"{get_api_url()}/health", timeout=5)
                if response.status_code == 200:
                    st.success("API is running ✓")
                else:
                    st.error(f"API returned status {response.status_code}")
            except Exception as e:
                st.error(f"Cannot connect: {str(e)}")
        
        st.divider()
        
        # Conversation info
        st.subheader("Conversation Info")
        user_turns = sum(1 for m in st.session_state.messages if m["role"] == "user")
        st.metric("User Turns", user_turns, help="Maximum 8 turns")
        
        if user_turns >= 8:
            st.warning("Maximum 8 turns reached. Conversation will end after the next response.")
        
        # Clear history button
        if st.button("Clear History", key="clear_history"):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        
        # About
        st.subheader("About")
        st.markdown("""
        **Task 10: Streamlit Demo Client**
        
        Thin client for the SHL Assessment Recommender API.
        - Maintains conversation history
        - Displays recommendations in a table
        - Configurable API endpoint
        
        **Quick Start:**
        1. Ensure API is running on localhost:8000
        2. Type a message below
        3. Submit to get recommendations
        """)

    # Main chat interface
    with st.container():
        # Display chat history
        st.subheader("Conversation")
        render_chat_history()
        
        # Input area
        st.divider()
        
        # Chat input
        user_input = st.chat_input(
            "Ask about assessments for your hiring needs...",
            key="user_input"
        )
        
        if user_input:
            # Add user message to history
            st.session_state.messages.append({
                "role": "user",
                "content": user_input
            })
            
            # Display user message
            with st.chat_message("user"):
                st.write(user_input)
            
            # Call API
            with st.spinner("Thinking..."):
                response = call_chat_api(st.session_state.messages)
            
            # Add agent message to history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.get("reply", "")
            })
            
            # Display agent response
            with st.chat_message("assistant"):
                st.write(response.get("reply", ""))
                
                # Display recommendations if present
                recommendations = response.get("recommendations", [])
                if recommendations:
                    render_recommendations(recommendations)
                
                # Show end of conversation info
                if response.get("end_of_conversation", False):
                    st.info("End of conversation reached. Start a new conversation by clearing history.")
            
            # Rerun to update UI
            st.rerun()


if __name__ == "__main__":
    main()
