# Intent List

## Chatbot Name / Domain
- Tennis League Manager Chatbot

## Default Confidence Threshold
- 70

---

## Intent: GET_STANDINGS

- **Intent Type**: READ
- **Confidence Threshold Override**: 70 (default)
- **Description**: The user wants to see the current win/loss standings for all teams in the league, ranked by wins.
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
- **Description**: The user wants to see the list of all registered players and teams in the league.
- **Example Messages**:
  - "show me all the players"
  - "who's in the league?"
  - "show me the roster"
  - "list all teams"
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
- **Description**: The user wants to record a doubles match result. They describe which two players were on each team and what the score was. New players and teams are automatically registered if they haven't played before.
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
| team1_player1_nickname | string | Yes | Nickname of the first player on team 1. |
| team1_player2_nickname | string | Yes | Nickname of the second player on team 1. |
| team2_player1_nickname | string | Yes | Nickname of the first player on team 2. |
| team2_player2_nickname | string | Yes | Nickname of the second player on team 2. |
| team1_score | string | Yes | Score for team 1 as a non-negative integer string (e.g. "6"). The winning team's score is typically higher. |
| team2_score | string | Yes | Score for team 2 as a non-negative integer string (e.g. "3"). |

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
- **Confidence Threshold Override**: 80
- **Description**: The admin/host wants to correct the score of a previously recorded match. The match is identified by the four player nicknames across both teams.
- **Example Messages**:
  - "fix the score for Alice and Bob vs Charlie and Diana — it should be 6-2 not 6-3"
  - "correct the match score: John and Sarah vs Mike and Emma was actually 7-5"
  - "the score for Alice/Bob versus Charlie/Diana was wrong, change it to 6 to 4"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| team1_player1_nickname | string | Yes | First player of team 1 — used together with the other three nicknames to identify the match in history. |
| team1_player2_nickname | string | Yes | Second player of team 1 — used to identify the match. |
| team2_player1_nickname | string | Yes | First player of team 2 — used to identify the match. |
| team2_player2_nickname | string | Yes | Second player of team 2 — used to identify the match. |
| new_team1_score | string | Yes | Corrected score for team 1 as a non-negative integer string (e.g. "6"). |
| new_team2_score | string | Yes | Corrected score for team 2 as a non-negative integer string (e.g. "2"). |

---

## Intent: DELETE_MATCH

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 85
- **Description**: The admin/host wants to permanently delete a match record from the league. The match is identified by the four player nicknames across both teams.
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
| team1_player1_nickname | string | Yes | First player of team 1 — used together with the other three nicknames to identify the match in history. |
| team1_player2_nickname | string | Yes | Second player of team 1 — used to identify the match. |
| team2_player1_nickname | string | Yes | First player of team 2 — used to identify the match. |
| team2_player2_nickname | string | Yes | Second player of team 2 — used to identify the match. |

---

## Intent: DELETE_TEAM

- **Intent Type**: WRITE
- **Confidence Threshold Override**: 85
- **Description**: The admin/host wants to permanently delete a team from the league roster. The team is identified by its two player nicknames. The team must have no associated match records before it can be deleted.
- **Example Messages**:
  - "delete the team Alice and Bob"
  - "remove Alice and Bob's team from the league"
  - "delete the team formed by John and Sarah"
  - "get rid of Mike and Emma's team"

### Request Parameters

| Name | Type | Required | Source |
|------|------|----------|--------|
| league_id | string (UUID) | Yes | path |
| host_token | string (UUID) | Yes | header (X-Host-Token) |

### Chat-Driven Parameters

| Name | Type | Required | Notes |
|------|------|----------|-------|
| player1_nickname | string | Yes | Nickname of the first player in the team to delete. Used together with player2_nickname to look up the team_id. |
| player2_nickname | string | Yes | Nickname of the second player in the team to delete. |
