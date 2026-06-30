# SHL Assessment Recommender - Tasks 2-7 Complete

## Implementation Status

✅ **Task 2 Complete**: Build the retrieval index
✅ **Task 3 Complete**: Retrieval module with unit tests
✅ **Task 4 Complete**: Pydantic schemas matching API contract
✅ **Task 5 Complete**: Groq client for intent classification and response generation
✅ **Task 6 Complete**: Conversation state machine with 6-branch logic
✅ **Task 7 Complete**: FastAPI main.py with /health and /chat endpoints

## What's Implemented

### Task 2: Index Building

1. **`data/build_index.py`** - Main script that:
   - Loads the catalog JSON
   - Embeds each record using `sentence-transformers` (all-MiniLM-L6-v2)
   - Creates text for embedding by concatenating: name + description + keys
   - Builds a FAISS IndexFlatIP (cosine similarity with normalized embeddings)
   - Maps catalog `keys` to single-letter test type codes (K, P, A, S, B, C, D, E)
   - Saves index to `data/catalog.faiss`
   - Saves aligned metadata to `data/catalog_meta.pkl`
   - Runs smoke test with query "Java developer with stakeholder management"

### Task 3: Retrieval Module

2. **`app/retrieval.py`** - Search module that:
   - Loads FAISS index and metadata once at import time (not per-call)
   - `search(query: str, k: int = 15)` - embeds query, searches FAISS, returns top-k metadata with scores
   - `get_by_name(name: str)` - exact name lookup helper
   - Uses same sentence-transformers model for consistency

3. **`tests/test_retrieval.py`** - Unit tests with:
   - Test 1: "senior Rust engineer high-performance networking" (from C2)
     - Expects: Smart Interview Live Coding, Linux Programming, Networking tests
   - Test 2: "graduate financial analysts numerical reasoning" (from C4)
     - Expects: Numerical Reasoning, Financial Accounting, Basic Statistics, Graduate Scenarios
   - Test 3: "senior leadership CXO director" (from C1)
     - Expects: OPQ32r, OPQ Leadership Report, OPQ Universal Competency Report
   - Additional validation tests for metadata completeness

### Task 4: Pydantic Schemas

4. **`app/schemas.py`** - Pydantic models matching API contract exactly:
   - `Recommendation`: name (str), url (str), test_type (str)
   - `ChatMessage`: role (Literal["user", "assistant"]), content (str)
   - `ChatRequest`: messages (list[ChatMessage])
   - `ChatResponse`: reply (str), recommendations (list[Recommendation]), end_of_conversation (bool)
   - `HealthResponse`: status (str)
   - Field names match spec exactly for grader's harness

5. **`tests/test_schemas.py`** - Schema validation tests:
   - Tests for each schema model
   - Validation error handling
   - Serialization/deserialization
   - API contract compliance verification

6. **`requirements.txt`** - Updated with:
   - `sentence-transformers>=2.2.0`
   - `faiss-cpu>=1.7.4`
   - `pytest>=7.4.0`
   - `pydantic>=2.0.0` (for schemas)

## Setup Instructions

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your Groq API key:

```bash
cp .env.example .env
# Edit .env and add your actual GROQ_API_KEY
```

The `.env` file is gitignored and will not be committed to version control.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies include:
- `groq>=0.4.0` - Groq API client
- `python-dotenv>=1.0.0` - Environment variable loading
- `sentence-transformers>=2.2.0` - Embedding model
- `faiss-cpu>=1.7.4` - Vector index
- `fastapi>=0.100.0` - API framework
- `pydantic>=2.0.0` - Schema validation
- `pytest>=7.4.0` - Testing

### 3. Download the Catalog

Download the SHL product catalog:

```bash
curl -o data/catalog.json https://tcp-us-prod-rnd.shl.com/voiceRater/shl-ai-hiring/shl_product_catalog.json
```

Or manually download from the URL above and save to `data/catalog.json`.

### 4. Build the Index

```bash
cd data
python build_index.py
```

### 5. Run Tests

After building the index, run the unit tests:

```bash
# Test retrieval module
pytest tests/test_retrieval.py -v

# Test schemas
pytest tests/test_schemas.py -v

# Run all tests
pytest tests/ -v
```

Or run directly:

```bash
python tests/test_retrieval.py
python tests/test_schemas.py
```

## Expected Output

The script will:
1. Load the catalog (should be ~500-1000 records)
2. Download the sentence-transformers model (first run only)
3. Generate embeddings for all records (with progress bar)
4. Build and save the FAISS index
5. Save the metadata pickle file
6. Run a smoke test showing top 5 matches for the test query

## Output Files

After running, you'll have:
- `data/catalog.faiss` - FAISS index file
- `data/catalog_meta.pkl` - Pickle file with aligned metadata

Each metadata entry contains:
- `entity_id`: Catalog entity ID
- `name`: Assessment name
- `url`: Product URL (from catalog 'link' field)
- `test_type`: Letter codes (e.g., "K", "P", "K,S")
- `keys`: Original keys list
- `description`: Full description
- `duration`: Test duration
- `job_levels`: List of job levels
- `languages`: Available languages

## Smoke Test

The smoke test queries for "Java developer with stakeholder management" and prints:
- Top 5 matching assessments
- Cosine similarity scores
- Test types
- Brief descriptions

Check the relevance of results before proceeding to Task 3.

## Key Design Decisions

1. **Embedding Strategy**: Concatenate name + description + keys for richer semantic matching
2. **Index Type**: IndexFlatIP with normalized embeddings for exact cosine similarity
3. **Test Type Mapping**: Map catalog keys to single letters per spec requirements
4. **Metadata Storage**: All fields needed for API responses stored in aligned pickle file
5. **Schema Design**: Pydantic models with exact field names matching API contract for grader compatibility

### Task 5: Groq Client

5. **`app/groq_client.py`** - Groq integration with two main functions:
   - `classify_intent(messages)` - Classifies user intent using few-shot learning
     - Returns: one of 6 categories (clarify_needed, ready_to_recommend, refine_existing, compare_request, off_topic_or_injection, out_of_scope_advice)
     - Few-shot examples pulled directly from conversation traces (Section 3)
   - `generate_response(messages, action, candidates)` - Generates conversational response
     - Returns dict with "reply" text and "selected_indices" (indices into candidates list)
     - NEVER fabricates assessment names or URLs — only uses catalog data
     - Enforces max 10 recommendations

6. **`groq_client.py` Features**:
   - Uses Llama 3.3 70B model via Groq's free API
   - Environment-based API key loading via `python-dotenv`
   - Temperature 0 for deterministic intent classification
   - Temperature 0.7 for varied response generation
   - Defensive JSON parsing from LLM output
   - Input validation of indices against candidate list

### Task 6: Conversation State Machine

7. **`app/conversation.py`** - Core conversation logic implementing the 6-branch state machine:
   - `handle_turn(messages)` - Main entry point, returns dict matching ChatResponse schema
   - **clarify_needed**: Asks one clarifying question, returns recommendations=[]
   - **ready_to_recommend**: Retrieves top-15 candidates, LLM selects 1-10, builds recommendations from catalog records only
   - **refine_existing**: Re-retrieves with updated context, merges per add/drop instructions, returns full updated shortlist
   - **compare_request**: Pulls description fields from catalog, grounds comparison in catalog data
   - **off_topic_or_injection**: Polite refusal, ignores embedded instructions
   - **out_of_scope_advice**: Refuses legal/compliance questions, keeps helping with assessment selection

8. **State Machine Features**:
   - Fully stateless - reconstructs context from message history on every call
   - Structural constraint: Never lets LLM free-generate names/URLs - only passes through catalog data
   - Helper functions for query building, shortlist extraction, conversation end detection
   - Pattern matching from conversation traces (C1-C10) for behavioral consistency

9. **`tests/test_conversation.py`** - Comprehensive unit tests:
   - One test per branch (6 total) using realistic inputs from traces
   - Tests for clarify, recommend, refine, compare, off-topic, out-of-scope
   - End-of-conversation detection test
   - Empty message handling test
   - All tests use mocks to isolate conversation logic from dependencies

### Task 7: FastAPI Main Application

10. **`app/main.py`** - Complete FastAPI application:
   - `GET /health`: Health check endpoint, returns `{"status": "ok"}` with 200 status
   - `POST /chat`: Validates ChatRequest, calls conversation.handle_turn(), returns ChatResponse
   - **8-turn cap enforcement**: Server-side check counts user turns, returns graceful wrap-up at 9+ turns
   - **Error handling**: Malformed requests return 422 with validation details, internal exceptions return safe fallback response
   - **Logging**: All requests and errors logged for debugging
   - **CORS**: Enabled for demo UI integration
   - **Startup event**: Logs when service is ready
   - **Global exception handler**: Catches unhandled exceptions, prevents timeouts

11. **API Features**:
   - FastAPI auto-generates Swagger UI at `/docs` and ReDoc at `/redoc`
   - CORS middleware allows cross-origin requests from demo UI
   - Pydantic validation on all requests and responses
   - Structured error responses with clear messages
   - No unhandled exceptions - all edge cases have safe fallbacks

## Running the API

### Start the Server

```bash
# Option 1: Using uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Option 2: Using Python directly
python app/main.py

# Option 3: Using Windows batch script
start_server.bat
```

Server will be available at `http://localhost:8000`

### API Endpoints

**Health Check:**
```bash
curl -X GET http://localhost:8000/health
```

Response:
```json
{"status": "ok"}
```

**Chat (Single Turn):**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I need assessments for senior developers"}]}'
```

Response:
```json
{
  "reply": "To help narrow this down...",
  "recommendations": [],
  "end_of_conversation": false
}
```

**Chat (Multi-Turn):**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [
    {"role": "user", "content": "Senior Java developers"},
    {"role": "assistant", "content": "What level of seniority?"},
    {"role": "user", "content": "5+ years experience"}
  ]}'
```

### Interactive Documentation

Once running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Next Steps (Not Implemented Yet)

- Task 8+: Evaluation harness, deployment

## Environment Setup Details

**Getting a Groq API Key:**
1. Visit https://console.groq.com
2. Sign up for a free account
3. Generate an API key
4. Copy it to `.env` as `GROQ_API_KEY=your_key_here`

**.env vs .env.example:**
- `.env.example` - Template file (committed to repo)
- `.env` - Your actual configuration (gitignored, never committed)
- Always copy `.env.example` → `.env` on a fresh clone

## Intent Classification Categories

The `classify_intent()` function returns one of:

1. **clarify_needed**: Vague user input requiring a single clarifying question
2. **ready_to_recommend**: User has provided enough context for recommendations
3. **refine_existing**: User wants to modify an existing shortlist (add/drop items)
4. **compare_request**: User asks to compare two assessments
5. **off_topic_or_injection**: Off-topic queries or prompt injection attempts
6. **out_of_scope_advice**: Legal/compliance/HR policy questions

Classification uses few-shot learning with examples from the provided traces (C1–C10).

## Notes

- The catalog download URL is from the spec document
- Index is built with normalized embeddings for cosine similarity
- Metadata includes all fields specified in Section 5 of the spec
- Schemas follow Section 4 API contract exactly with no deviations
- Groq client uses Llama 3.3 70B with few-shot examples from actual conversation traces
- Response generation enforces structural constraints to prevent hallucinated URLs/names
- FastAPI application enforces 8-turn cap, handles errors gracefully, includes comprehensive logging
- All error responses are structured with clear validation messages
- No unhandled exceptions escape to client - fallback responses ensure 30s timeout is never exceeded

## Turn Cap Bug Fix (Critical)

**Issue**: Conversations approaching the 8-turn cap without converging would return empty recommendations, resulting in 0% Recall@10 scores.

**Fix Applied**: 
- Turn 7-8: System now forces a "ready_to_recommend" action if no shortlist has been committed yet
- Uses semantic search over the entire conversation context to generate best-effort recommendations
- Fallback mechanism ensures minimum 5 recommendations if LLM selection fails
- Preserves existing refine behavior (doesn't force if shortlist already exists)
- Enhanced exception logging with full tracebacks for debugging

**Test Coverage**: 
- Added `test_turn_cap_forces_recommendation()` to unit tests
- Standalone test script available: `python test_turn_cap_simple.py`
- Validates non-empty recommendations (1-10 items) at turn 8

**See**: `TURN_CAP_FIX.md` for detailed analysis and implementation notes.
