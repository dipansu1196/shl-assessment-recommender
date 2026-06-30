# Quick Start Guide

## 5-Minute Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add Groq API key
```bash
# Edit .env (already configured for you)
# Verify: GROQ_API_KEY=gsk_your_actual_key_here
```

### 3. Build index (if not done)
```bash
cd data && python build_index.py
cd ..
```

### 4. Start the API server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 5. In another terminal, test it
```bash
# Health check
curl -X GET http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need assessments for senior Java developers"}]}'
```

### 6. Open interactive docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Common Commands

### Run unit tests
```bash
pytest tests/ -v
```

### Run evaluation harness
```bash
python eval/replay_harness.py
```

### Run demo (no full index needed)
```bash
python eval/demo_harness.py
```

### View API logs
The server outputs logs showing:
- All requests and responses
- Inference times
- Error details
- Turn counts

### Stop the server
Press `Ctrl+C` in the terminal running uvicorn

---

## Example Conversations

### Single-turn (clarification needed)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "We need assessments"}]}'
```

Expected: Agent asks clarifying question, no recommendations

### Multi-turn (converging on shortlist)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Senior Java developers"},
      {"role": "assistant", "content": "What seniority level?"},
      {"role": "user", "content": "5+ years, need cognitive tests"}
    ]
  }'
```

Expected: Agent returns 1-10 recommendations with names, URLs, test types

### Turn limit (8+ turns)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "msg1"},
      {"role": "assistant", "content": "resp1"},
      ...
      {"role": "user", "content": "msg9"}
    ]
  }'
```

Expected: Graceful wrap-up, end_of_conversation=true

### Validation error (malformed request)
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": "not an array"}'
```

Expected: 422 error with validation details

---

## Troubleshooting

### "Cannot connect to http://localhost:8000"
- Make sure server is running: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Check port 8000 is not in use: `netstat -an | findstr :8000`
- Try `http://127.0.0.1:8000` instead of `localhost`

### "ModuleNotFoundError: No module named 'faiss'"
- Install: `pip install faiss-cpu`
- Or full requirements: `pip install -r requirements.txt`

### "GROQ_API_KEY not found"
- Check .env file exists in project root
- Verify it contains: `GROQ_API_KEY=gsk_...`
- Check .env is not in .gitignore (it should be)

### "JSONDecodeError: Invalid control character"
- Catalog file has encoding issues
- Run: `python clean_catalog.py`
- Rebuild index: `cd data && python build_index.py`

### "No such file: catalog.faiss"
- Index not built yet
- Run: `cd data && python build_index.py`
- Takes 2-5 minutes first time

### "Turn limit exceeded" message
- This is intentional - conversation ended gracefully
- Max 8 user turns to prevent infinite loops
- Start new conversation for next batch of questions

---

## Project Structure

```
d:\SHL Assignment\
├── app/                    # Main application code
│   ├── main.py            # FastAPI app
│   ├── conversation.py    # State machine
│   ├── groq_client.py     # LLM integration
│   ├── retrieval.py       # Vector search
│   └── schemas.py         # Data models
├── data/
│   ├── build_index.py     # Index builder
│   ├── catalog.json       # SHL catalog
│   ├── catalog.faiss      # Vector index
│   └── catalog_meta.pkl   # Metadata
├── eval/                  # Evaluation harness
│   ├── parse_traces.py    # Parse traces
│   ├── replay_harness.py  # Replay traces
│   └── demo_harness.py    # Demo mode
├── tests/                 # Unit tests
│   ├── test_conversation.py
│   ├── test_retrieval.py
│   └── test_schemas.py
├── GenAI_SampleConversations/  # 10 test traces
├── .env                   # API key (gitignored)
├── requirements.txt       # Dependencies
└── README.md             # Full setup guide
```

---

## Key Concepts

### Stateless
Every API call is independent - all context is in the message history. This enables:
- Horizontal scaling (no session DB)
- Easy deployment (no state to sync)
- Replay testing (deterministic given history)

### Intent Classification
The API detects what the user wants:
- **clarify_needed**: Ask one question
- **ready_to_recommend**: Show 1-10 assessments
- **refine_existing**: Modify shortlist
- **compare_request**: Explain differences
- **off_topic_or_injection**: Polite refusal
- **out_of_scope_advice**: Refuse legal/HR questions

### Semantic Search
Finds relevant assessments by meaning, not keywords:
- Converts queries to embeddings (sentence-transformers)
- Searches FAISS index for similar assessments
- Returns top-15 candidates for LLM to select from

### Hallucination Prevention
LLM only selects from retrieved candidates by index:
- Never free-generates assessment names
- Never constructs URLs
- Only passes through catalog data

---

## Performance Notes

- **Cold start**: ~30s (FAISS index loads once at startup)
- **Per-request**: ~2-3s (embedding + search + LLM inference)
- **Max timeout**: 30s per request
- **Max conversation**: 8 user turns

---

## Next Steps

1. **Verify everything works**: Run the test commands above
2. **Explore the code**: Start with app/main.py, then conversation.py
3. **Try different queries**: Use Swagger UI at /docs
4. **Run evaluation**: `python eval/replay_harness.py`
5. **Check logs**: Watch the server output for insights

---

Good luck! 🚀
