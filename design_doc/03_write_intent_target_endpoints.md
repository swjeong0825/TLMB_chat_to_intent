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
- **URL Pattern**: /admin/leagues/{league_id}/matches/{match_id}

### Path Parameter Mapping


| URL Path Param | Resolved from (intent param name)                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| league_id      | league_id                                                                                                                                                                |
| match_id       | Resolved by handler: GET /leagues/{league_id}/matches → match all four player nicknames (case-insensitive, either player ordering within each team) → extract `match_id` |


### Request Body Fields


| Field Name  | Type   | Required | Enum Options | Resolved from (intent param name) |
| ----------- | ------ | -------- | ------------ | --------------------------------- |
| team1_score | string | Yes      | —            | new_team1_score                   |
| team2_score | string | Yes      | —            | new_team2_score                   |


### Notes

- The `match_id` path parameter is resolved by the handler via GET /leagues/{league_id}/matches. Find the match whose four player nicknames match all of `team1_player1_nickname`, `team1_player2_nickname`, `team2_player1_nickname`, `team2_player2_nickname` (case-insensitive; player order within each team pair is not guaranteed to be consistent).
- If no match is found, return an ERROR response (status_code 502).
- If multiple matches exist for the same player combination, use the most recent one (highest `created_at`) and include a note in `server_message` about the ambiguity.
- Scores must be non-negative integer strings. If an extracted score cannot be confirmed as valid, leave the `value` as `null` and record the issue in `server_message`.

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

