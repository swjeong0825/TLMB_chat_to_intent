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
      "subject_kind": "string — 'team' or 'player'; discriminates the row shape below",
      "rank": "integer — position in the table; tied subjects share the same rank",
      "team_id": "string (UUID) — present when subject_kind == 'team'",
      "player1_nickname": "string — present when subject_kind == 'team'",
      "player2_nickname": "string — present when subject_kind == 'team'",
      "player_id": "string (UUID) — present when subject_kind == 'player'",
      "nickname": "string — present when subject_kind == 'player'",
      "matches_played": "integer",
      "wins": "integer",
      "losses": "integer",
      "games_won": "integer",
      "games_lost": "integer",
      "games_diff": "integer",
      "win_pct": "float — wins / matches_played, 0.0 for unplayed subjects"
    }
  ],
  "tie_breakers": "list[string] — copy of the league's ordered ranking metrics; first entry is the primary metric"
}
```

### Notes
- Returns 404 if the league does not exist. The handler should surface this as an ERROR response (status_code 502).
- Tied subjects share the same rank (standard-competition ranking — see backend design doc 17).
- The response may be an empty `standings` array if no matches have been recorded yet; `tie_breakers` is still populated from the league's rules.
- `tie_breakers` is forwarded to the frontend so it can label the displayed metric column to match the league's primary tie-breaker (e.g. "Games won" vs "Games ±").

---

## GET /leagues/{league_id}/standings/by-player

- **Description**: Returns the standings row(s) for one named player. The response shape mirrors `/standings` (`subject_kind`-discriminated rows + top-level `tie_breakers`), but filtered to the player's perspective.
- **Used by Intents**: GET_STANDINGS_BY_PLAYER

### Path Parameters

| Name | Type | Description |
|------|------|-------------|
| league_id | string (UUID) | The unique identifier of the league. |

### Query Parameters

| Name | Type | Description |
|------|------|-------------|
| player_name | string | Case-insensitive nickname of the player. |

### Response Schema

Same row shape as `GET /leagues/{league_id}/standings` (see above). The `standings` array may contain **one or more rows** depending on the league's v3 rules; see notes.

### Notes
- Returns 404 if the league or the named player does not exist. The handler should surface this as an ERROR response (status_code 502).
- **v3 row-count semantics:** the number of rows depends on the league's `LeagueRules`:

  | League rules | Number of rows |
  |---|---|
  | `(team, OTPP=true)` | exactly 1 (the player's single team row) |
  | `(team, OTPP=false)` and the player belongs to N teams | N rows (one per team) |
  | `(player, OTPP=false)` | exactly 1 (the player's own player-subject row) |

  The chat handler (`GetStandingsByPlayerHandler`) forwards the array verbatim and does not parse per-row fields, so it transparently tolerates any of these shapes. Tests should not assert a single-row response for the by-player path.
- `tie_breakers` is forwarded to the frontend for column labelling, identical to `GET /standings`.
- See [`../../design_doc/configurable_ranking_v3.md`](../../design_doc/configurable_ranking_v3.md) for the full v3 spec.

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
- **For DELETE_MATCH handler:** this endpoint is called to resolve a single `match_id` from the four player nicknames extracted from the user's message. Match using case-insensitive nickname comparison, considering both player orderings within each team (player1/player2 positions are not guaranteed to be consistent). If no match is found for the given nicknames, the handler should return an ERROR response (status_code 502). If multiple matches exist for the same player combination, use the most recent one and note the ambiguity in `server_message`.
- **For EDIT_MATCH_SCORE handler:** this endpoint is called to fetch the list of candidate matches that contain ALL of the 1-4 chat-extracted player nicknames (set-membership, order-agnostic). An empty result is NOT an error — the handler returns `data_type: "EDIT_MATCH_SCORE"` with `matches: []` and a `server_message` explaining the ALL semantics. Filtering happens on the chat server; the backend response is not filtered by player.

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
- Players are added to the roster on either of two backend paths: (1) first confirmed match submission via `POST /leagues/{league_id}/matches` (auto-registration, gated by `LeagueRules.auto_register_players_on_match`), or (2) host-initiated pre-registration via `POST /leagues` (`initial_players` field at create time) or `POST /admin/leagues/{league_id}/players`. There is no separate player-registration endpoint — the roster IS the player list.
- Because of the second path, `GET /leagues/{league_id}/roster` may return `players` entries that have **no team and zero matches** (pre-registered roster members). The response shape is unchanged — a Player with no team simply does not appear in the `teams` array. Handlers that compute "matches played by player" or similar metrics should not assume `players ⊆ team-membership`.
