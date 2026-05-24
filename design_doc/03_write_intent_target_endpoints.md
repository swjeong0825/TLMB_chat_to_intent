# Write Intent Target Endpoint Specs

---

## Intent: SUBMIT_MATCH_RESULT

- **HTTP Method**: POST
- **URL Pattern**: /leagues/{league_id}/matches

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name) |
| -------------- | --------------------------------- |
| league_id      | league_id                         |


### Request Body Fields


| Field Name      | Type          | Required | Enum Options | Resolved from (intent param name)                                     |
| --------------- | ------------- | -------- | ------------ | --------------------------------------------------------------------- |
| team1_nicknames | array[string] | Yes      | —            | [team1_player1_nickname, team1_player2_nickname] assembled by handler |
| team2_nicknames | array[string] | Yes      | —            | [team2_player1_nickname, team2_player2_nickname] assembled by handler |
| team1_score     | string        | Yes      | —            | team1_score                                                           |
| team2_score     | string        | Yes      | —            | team2_score                                                           |


### Notes

- `team1_nicknames` and `team2_nicknames` are two-element string arrays. The handler assembles each array from the two separate chat-driven nickname parameters: `team1_nicknames = [team1_player1_nickname, team1_player2_nickname]` and `team2_nicknames = [team2_player1_nickname, team2_player2_nickname]`. The `value` in the prefilled payload should be the assembled array.
- Scores must be non-negative integer strings (e.g. `"6"`, `"3"`). If an extracted score cannot be confirmed as a valid non-negative integer string, leave the `value` as `null` and record the issue in `server_message`.
- The backend will auto-register any new players and teams on first submission. No pre-validation of player existence is needed.
- The backend enforces a one-team-per-player rule: a player may only be a member of one team per league (TeamConflictError → 409). This constraint cannot be pre-validated at this layer; it will surface as a backend error after the client submits the form.

---

## Intent: EDIT_PLAYER_NICKNAME

- **HTTP Method**: PATCH
- **URL Pattern**: /admin/leagues/{league_id}/players/{player_id}

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name)                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| league_id      | league_id                                                                                                                            |
| player_id      | Resolved by handler: GET /leagues/{league_id}/roster → look up player by `current_nickname` (case-insensitive) → extract `player_id` |


### Request Body Fields


| Field Name   | Type   | Required | Enum Options | Resolved from (intent param name) |
| ------------ | ------ | -------- | ------------ | --------------------------------- |
| new_nickname | string | Yes      | —            | new_nickname                      |


### Notes

- The `player_id` path parameter is not extractable from the chat. The handler must call GET /leagues/{league_id}/roster, find the player whose `nickname` matches `current_nickname` (case-insensitive), and use that player's `player_id` to construct the fully resolved URL.
- If no player with `current_nickname` is found in the roster, the handler should return an ERROR response (status_code 502) rather than a prefilled payload.
- The backend enforces case-insensitive nickname uniqueness within the league. If `new_nickname` conflicts with an existing player, the client will receive a 409 error on form submission.

---

## Intent: EDIT_MATCH_SCORE

- **HTTP Method**: PATCH
- **URL Pattern**: /leagues/{league_id}/matches/{match_id}
- **Response Shape**: picker (a list of candidate matches), not a single prefilled `{method, url, body}` payload.

### Picker Response Shape

Unlike the other write intents, EDIT_MATCH_SCORE returns a candidate list rather than a single prefilled payload, because the user only narrows the match by mentioning 1-4 players in chat. The frontend renders the candidates and lets the user pick a row, expand a prefilled form, edit the scores, and submit.

```json
{
  "data_type": "EDIT_MATCH_SCORE",
  "data": {
    "league_id": "<league_id>",
    "method": "PATCH",
    "url_template": "<backend_base_url>/leagues/<league_id>/matches/{match_id}",
    "player_filters": ["Alice", "Bob"],
    "matches": [
      {
        "match_id": "<uuid>",
        "team1_player1_nickname": "Alice",
        "team1_player2_nickname": "Bob",
        "team2_player1_nickname": "Charlie",
        "team2_player2_nickname": "Diana",
        "team1_score": 6,
        "team2_score": 3,
        "created_at": "2026-04-12T10:23:00Z"
      }
    ],
    "body_schema": {
      "team1_score": { "type": "string", "required": true },
      "team2_score": { "type": "string", "required": true }
    }
  },
  "server_message": "Showing matches that contain ALL of: Alice, Bob. Pick one to edit its score."
}
```

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name)                                                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| league_id      | league_id                                                                                                                                                                                        |
| match_id       | Selected by the user on the frontend by clicking a row in the picker. The handler does not pre-bind a single match; instead it returns `url_template` containing the literal `{match_id}` token. |


### Request Body Fields (rendered by the frontend after row selection)


| Field Name  | Type   | Required | Enum Options | Resolved from                                                                |
| ----------- | ------ | -------- | ------------ | ---------------------------------------------------------------------------- |
| team1_score | string | Yes      | —            | User input in the prefilled form (initial value = match's current `team1_score`). |
| team2_score | string | Yes      | —            | User input in the prefilled form (initial value = match's current `team2_score`). |

### Authorization (X-Host-Token bypass vs. player window)

The `url_template` points at the **player-facing** edit endpoint, not `/admin/...`. The same URL is used by every caller (admin and player). The backend decides:

- If the request has a valid `X-Host-Token` header, the edit is accepted regardless of the match's age. The frontend attaches the token automatically when the page was opened with `host_token=...` in the URL.
- If the request has no token, the edit is accepted only while the match is within the configured player-edit window (`PLAYER_SCORE_EDIT_WINDOW_SECONDS`, default 3600s). Outside the window the backend returns `422 MatchEditWindowExpiredError`.

This is why `host_token` is *not* a required request param on this intent in `01_intent_list.md`: the chat layer doesn't care about the token; the backend does.

### Notes

- Supplementary GET: `GET /leagues/{league_id}/matches`. The handler filters the response to matches whose four-nickname set is a superset of the mentioned nicknames (case-insensitive, ALL semantics). The result is sorted by `created_at` descending.
- If zero nicknames are extracted from the chat message, the handler returns `ERROR` (status_code 400) asking the user to mention at least one player.
- If 1+ nicknames are extracted but no match contains all of them, this is NOT an error: the handler still returns `data_type: "EDIT_MATCH_SCORE"` with `matches: []` and a `server_message` that explicitly states the ALL semantics (so the user understands why the list is empty).
- The handler does NOT filter out matches that are past the player-edit window. All candidate matches are returned regardless of age; the frontend renders disabled rows with a tooltip for players (and lets admins edit them anyway). Server-side filtering would hide rows the admin still wants to edit and would require the handler to know per-deployment window config, which lives outside the chat server.
- Scores are entered by the user in the per-row form rendered by the frontend; they are not extracted from the chat message. The form prefills with the match's current scores so the user can correct just the one that was wrong.
- The `url_template` is "fully resolved" except for the `{match_id}` placeholder, which the frontend substitutes when the user picks a row.

---

## Intent: DELETE_MATCH

- **HTTP Method**: DELETE
- **URL Pattern**: /admin/leagues/{league_id}/matches/{match_id}

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name)                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| league_id      | league_id                                                                                                                                                                |
| match_id       | Resolved by handler: GET /leagues/{league_id}/matches → match all four player nicknames (case-insensitive, either player ordering within each team) → extract `match_id` |


### Request Body Fields

(none — DELETE operation has no request body)

### Notes

- The `match_id` path parameter is resolved by the handler via GET /leagues/{league_id}/matches. Find the match whose four player nicknames match all of `team1_player1_nickname`, `team1_player2_nickname`, `team2_player1_nickname`, `team2_player2_nickname` (case-insensitive; player order within each team pair is not guaranteed to be consistent).
- If no match is found, return an ERROR response (status_code 502).
- If multiple matches exist for the same player combination, surface this as ambiguity in `server_message` and use the most recent one (highest `created_at`).
- This is a destructive, irreversible operation. The threshold is set to 85 to reduce the chance of acting on ambiguous user intent.
- After a match is deleted, if its associated team(s) have no remaining match records, the host may then delete those teams via DELETE_TEAM.

---

## Intent: DELETE_TEAM

- **HTTP Method**: DELETE
- **URL Pattern**: /admin/leagues/{league_id}/teams/{team_id}

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name)                                                                                                                              |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| league_id      | league_id                                                                                                                                                      |
| team_id        | Resolved by handler: GET /leagues/{league_id}/roster → match both player nicknames (case-insensitive, in either order) in the `teams` list → extract `team_id` |


### Request Body Fields

(none — DELETE operation has no request body)

### Notes

- The `team_id` path parameter is resolved by the handler via GET /leagues/{league_id}/roster. Find the team where both `player1_nickname` and `player2_nickname` match `player1_nickname` and `player2_nickname` from the intent params (case-insensitive, considering either ordering).
- If no matching team is found, return an ERROR response (status_code 502).
- This is a destructive, irreversible operation. The threshold is set to 85.
- The backend rejects team deletion if the team still has associated match records (TeamHasMatchesError → 409). The host must delete all associated matches first. This precondition cannot be pre-validated at this layer — the frontend will receive a 409 error if the team has remaining matches. The handler may optionally note this precondition in `server_message`.

---

## Intent: ADD_PLAYERS_TO_ROSTER

- **HTTP Method**: POST
- **URL Pattern**: /admin/leagues/{league_id}/players

### Path Parameter Mapping

| URL Path Param | Resolved from (intent param name) |
| -------------- | --------------------------------- |
| league_id      | league_id                         |

### Request Body Fields

| Field Name | Type          | Required | Enum Options | Resolved from (intent param name) |
| ---------- | ------------- | -------- | ------------ | --------------------------------- |
| nicknames  | array[string] | Yes      | —            | nicknames                         |

### Notes

- No supplementary GET — the handler is a pure prefilled-form passthrough.
- The chat-driven `nicknames` parameter is a list. The handler coerces a bare scalar string into a one-element list to cover LLMs that return a single string instead of a JSON array.
- Replaces v5's `ADD_ALLOWLIST_ENTRIES`. The `allowlist_entries` side table was retired in alembic 007; pre-registration now writes `Player` rows directly. The backend's `POST /admin/leagues/{league_id}/players` enforces case-insensitive nickname uniqueness within the league and against in-batch duplicates (409 `NicknameAlreadyInUseError`).

---

## Intent: REMOVE_PLAYER_FROM_ROSTER

- **HTTP Method**: DELETE
- **URL Pattern**: /admin/leagues/{league_id}/players/{player_id}

### Path Parameter Mapping

| URL Path Param | Resolved from (intent param name)                                                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| league_id      | league_id                                                                                                                                          |
| player_id      | Resolved by handler: GET /leagues/{league_id}/roster → look up player by `nickname` (case-insensitive) in the `players` list → extract `player_id` |

### Request Body Fields

(none — DELETE operation has no request body)

### Notes

- Supplementary GET: `GET /leagues/{league_id}/roster`. The handler resolves `player_id` from the spoken nickname. If the nickname is not found on the roster, the handler returns `CLARIFICATION_QUESTION` listing the actual roster nicknames so the host can pick the correct one.
- Replaces v5's `REMOVE_ALLOWLIST_ENTRY`. The backend's `DELETE /admin/leagues/{league_id}/players/{player_id}` is **hard-delete with a participation guard**: it only succeeds when the player has zero teams AND zero matches. Otherwise the backend returns 409 `PlayerHasParticipationError` with the participation counts; the frontend renders this as a user-facing message (it cannot be pre-validated at this layer).
- The "remove from allowlist" wording is intentionally retained in `example_messages` so existing user phrasing still routes here.

