# Chat-to-Intent Server — Input Document Templates

This file defines the **three input documents** an AI agent needs to generate a domain-specific chat-to-intent server from the generic `chat_to_intent_server_ai_agents_guide.md`.

The generic guide defines the structure, pipeline, rules, and file layout. These three documents supply the **domain-specific content** that goes inside that structure.

---

## How the three documents map to generated code

| Input Document | Drives generation of |
|---|---|
| **1. Intent List** | `intent_registry.py`, LLM classification prompt, parameter resolver configuration, handler file scaffolding |
| **2. Read-Only Backend Endpoint Specs** | `read_only_backend_client.py` base URL, intent handler GET calls and response-reshaping logic |
| **3. Write Intent Target Endpoint Specs** | Write intent handler prefilled payload: `method`, `url`, `body` field schema |

---

# Document 1 — Intent List

## Purpose

Declare every intent the chatbot supports and all metadata the pipeline needs to handle it: its type (Read or Write), confidence threshold, parameter schemas, and LLM prompt hints.

**This is the most important of the three documents.** Every other component in the pipeline is driven off the intent registry, which is built directly from this document.

## Output file

`/ai/chat_to_intent/<chatbot_name>/01_intent_list.md`

## Template

```md
# Intent List

## Chatbot Name / Domain
-

## Default Confidence Threshold
- (system default is 70; only set this if you want a different global default)

---

## Intent: <INTENT_NAME>

- **Intent Type**: READ | WRITE
- **Confidence Threshold Override**: <integer 0–100, or omit to use default>
- **Description**: (1–2 sentences used in the LLM classification prompt)
- **Example Messages**:
  -
  -
  -

### Request Parameters
(Parameters sourced from the HTTP request: path params, query params, or body fields.
The LLM does NOT extract these — they come directly from the client request.)

| Name | Type | Required | Source |
|------|------|----------|--------|
|      |      |          | path \| query \| body |

### Chat-Driven Parameters
(Parameters the LLM extracts from the user's natural-language client_message.)

| Name | Type | Required | Notes |
|------|------|----------|-------|
|      |      |          |       |

---

## Intent: <INTENT_NAME>
(repeat block for each intent)
```

## Why it matters

- The `name`, `intent_type`, `description`, and `example_messages` fields are used to build the LLM **classification prompt** in `intent_identifier.py`.
- The `confidence_threshold` is used by the intent identifier to decide `HIGH` vs `LOW` confidence.
- The four parameter lists (required/optional × request/chat-driven) are used by all three sub-layers of the **Parameter Resolution Layer**.
- The `intent_type` determines which response shape the intent handler produces: domain data (Read) or prefilled payload (Write).
- The `name` becomes the `data_type` value in every response for that intent.

## What the AI agent builds from this document

- All entries in `application/intent_identification/intent_registry.py`
- The classification prompt template in `application/intent_identification/intent_identifier.py`
- The parameter extraction prompt in `application/parameter_resolution/chat_params_extractor.py`
- Scaffolded handler files under `intents/handlers/`

## Example

```md
# Intent List

## Chatbot Name / Domain
- Sports League Chatbot

## Default Confidence Threshold
- 70

---

## Intent: GET_STANDINGS

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to see the current league standings for a specific season. Returns a ranked list of teams with match statistics.
- **Example Messages**:
  - "show me the standings"
  - "what are the current standings for season 3?"
  - "who is top of the league?"

### Request Parameters

(none)

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| season_id | number | Yes | The season number or ID the user refers to. May be implicit (e.g. "current season" → resolve to latest). |

---

## Intent: GET_PLAYER_PROFILE

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to view the profile and current registration details of a specific player.
- **Example Messages**:
  - "show me John's profile"
  - "what team is player_456 on?"
  - "tell me about Sarah"

### Request Parameters

(none)

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player_id | string | Yes | The ID or name of the player the user mentions. |

---

## Intent: REGISTER_PLAYER

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 75
- **Description**: The user wants to register a player for a season. Returns a pre-filled registration form.
- **Example Messages**:
  - "register player_456 for season 3"
  - "add John to the upcoming season as a midfielder"
  - "sign up Sarah for season 4, shirt number 10"

### Request Parameters

(none)

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player_id | string | Yes | The player to register. |
| season_id | number | Yes | The target season. |
| position | string (enum) | No | Playing position: GK, DEF, MID, or FWD. |
| shirt_number | number | No | Preferred shirt number. |

---

## Intent: UPDATE_PLAYER_POSITION

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 80
- **Description**: The user wants to change a registered player's playing position for a season.
- **Example Messages**:
  - "move player_456 to goalkeeper for season 3"
  - "change Sarah's position to defender"
  - "update John's role to FWD in season 4"

### Request Parameters

(none)

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player_id | string | Yes | The player to update. |
| season_id | number | Yes | The season the registration belongs to. |
| position | string (enum) | Yes | New position: GK, DEF, MID, or FWD. |
```

---

# Document 2 — Read-Only Backend Endpoint Specs

## Purpose

Describe every external backend GET endpoint the chat-to-intent server may call through `ReadOnlyBackendGateway`. This covers both:

1. **Data endpoints** — called by Read intent handlers to fetch the data returned to the client
2. **Lookup/enrichment endpoints** — called by Write intent handlers to pre-fill optional form fields (e.g. fetching valid enum options or resolving IDs)

## Output file

`/ai/chat_to_intent/<chatbot_name>/02_read_only_backend_endpoints.md`

## Template

````md
# Read-Only Backend Endpoint Specs

## Base URL
-

---

## GET <path>

- **Description**:
- **Used by Intents**:

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
|      |      |             |

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
|      |      |          |             |

### Response Schema

```json
{
  "field": "type and description"
}
```

### Notes
- (any edge cases, pagination, error conditions the handler should be aware of)

---

## GET <path>
(repeat block for each endpoint)
````

## Why it matters

- The base URL is used to configure `infrastructure/providers/read_only_backend_client.py`.
- Each endpoint's path, path parameters, and query parameters determine how intent handlers construct GET calls via `ReadOnlyBackendGateway`.
- The response schema tells the agent how to **reshape** the raw backend response into the domain-specific `data` shape for Read intent responses. Raw responses are never passed through directly.
- For Write intents, lookup endpoints listed here tell the agent what supplementary GET calls are available to pre-fill optional fields (e.g. fetching valid position options for the `position` enum).

## What the AI agent builds from this document

- `infrastructure/config/settings.py` — base URL value
- Read intent handlers in `intents/handlers/` — GET call paths, query param construction, and response-reshaping logic
- Write intent handlers in `intents/handlers/` — supplementary GET calls for optional field pre-filling

## Example

````md
# Read-Only Backend Endpoint Specs

## Base URL
- https://api.sportsleague.example.com

---

## GET /seasons/{season_id}/standings

- **Description**: Returns the ranked standings table for a given season.
- **Used by Intents**: GET_STANDINGS

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| season_id | integer | The unique ID of the season. |

### Query Parameters

(none)

### Response Schema

```json
{
  "season_id": "integer — the season ID",
  "season_name": "string — human-readable season label (e.g. 'Season 3')",
  "standings": [
    {
      "rank": "integer",
      "team_id": "string",
      "team_name": "string",
      "played": "integer",
      "won": "integer",
      "drawn": "integer",
      "lost": "integer",
      "goals_for": "integer",
      "goals_against": "integer",
      "points": "integer"
    }
  ]
}
```

### Notes
- Returns 404 if the season does not exist. The handler should bubble this up as an ERROR response (status_code 502).

---

## GET /seasons

- **Description**: Returns a list of all seasons. Used to resolve "current season" or "latest season" references in the user's message.
- **Used by Intents**: GET_STANDINGS (optional enrichment), REGISTER_PLAYER (season lookup), UPDATE_PLAYER_POSITION (season lookup)

### Path Parameters

(none)

### Query Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| status | string | No | Filter by season status: `active`, `completed`, `upcoming`. |

### Response Schema

```json
{
  "seasons": [
    {
      "season_id": "integer",
      "season_name": "string",
      "status": "string — active | completed | upcoming",
      "start_date": "string (ISO 8601 date)"
    }
  ]
}
```

### Notes
- When the user says "current season" or "this season", the handler should call this endpoint with `status=active` and use the first result's `season_id`.

---

## GET /players/{player_id}

- **Description**: Returns the profile of a single player.
- **Used by Intents**: GET_PLAYER_PROFILE, REGISTER_PLAYER (to validate player exists before pre-filling), UPDATE_PLAYER_POSITION (to confirm registration exists)

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| player_id | string | The unique player identifier. |

### Query Parameters

(none)

### Response Schema

```json
{
  "player_id": "string",
  "display_name": "string",
  "date_of_birth": "string (ISO 8601 date)",
  "current_season_registration": {
    "season_id": "integer",
    "position": "string — GK | DEF | MID | FWD | null",
    "shirt_number": "integer | null"
  }
}
```

### Notes
- Returns 404 if the player does not exist.
- `current_season_registration` is null if the player is not registered for any active season.
````

---

# Document 3 — Write Intent Target Endpoint Specs

## Purpose

Describe the backend endpoints the chat-to-intent server's **prefilled payloads point to**. These are the endpoints the frontend will call when the user submits the pre-filled form from the chatroom.

The chat-to-intent server never calls these endpoints itself — it only assembles the `method`, `url`, and `body` schema so the frontend knows exactly how to submit the form.

## Output file

`/ai/chat_to_intent/<chatbot_name>/03_write_intent_target_endpoints.md`

## Template

```md
# Write Intent Target Endpoint Specs

---

## Intent: <INTENT_NAME>

- **HTTP Method**: POST | PUT | PATCH
- **URL Pattern**: /path/{param}/subpath

### Path Parameter Mapping

| URL Path Param | Resolved from (intent param name) |
|----------------|----------------------------------|
|                |                                  |

### Request Body Fields

| Field Name | Type | Required | Enum Options | Resolved from (intent param name) |
|------------|------|----------|--------------|----------------------------------|
|            |      |          |              |                                  |

### Notes
- (any constraints, conditional required fields, or special assembly logic the handler should know)

---

## Intent: <INTENT_NAME>
(repeat block for each Write intent)
```

## Why it matters

- The HTTP method and URL pattern (with path parameter mapping) determine the `method` and `url` fields in the prefilled payload.
- The request body field table is a direct specification of the `body` map in the Write intent response: each row becomes one entry with `type`, `required`, `value`, and `options` (for enums).
- The "Resolved from" column tells the agent which validated intent parameter to use as the `value` for each body field. If no mapping exists (i.e. the field cannot be pre-filled from the chat), `value` is `null`.

## What the AI agent builds from this document

- Write intent handlers in `intents/handlers/` — the complete prefilled payload: `method`, fully resolved `url`, and `body` map with field metadata and pre-filled values

## Example

```md
# Write Intent Target Endpoint Specs

---

## Intent: REGISTER_PLAYER

- **HTTP Method**: POST
- **URL Pattern**: /seasons/{season_id}/registrations

### Path Parameter Mapping

| URL Path Param | Resolved from (intent param name) |
|----------------|----------------------------------|
| season_id | season_id |

### Request Body Fields

| Field Name | Type | Required | Enum Options | Resolved from (intent param name) |
|------------|------|----------|--------------|----------------------------------|
| player_id | string | Yes | — | player_id |
| position | enum | No | GK, DEF, MID, FWD | position |
| shirt_number | number | No | — | shirt_number |

### Notes
- The backend enforces uniqueness: a player may only be registered once per season. Duplicate registration returns 409. If the handler detects this via a supplementary GET call (e.g. GET /players/{player_id}), it should surface it as an ERROR response rather than returning the prefilled form.

---

## Intent: UPDATE_PLAYER_POSITION

- **HTTP Method**: PATCH
- **URL Pattern**: /seasons/{season_id}/registrations/{player_id}

### Path Parameter Mapping

| URL Path Param | Resolved from (intent param name) |
|----------------|----------------------------------|
| season_id | season_id |
| player_id | player_id |

### Request Body Fields

| Field Name | Type | Required | Enum Options | Resolved from (intent param name) |
|------------|------|----------|--------------|----------------------------------|
| position | enum | Yes | GK, DEF, MID, FWD | position |

### Notes
- Only the `position` field is patchable via this endpoint. Shirt number changes use a separate endpoint (out of scope for this chatbot).
- If the player is not registered for the given season, the backend returns 404. The handler should check this via GET /players/{player_id} before returning the prefilled payload, and surface a 502 ERROR if not found.
```

---

# Checklist — What to Verify Before Handing to an AI Agent

Before passing these three documents to an AI agent for code generation, confirm:

**Intent List**
- [ ] Every intent the chatbot needs is listed
- [ ] Each intent has at least 3 example messages
- [ ] All parameters are correctly classified as Request vs. Chat-Driven and Required vs. Optional
- [ ] High-stakes Write intents have a confidence threshold higher than the default (70)
- [ ] Intent names are verb-noun formatted (e.g. `GET_STANDINGS`, `REGISTER_PLAYER`)

**Read-Only Backend Endpoint Specs**
- [ ] Every GET endpoint that any intent handler will call is listed
- [ ] The base URL is included
- [ ] Response schemas are detailed enough to write the reshaping logic
- [ ] Endpoints used only for optional field pre-filling are clearly noted as supplementary

**Write Intent Target Endpoint Specs**
- [ ] Every Write intent from the Intent List has a corresponding entry here
- [ ] The "Resolved from" mapping is complete — every body field either maps to an intent param or is explicitly noted as `null` (not pre-fillable)
- [ ] Enum options are listed for all enum-type fields
- [ ] URL patterns use the same parameter names as the Intent List's chat-driven or request parameters
