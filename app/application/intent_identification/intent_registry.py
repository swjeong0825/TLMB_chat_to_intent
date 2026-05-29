from dataclasses import dataclass, field
from enum import Enum


class IntentType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


@dataclass(frozen=True)
class ParamDef:
    name: str
    type: type
    description: str = ""


@dataclass
class IntentDefinition:
    name: str
    intent_type: IntentType
    confidence_threshold: int = 70
    required_request_params: list[ParamDef] = field(default_factory=list)
    optional_request_params: list[ParamDef] = field(default_factory=list)
    required_chat_params: list[ParamDef] = field(default_factory=list)
    optional_chat_params: list[ParamDef] = field(default_factory=list)
    description: str = ""
    summary: str = ""
    example_messages: list[str] = field(default_factory=list)


# Shared request params declared once and reused across intents
_LEAGUE_ID_PARAM = ParamDef("league_id", str, "path")
_HOST_TOKEN_PARAM = ParamDef("host_token", str, "header:X-Host-Token")


class IntentRegistry:
    INTENTS: list[IntentDefinition] = [

        # ── READ INTENTS ──────────────────────────────────────────────────────

        IntentDefinition(
            name="GET_STANDINGS",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            description=(
                "The user wants to see the league's current standings — the configured "
                "ranking for the league (pairs or players, in the league's tie-breaker "
                "order). Some leagues rank by pair and some by individual player; "
                "either way, this intent returns the full leaderboard."
            ),
            summary="Show League leaderboard.",
            example_messages=[
                "show me the standings",
                "who's winning the league?",
                "what's the current leaderboard?",
                "who's at the top of the table?",
                "who has the most games?",
                "individual leaderboard",
                "show the player rankings",
            ],
        ),

        IntentDefinition(
            name="GET_MATCH_HISTORY",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            description=(
                "The user wants to see the list of all recorded match results "
                "in the league, sorted most recent first."
            ),
            summary="Show all match results, newest first.",
            example_messages=[
                "show me all the matches",
                "what matches have been played?",
                "show me the match history",
                "what were the recent results?",
            ],
        ),

        IntentDefinition(
            name="GET_STANDINGS_BY_PLAYER",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            required_chat_params=[
                ParamDef(
                    "player_name",
                    str,
                    "The player's nickname to look up their standing for",
                ),
            ],
            description=(
                "The user wants the standings row for a specific named player. "
                "Depending on the league configuration this is either the player's "
                "own row (player-ranked leagues) or their pair's row (pair-ranked "
                "leagues); the backend selects the correct shape automatically. "
                "A player name is clearly mentioned and the focus is on "
                "standing/rank/position, not match-by-match history. "
                "Use GET_STANDINGS when they want the full leaderboard with no "
                "player named. Use GET_MATCH_HISTORY_BY_PLAYER when they ask for "
                "matches or results for a player."
            ),
            summary="Show one player's standings row.",
            example_messages=[
                "what's Alice's rank in the league?",
                "where does Bob's pair stand?",
                "show me Charlie's standing",
                "how is Diana doing in the standings?",
                "what place is Emma's pair?",
                "where does Alice rank individually?",
                "what's Bob's individual standing?",
            ],
        ),

        IntentDefinition(
            name="GET_MATCH_HISTORY_BY_PLAYER",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            required_chat_params=[
                ParamDef(
                    "player_name",
                    str,
                    "The player's nickname to look up match history for",
                ),
            ],
            description=(
                "The user wants to see the match history for a specific named player. "
                "A player name is clearly mentioned in the message. "
                "Use GET_MATCH_HISTORY instead when no specific player is mentioned. "
                "Use GET_STANDINGS_BY_PLAYER when they ask for rank, standing, or leaderboard position "
                "for that player's pair rather than a list of matches."
            ),
            summary="Show one player's match history.",
            example_messages=[
                "show me Alice's match history",
                "what matches has Bob played?",
                "show me the games for Charlie",
                "what are Alice's results?",
                "matches involving Bob",
                "how has Diana been performing?",
            ],
        ),

        IntentDefinition(
            name="GET_ROSTER",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            description=(
                "The user wants to see the list of all registered players and pairs in the league."
            ),
            summary="Show all registered players and pairs.",
            example_messages=[
                "show me all the players",
                "who's in the league?",
                "show me the roster",
                "list all pairs",
                "who are the registered players?",
            ],
        ),

        IntentDefinition(
            name="HELP",
            intent_type=IntentType.READ,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            description=(
                "The user wants to discover what the chatbot can do — a general help / "
                "command-list request. Triggered by bare requests like 'help', 'help me', "
                "'what can you do?', 'which commands do you support?', 'how do I use this?'. "
                "Returns the full list of supported intents with their descriptions and "
                "example messages; no league data is fetched. "
                "Do NOT use this intent when the user is asking for help completing a "
                "specific action — for example, 'help me record a match' is "
                "SUBMIT_MATCH_RESULT, and 'how do I edit a score?' is EDIT_MATCH_SCORE. "
                "Only use HELP for generic, action-less discovery requests."
            ),
            summary="Generic help, listing available commands.",
            example_messages=[
                "help",
                "help me",
                "what can you do?",
                "what can I ask?",
                "which commands do you support?",
                "show me the commands",
                "list of commands",
                "how do I use this?",
                "what are the supported intents?",
                "what features do you have?",
            ],
        ),

        # ── WRITE INTENTS ─────────────────────────────────────────────────────

        IntentDefinition(
            name="SUBMIT_MATCH_RESULT",
            intent_type=IntentType.WRITE,
            confidence_threshold=70,
            required_request_params=[_LEAGUE_ID_PARAM],
            optional_chat_params=[
                ParamDef("pair1_player1_nickname", str, "Nickname of the first player on pair 1"),
                ParamDef("pair1_player2_nickname", str, "Nickname of the second player on pair 1"),
                ParamDef("pair2_player1_nickname", str, "Nickname of the first player on pair 2"),
                ParamDef("pair2_player2_nickname", str, "Nickname of the second player on pair 2"),
                ParamDef("pair1_score", str, "Score for pair 1 as a non-negative integer string"),
                ParamDef("pair2_score", str, "Score for pair 2 as a non-negative integer string"),
            ],
            description=(
                "The user wants to record a doubles match result. This intent applies whenever the "
                "user expresses the desire to log/record/submit a match — even when no players or "
                "score are mentioned yet. All match details (players, scores) are OPTIONAL: any "
                "missing fields are simply rendered as a blank match-submission form for the user "
                "to fill in. Therefore, classify bare/info-less requests like 'record match', "
                "'submit a match', 'log a result', 'I want to enter a match' as this intent with "
                "high confidence — do NOT ask a clarification question for missing players or "
                "scores. New players and pairs are automatically registered if they haven't played "
                "before."
            ),
            summary="Record a doubles match result.",
            example_messages=[
                "Jeff + James 6:4 John + Hana",
                "Tony & Hana vs Aaron & Sarah",
                "record match",
                "record a match",
                "submit a match",
                "submit a match result",
                "log a result",
                "enter a match",
                "I want to record a match",
                "I want to submit a match result",
                "Alice and Bob beat Charlie and Diana 6 to 3",
                "record a match: John and Sarah vs Mike and Emma, 7-5",
                "we just played, Alice and Bob won 6 to 4 against Charlie and Diana",
                "submit result: John/Sarah beat Mike/Emma 6-2",
            ],
        ),

        IntentDefinition(
            name="EDIT_PLAYER_NICKNAME",
            intent_type=IntentType.WRITE,
            confidence_threshold=80,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef(
                    "current_nickname",
                    str,
                    "The player's current nickname exactly as it appears in the league roster",
                ),
                ParamDef("new_nickname", str, "The desired new nickname for the player"),
            ],
            description=(
                "The admin/host wants to correct or update a player's nickname in the league. "
                "The player is identified by their current nickname."
            ),
            summary="Change a player's nickname.",
            example_messages=[
                "rename Alice to Alicia",
                "change John's nickname to Johnny",
                "update player Bob's name to Robert",
                "fix Sarah's name, it should be Sara",
            ],
        ),

        IntentDefinition(
            name="EDIT_MATCH_SCORE",
            intent_type=IntentType.WRITE,
            confidence_threshold=65,
            # `host_token` is intentionally NOT required here: any user
            # with `league_id` (player or host) may want to correct a
            # match score. The backend enforces the policy: players can
            # only edit recently-created matches (configurable window,
            # default 1h); admins (with X-Host-Token) can edit any
            # match at any time.
            required_request_params=[_LEAGUE_ID_PARAM],
            optional_chat_params=[
                ParamDef(
                    "player1_nickname",
                    str,
                    "First player nickname mentioned by the user, used to narrow which match to edit",
                ),
                ParamDef(
                    "player2_nickname",
                    str,
                    "Second player nickname mentioned by the user (optional)",
                ),
                ParamDef(
                    "player3_nickname",
                    str,
                    "Third player nickname mentioned by the user (optional)",
                ),
                ParamDef(
                    "player4_nickname",
                    str,
                    "Fourth player nickname mentioned by the user (optional)",
                ),
            ],
            description=(
                "The user wants to correct the score of a previously recorded match. "
                "The user mentions 1 to 4 player nicknames to narrow down which match to edit; "
                "the server returns all matches containing ALL of the mentioned players, and the "
                "user then picks one and edits its score in a form. The new score is NOT typed in "
                "the chat message — score editing happens in the picker form. "
                "The league host can edit any match; non-host players can only edit a recently "
                "submitted match within the league's configured edit window."
            ),
            summary="Update/Fix the match score.",
            example_messages=[
                "edit match score for Alice",
                "update match score for Alice",
                "fix a match score involving Alice and Bob",
                "correct a match score for Alice, Bob, Charlie",
                "edit the score of the match Alice and Bob vs Charlie and Diana",
                "I want to fix the score of one of Alice's matches",
            ],
        ),

        IntentDefinition(
            name="DELETE_MATCH",
            intent_type=IntentType.WRITE,
            confidence_threshold=85,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef("pair1_player1_nickname", str, "First player of pair 1 — used to identify the match"),
                ParamDef("pair1_player2_nickname", str, "Second player of pair 1 — used to identify the match"),
                ParamDef("pair2_player1_nickname", str, "First player of pair 2 — used to identify the match"),
                ParamDef("pair2_player2_nickname", str, "Second player of pair 2 — used to identify the match"),
            ],
            description=(
                "The admin/host wants to permanently delete a match record from the league. "
                "The match is identified by the four player nicknames across both pairs."
            ),
            summary="Delete a match (need four players).",
            example_messages=[
                "delete the match between Alice/Bob and Charlie/Diana",
                "remove the match where John and Sarah played Mike and Emma",
                "erase the match Alice and Bob versus Charlie and Diana",
            ],
        ),

        IntentDefinition(
            name="DELETE_PAIR",
            intent_type=IntentType.WRITE,
            confidence_threshold=85,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef("player1_nickname", str, "Nickname of the first player in the pair to delete"),
                ParamDef("player2_nickname", str, "Nickname of the second player in the pair to delete"),
            ],
            description=(
                "The admin/host wants to permanently delete a pair from the league roster. "
                "The pair is identified by its two player nicknames. "
                "The pair must have no associated match records before it can be deleted."
            ),
            summary="Delete a pair with no matches.",
            example_messages=[
                "delete the pair Alice and Bob",
                "remove Alice and Bob's pair from the league",
                "delete the pair formed by John and Sarah",
                "get rid of Mike and Emma's pair",
            ],
        ),

        IntentDefinition(
            name="ADD_PLAYERS_TO_ROSTER",
            intent_type=IntentType.WRITE,
            confidence_threshold=80,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef(
                    "nicknames",
                    list,
                    "One or more nicknames to pre-register on the league's roster",
                ),
            ],
            description=(
                "The admin/host wants to pre-register one or more players on the "
                "league's roster without recording a match for them. Pre-registered "
                "players show up in GET_ROSTER immediately and become match-eligible "
                "when the league's `auto_register_players_on_match` flag is off "
                "(meaning only pre-registered nicknames can play). The frontend "
                "should use this intent for 'add to roster' / 'allow X to play' "
                "requests; the legacy 'allowlist' wording also maps here (the "
                "allowlist concept was retired)."
            ),
            summary="Pre-register players on the roster.",
            example_messages=[
                "add Alex and Daniel to the roster",
                "add Michael to the roster",
                "register Jason as a player",
                "pre-register Alex Kim, Daniel Park, Jason Lee",
                "allow Jason to play",
                "add Alex, Daniel, Jason to the allowlist",
            ],
        ),

        IntentDefinition(
            name="REMOVE_PLAYER_FROM_ROSTER",
            intent_type=IntentType.WRITE,
            confidence_threshold=80,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef(
                    "nickname",
                    str,
                    "The nickname to remove from the league's roster",
                ),
            ],
            description=(
                "The admin/host wants to remove a pre-registered player from the "
                "league's roster. The DELETE only succeeds when the player has no "
                "pairs and no matches; otherwise the backend returns 409 "
                "`PlayerHasParticipationError`. The frontend's error renderer "
                "surfaces that to the user. The legacy 'remove from allowlist' "
                "wording also maps here."
            ),
            summary="Remove one player from the roster.",
            example_messages=[
                "remove Michael from the roster",
                "drop Ryan from the roster",
                "Daniel is no longer on the roster",
                "remove Michael from the allowlist",
            ],
        ),
    ]

    @classmethod
    def get(cls, name: str) -> IntentDefinition | None:
        return next((i for i in cls.INTENTS if i.name == name), None)
