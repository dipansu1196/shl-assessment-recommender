# Streamlit Demo Client

Thin client for the SHL Assessment Recommender API built with Streamlit.

## Features

- **Chat Interface**: Interactive chat with the API
- **Session State**: Maintains conversation history across interactions
- **Recommendations Table**: Displays recommendations with name, type, and URL
- **API Configuration**: Change API endpoint on the fly
- **Connection Check**: Verify API is running with health check
- **Turn Counter**: Track conversation turns (max 8)
- **Clear History**: Start a new conversation

## Setup

### 1. Install Streamlit

```bash
pip install streamlit
```

Or add to requirements.txt:
```
streamlit>=1.28.0
```

### 2. Start the API Server

In a terminal:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Run the Streamlit App

In another terminal:
```bash
streamlit run streamlit_demo/app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Basic Workflow

1. **Check Connection**: Click "Check Connection" in the sidebar to verify API is running
2. **Type a Message**: Type your question in the chat input
3. **Submit**: Press Enter or click the send button
4. **View Results**: See the agent's reply and any recommendations
5. **Continue**: Type more messages to refine or modify the shortlist

### Changing API Endpoint

1. In the sidebar, under "API Endpoint", edit the URL
2. Click "Check Connection" to verify
3. Continue chatting

### Clear Conversation

- Click "Clear History" in the sidebar to start over
- This resets the message history but keeps the API URL

## Interface Layout

```
[Sidebar]                          [Main Area]
- Configuration                    - Conversation history
  - API URL input                  - User messages
  - Health check button            - Agent replies
  - Conversation info              - Recommendations table
  - Clear history button           - Chat input box
  - About section
```

## API Interaction

The Streamlit app calls the API with the following contract:

**Request**:
```json
POST /chat
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Response**:
```json
{
  "reply": "Agent response text",
  "recommendations": [
    {"name": "Assessment Name", "url": "https://...", "test_type": "K"},
    ...
  ],
  "end_of_conversation": false
}
```

## Session State

Streamlit maintains conversation state in `st.session_state`:

- `messages`: List of {"role": ..., "content": ...} dicts
- `api_url`: Current API endpoint URL

This persists across interactions within a session but resets when the app restarts.

## Error Handling

- **Connection Error**: Shows message if API is unreachable
- **API Error**: Displays HTTP error status
- **Invalid Response**: Shows error message to user

## Recommendations Display

Recommendations are displayed as a Streamlit dataframe table with:
- `#`: Row number
- `Assessment`: Full assessment name (sortable)
- `Type`: Single-letter code (K, P, A, S, B, C, D)
- `URL`: Clickable link to SHL product page

## Configuration

### Environment Variables

```bash
export API_URL=http://localhost:8000
streamlit run streamlit_demo/app.py
```

Or set in the UI directly.

### Streamlit Config

To customize Streamlit behavior, create `.streamlit/config.toml`:

```toml
[client]
showErrorDetails = false

[server]
port = 8501
```

## Deployment

### Local Development

```bash
streamlit run streamlit_demo/app.py
```

### Hugging Face Spaces

1. Create a repository at https://huggingface.co/spaces
2. Select "Streamlit" as the SDK
3. Add files: `app.py`, `requirements.txt`
4. Set `API_URL` environment variable to deployed API URL

## Troubleshooting

### "API not found"
- Ensure FastAPI server is running
- Check port 8000 is not in use
- Verify API URL in sidebar

### "Connection refused"
- Start the API server: `python -m uvicorn app.main:app --port 8000`
- Check firewall settings

### "Recommendations not showing"
- Verify API returned recommendations (check reply for message)
- Check browser console for errors (F12)

### "History cleared"
- This is normal when app restarts
- Use "Clear History" button to intentionally clear

## Performance

- **First load**: ~2-3 seconds (Streamlit startup)
- **Per message**: ~2-3 seconds (API inference)
- **UI responsiveness**: Instant

## Limitations

- Single user (no multi-user state management)
- No persistence (history lost on app restart)
- No authentication
- Max 8 turns enforced by API

## Future Enhancements (Not Implemented)

- Persistent history (database or file)
- User authentication
- Export conversation to PDF
- Evaluation dashboard
- Multi-turn analytics
- Conversation replay

## Notes

- This is a demo client - not graded
- The API (Task 7) is what's evaluated
- Streamlit is for demonstration purposes only
- Production UI would use different framework (React, Vue, etc.)
