# Intent List

## Chatbot Name / Domain
- Tennis League Manager Chatbot

## Default Confidence Threshold
- 70

---

## Intent: GET_STANDINGS

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to see the current win/loss standings for all pairs in the league, ranked by wins.
- **Example Messages**:
  - "show me the standings"
  - "who's winning the league?"
  - "what's the current leaderboard?"
  - "who's at the top of the table?"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |

### Chat-Driven Parameters

(none)

---

## Intent: GET_MATCH_HISTORY

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to see the list of all recorded match results in the league, sorted most recent first.
- **Example Messages**:
  - "show me all the matches"
  - "what matches have been played?"
  - "show me the match history"
  - "what were the recent results?"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |

### Chat-Driven Parameters

(none)

---

## Intent: GET_ROSTER

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to see the list of all registered players and pairs in the league.
- **Example Messages**:
  - "show me all the players"
  - "who's in the league?"
  - "show me the roster"
  - "list all pairs"
  - "who are the registered players?"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |

### Chat-Driven Parameters

(none)

---

## Intent: SUBMIT_MATCH_RESULT

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 75
- **Description**: The user wants to record a doubles match result. They describe which two players were on each pair and what the score was. New players and pairs are automatically registered if they haven't played before.
- **Example Messages**:
  - "Alice and Bob beat Charlie and Diana 6 to 3"
  - "record a match: John and Sarah vs Mike and Emma, 7-5"
  - "we just played, Alice and Bob won 6 to 4 against Charlie and Diana"
  - "submit result: John/Sarah beat Mike/Emma 6-2"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| pair1_player1_nickname | string | Yes | Nickname of the first player on pair 1. |
| pair1_player2_nickname | string | Yes | Nickname of the second player on pair 1. |
| pair2_player1_nickname | string | Yes | Nickname of the first player on pair 2. |
| pair2_player2_nickname | string | Yes | Nickname of the second player on pair 2. |
| pair1_score | string | Yes | Score for pair 1 as a non-negative integer string (e.g. "6"). The winning pair's score is typically higher. |
| pair2_score | string | Yes | Score for pair 2 as a non-negative integer string (e.g. "3"). |

---

## Intent: EDIT_PLAYER_NICKNAME

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 80
- **Description**: The admin/host wants to correct or update a player's nickname in the league. The player is identified by their current nickname.
- **Example Messages**:
  - "rename Alice to Alicia"
  - "change John's nickname to Johnny"
  - "update player Bob's name to Robert"
  - "fix Sarah's name, it should be Sara"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| current_nickname | string | Yes | The player's current nickname exactly as it appears in the league roster. Used to look up the player's ID. |
| new_nickname | string | Yes | The desired new nickname for the player. Must be unique within the league (case-insensitive). |

---

## Intent: EDIT_MATCH_SCORE

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 65
- **Description**: The user wants to correct the score of a previously recorded match. The user mentions 1-4 player nicknames in chat to narrow which match to edit; the server returns every recorded match whose four-nickname set contains ALL mentioned players. The frontend renders the candidates as a picker; the user picks one row to expand an inline form prefilled with the current scores, edits the scores, and submits. The corrected scores are NOT extracted from the chat message. The league host can edit any match; non-host players can only edit a match that is still within the league's configured player-edit window (the backend enforces this on submission).
- **Example Messages**:
  - "edit match score for Alice"
  - "fix a match score involving Alice and Bob"
  - "correct a match score for Alice, Bob, Charlie"
  - "edit the score of the match Alice and Bob vs Charlie and Diana"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player1_nickname | string | No (at least one of player1..player4_nickname required) | First player nickname mentioned by the user, used to filter candidate matches. |
| player2_nickname | string | No | Second player nickname mentioned by the user. |
| player3_nickname | string | No | Third player nickname mentioned by the user. |
| player4_nickname | string | No | Fourth player nickname mentioned by the user. |

### Notes

- All four `playerN_nickname` params are individually optional, but the handler returns an `ERROR` response if zero nicknames are extracted.
- Filtering is case-insensitive and uses ALL semantics: a match is returned only if every mentioned nickname is among the match's four nicknames (in either pair, in either ordering).
- An empty result is NOT an error — the response carries `matches: []` and a `server_message` that explains the ALL semantics so the user understands.
- The user enters the corrected scores in the form rendered for the selected row; the client then `PATCH`es the URL produced by the handler — one of two routes, picked per-role at chat-response time:
  - Admin chat request (`X-Host-Token` present) → `/admin/leagues/{league_id}/matches/{match_id}` (no window check; requires `X-Host-Token`).
  - Player chat request (no token) → `/leagues/{league_id}/matches/{match_id}` (backend enforces `PLAYER_SCORE_EDIT_WINDOW_SECONDS`, default 3600s; returns `422 MatchEditWindowExpiredError` outside the window).
  The chat-to-intent server is not in the write path.
- `host_token` is **not** a required request param on this intent (anyone with `league_id` can attempt an edit). The handler is indifferent to *whether* the caller is authorized; the header only changes which downstream URL goes into `url_template`. Final authorization happens at backend submission time. See `03_write_intent_target_endpoints.md` "Authorization (admin URL vs. player URL)" for the full contract.

---

## Intent: DELETE_MATCH

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 85
- **Description**: The admin/host wants to permanently delete a match record from the league. The match is identified by the four player nicknames across both pairs.
- **Example Messages**:
  - "delete the match between Alice/Bob and Charlie/Diana"
  - "remove the match where John and Sarah played Mike and Emma"
  - "erase the match Alice and Bob versus Charlie and Diana"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| pair1_player1_nickname | string | Yes | First player of pair 1 — used together with the other three nicknames to identify the match in history. |
| pair1_player2_nickname | string | Yes | Second player of pair 1 — used to identify the match. |
| pair2_player1_nickname | string | Yes | First player of pair 2 — used to identify the match. |
| pair2_player2_nickname | string | Yes | Second player of pair 2 — used to identify the match. |

---

## Intent: DELETE_PAIR

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 85
- **Description**: The admin/host wants to permanently delete a pair from the league roster. The pair is identified by its two player nicknames. The pair must have no associated match records before it can be deleted.
- **Example Messages**:
  - "delete the pair Alice and Bob"
  - "remove Alice and Bob's pair from the league"
  - "delete the pair formed by John and Sarah"
  - "get rid of Mike and Emma's pair"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player1_nickname | string | Yes | Nickname of the first player in the pair to delete. Used together with player2_nickname to look up the pair_id. |
| player2_nickname | string | Yes | Nickname of the second player in the pair to delete. |

---

## Intent: ADD_PLAYERS_TO_ROSTER

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 80
- **Description**: The admin/host wants to pre-register one or more players on the league's roster without recording a match for them. Pre-registered players show up in `GET_ROSTER` immediately and become match-eligible when the league's `auto_register_players_on_match` flag is off (only pre-registered nicknames can play). Replaces v5's `ADD_ALLOWLIST_ENTRIES`; the legacy "allowlist" wording is still accepted (and listed in `example_messages`) so existing user phrasing keeps working.
- **Example Messages**:
  - "add Alex and Daniel to the roster"
  - "add Michael to the roster"
  - "register Jason as a player"
  - "pre-register Alex Kim, Daniel Park, Jason Lee"
  - "allow Jason to play"
  - "add Alex, Daniel, Jason to the allowlist"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| nicknames | list[string] | Yes | One or more nicknames to pre-register on the league's roster. Bare scalar strings are coerced to a one-element list. |

---

## Intent: REMOVE_PLAYER_FROM_ROSTER

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 80
- **Description**: The admin/host wants to remove a pre-registered player from the league's roster. The DELETE only succeeds when the player has no pairs and no matches; otherwise the backend returns 409 `PlayerHasParticipationError`. Replaces v5's `REMOVE_ALLOWLIST_ENTRY`; the legacy "allowlist" wording is still accepted.
- **Example Messages**:
  - "remove Michael from the roster"
  - "drop Ryan from the roster"
  - "Daniel is no longer on the roster"
  - "remove Michael from the allowlist"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| nickname | string | Yes | The nickname to remove from the league's roster. Resolved to `player_id` via `GET /leagues/{league_id}/roster`. |
