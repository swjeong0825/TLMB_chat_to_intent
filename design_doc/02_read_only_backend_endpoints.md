# Read-Only Backend Endpoint Specs

## Base URL
- http://localhost:8000

---

## GET /leagues/{league_id}/standings

- **Description**: Returns the ranked win/loss standings for all teams in the league. Standings are always computed on the fly from match records.
- **Used by Intents**: GET_STANDINGS

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| league_id | string (UUID) | The unique identifier of the league. |

### Query Parameters

(none)

### Response Schema

```json
{
  "standings": [
    {
      "rank": "integer — position in the table; tied teams share the same rank",
      "team_id": "string (UUID)",
      "player1_nickname": "string",
      "player2_nickname": "string",
      "wins": "integer",
      "losses": "integer"
    }
  ]
}
```

### Notes
- Returns 404 if the league does not exist. The handler should surface this as an ERROR response (status_code 502).
- Tied teams share the same rank. No tiebreaker is applied in V1.
- The response may be an empty `standings` array if no matches have been recorded yet.

---

## GET /leagues/{league_id}/matches

- **Description**: Returns the chronological list of all recorded match results in the league, sorted by creation date descending (most recent first).
- **Used by Intents**: GET_MATCH_HISTORY, EDIT_MATCH_SCORE (supplementary — resolves match_id from player nicknames), DELETE_MATCH (supplementary — resolves match_id from player nicknames)

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| league_id | string (UUID) | The unique identifier of the league. |

### Query Parameters

(none)

### Response Schema

```json
{
  "matches": [
    {
      "match_id": "string (UUID)",
      "team1_player1_nickname": "string",
      "team1_player2_nickname": "string",
      "team2_player1_nickname": "string",
      "team2_player2_nickname": "string",
      "team1_score": "string — non-negative integer as string (e.g. '6')",
      "team2_score": "string — non-negative integer as string (e.g. '3')",
      "created_at": "string (ISO 8601 UTC datetime)"
    }
  ]
}
```

### Notes
- Returns 404 if the league does not exist. The handler should surface this as an ERROR response (status_code 502).
- Player nicknames reflect the current league state — admin nickname edits retroactively affect all historical display.
- **For EDIT_MATCH_SCORE and DELETE_MATCH handlers:** this endpoint is called to resolve a `match_id` from the four player nicknames extracted from the user's message. Match using case-insensitive nickname comparison, considering both player orderings within each team (player1/player2 positions are not guaranteed to be consistent). If no match is found for the given nicknames, the handler should return an ERROR response (status_code 502). If multiple matches exist for the same player combination, use the most recent one and note the ambiguity in `server_message`.

---

## GET /leagues/{league_id}/roster

- **Description**: Returns the list of all registered players and teams in the league.
- **Used by Intents**: GET_ROSTER, EDIT_PLAYER_NICKNAME (supplementary — resolves player_id from current_nickname), DELETE_TEAM (supplementary — resolves team_id from player nicknames)

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| league_id | string (UUID) | The unique identifier of the league. |

### Query Parameters

(none)

### Response Schema

```json
{
  "players": [
    {
      "player_id": "string (UUID)",
      "nickname": "string"
    }
  ],
  "teams": [
    {
      "team_id": "string (UUID)",
      "player1_nickname": "string",
      "player2_nickname": "string"
    }
  ]
}
```

### Notes
- Returns 404 if the league does not exist. The handler should surface this as an ERROR response (status_code 502).
- **For EDIT_PLAYER_NICKNAME handler:** look up the player by `current_nickname` (case-insensitive) in the `players` list to resolve their `player_id`. If no player with that nickname is found, return an ERROR response (status_code 502) rather than a prefilled payload.
- **For DELETE_TEAM handler:** look up the team by matching both `player1_nickname` and `player2_nickname` (case-insensitive, in either order) in the `teams` list to resolve the `team_id`. If no matching team is found, return an ERROR response (status_code 502).
- Players are auto-registered on first match submission. There is no explicit player registration endpoint.
