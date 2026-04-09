# TLM Chat-to-Intent Server

LLM-powered intermediary for the **Tennis League Manager (TLM)** system. Receives natural-language chat messages from the frontend, classifies them into a registered intent using an LLM, and either fetches and returns domain data (read intents) or assembles a pre-filled form payload for the frontend to confirm and submit (write intents).

**Live service:** [https://tlmb.swjapps.com](https://tlmb.swjapps.com)

**Key design constraints:**
- **Stateless** — no session or conversation history stored server-side; the client carries context via `last_server_message`.
- **Read-only to the backend** — only calls `GET` endpoints on the TLM Backend; never issues write requests.
- **Owns no domain logic** — all business rules and persistence belong to the TLM Backend.

## Related Projects

| Project | Role |
|---|---|
| **[TLMB_backend_main](https://github.com/swjeong0825/TLMB_backend_main)** | Domain logic, PostgreSQL persistence, and REST API. This server reads from it via `GET` only to populate responses and pre-fill write form payloads. Confirmed write forms are submitted by the frontend directly to the backend. |
| **[ai-agent-guidelines](https://github.com/swjeong0825/ai-agent-guidelines)** | AI agent coding guidelines used during development. |

## System Architecture

```
Frontend (Browser)
    │
    │  POST /chat  { client_message, last_server_message, league_id, [host_token] }
    ▼
Chat-to-Intent Server (this)
    │
    ├── intent_identifier ──► LLM
    │       │
    │  LOW confidence ──► CLARIFICATION_QUESTION response
    │  HIGH confidence
    │       │
    ├── parameter_resolver
    │       ├── request_params_validator
    │       ├── chat_params_extractor ──► LLM
    │       └── chat_params_validator
    │
    └── intent_handler ──► ReadOnlyBackendGateway.get() ──► TLM Backend
                │
            Read intent: returns reshaped domain data
            Write intent: returns pre-filled form payload
                              │
                    Frontend (user confirms)
                              │
                    POST/PATCH/DELETE directly ──► TLM Backend
```

## Supported Intents

| Intent | Type | Confidence Threshold | Description |
|---|---|---|---|
| `GET_STANDINGS` | READ | 70 | Show current win/loss standings |
| `GET_MATCH_HISTORY` | READ | 70 | Show list of recorded match results |
| `GET_ROSTER` | READ | 70 | Show all registered players and teams |
| `SUBMIT_MATCH_RESULT` | WRITE | 75 | Record a doubles match result (auto-registers new players) |
| `EDIT_PLAYER_NICKNAME` | WRITE | 80 | Correct a player's nickname (admin) |
| `EDIT_MATCH_SCORE` | WRITE | 80 | Correct a match score (admin) |
| `DELETE_MATCH` | WRITE | 85 | Delete a match record (admin, destructive) |
| `DELETE_TEAM` | WRITE | 85 | Delete a team from the roster (admin, destructive) |

If the LLM confidence score is below the intent's threshold, the server returns a `CLARIFICATION_QUESTION` response. The clarification loop is unbounded server-side; the client decides when to cap it.

## Request / Response Envelope

Every response uses the same three-field envelope regardless of outcome:

```json
{
  "data_type": "GET_STANDINGS | SUBMIT_MATCH_RESULT | CLARIFICATION_QUESTION | ERROR | ...",
  "data": { ... },
  "server_message": "Human-readable summary"
}
```

| `data_type` | `data` shape |
|---|---|
| Read intent name (e.g. `GET_STANDINGS`) | Reshaped domain data |
| Write intent name (e.g. `SUBMIT_MATCH_RESULT`) | `{ "method", "url", "body": { field: { type, required, value, options? } } }` |
| `CLARIFICATION_QUESTION` | `{ "question": "..." }` |
| `ERROR` | `{ "status_code": 400/422/502, "error_message": "..." }` |

For write intents, the returned `url` is always fully resolved (no unsubstituted path placeholders). The `X-Host-Token` header is not included — the client holds it and attaches it when submitting.

## Setup

**Prerequisites:** Python 3.13+, an API key for Groq, OpenAI, or Google Gemini

```bash
# 1. Clone and enter the project
git clone https://github.com/swjeong0825/TLMB_chat_to_intent.git
cd TLMB_chat_to_intent

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set:
#   LLM_PROVIDER=groq | openai | google
#   The corresponding API key and model name
#   BACKEND_BASE_URL=<URL of your running TLM Backend>
```

`.env.example` reference:

```dotenv
# LLM provider to use: groq | openai | google
LLM_PROVIDER=groq

# GROQ_API_KEY=gsk_...
# GROQ_MODEL=llama-3.3-70b-versatile

# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# GOOGLE_API_KEY=...
# GOOGLE_MODEL=gemini-2.0-flash

BACKEND_BASE_URL=https://tlmbbackendmain-production.up.railway.app
```

```bash
# 5. Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Running Tests

```bash
pytest
```

End-to-end tests require a live TLM Backend instance and a pre-created league. Set the following in your `.env` before running:

```dotenv
TEST_LEAGUE_ID=<uuid of a freshly created league>
TEST_HOST_TOKEN=<host_token returned when the league was created>
```

The test suite seeds all required match, player, and team data automatically.
