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
                "ranking for the league (teams or players, in the league's tie-breaker "
                "order). Some leagues rank by team and some by individual player; "
                "either way, this intent returns the full leaderboard."
            ),
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
                "own row (player-ranked leagues) or their team's row (team-ranked "
                "leagues); the backend selects the correct shape automatically. "
                "A player name is clearly mentioned and the focus is on "
                "standing/rank/position, not match-by-match history. "
                "Use GET_STANDINGS when they want the full leaderboard with no "
                "player named. Use GET_MATCH_HISTORY_BY_PLAYER when they ask for "
                "matches or results for a player."
            ),
            example_messages=[
                "what's Alice's rank in the league?",
                "where does Bob's team stand?",
                "show me Charlie's standing",
                "how is Diana doing in the standings?",
                "what place is Emma's team?",
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
                "for that player's team rather than a list of matches."
            ),
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
                "The user wants to see the list of all registered players and teams in the league."
            ),
            example_messages=[
                "show me all the players",
                "who's in the league?",
                "show me the roster",
                "list all teams",
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
                ParamDef("team1_player1_nickname", str, "Nickname of the first player on team 1"),
                ParamDef("team1_player2_nickname", str, "Nickname of the second player on team 1"),
                ParamDef("team2_player1_nickname", str, "Nickname of the first player on team 2"),
                ParamDef("team2_player2_nickname", str, "Nickname of the second player on team 2"),
                ParamDef("team1_score", str, "Score for team 1 as a non-negative integer string"),
                ParamDef("team2_score", str, "Score for team 2 as a non-negative integer string"),
            ],
            description=(
                "The user wants to record a doubles match result. This intent applies whenever the "
                "user expresses the desire to log/record/submit a match — even when no players or "
                "score are mentioned yet. All match details (players, scores) are OPTIONAL: any "
                "missing fields are simply rendered as a blank match-submission form for the user "
                "to fill in. Therefore, classify bare/info-less requests like 'record match', "
                "'submit a match', 'log a result', 'I want to enter a match' as this intent with "
                "high confidence — do NOT ask a clarification question for missing players or "
                "scores. New players and teams are automatically registered if they haven't played "
                "before."
            ),
            example_messages=[
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
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
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
                "The admin/host wants to correct the score of a previously recorded match. "
                "The user mentions 1 to 4 player nicknames to narrow down which match to edit; "
                "the server returns all matches containing ALL of the mentioned players, and the "
                "admin then picks one and edits its score in a form. The user does NOT type new "
                "scores in the chat message — score editing happens in the picker form."
            ),
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
                ParamDef("team1_player1_nickname", str, "First player of team 1 — used to identify the match"),
                ParamDef("team1_player2_nickname", str, "Second player of team 1 — used to identify the match"),
                ParamDef("team2_player1_nickname", str, "First player of team 2 — used to identify the match"),
                ParamDef("team2_player2_nickname", str, "Second player of team 2 — used to identify the match"),
            ],
            description=(
                "The admin/host wants to permanently delete a match record from the league. "
                "The match is identified by the four player nicknames across both teams."
            ),
            example_messages=[
                "delete the match between Alice/Bob and Charlie/Diana",
                "remove the match where John and Sarah played Mike and Emma",
                "erase the match Alice and Bob versus Charlie and Diana",
            ],
        ),

        IntentDefinition(
            name="DELETE_TEAM",
            intent_type=IntentType.WRITE,
            confidence_threshold=85,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef("player1_nickname", str, "Nickname of the first player in the team to delete"),
                ParamDef("player2_nickname", str, "Nickname of the second player in the team to delete"),
            ],
            description=(
                "The admin/host wants to permanently delete a team from the league roster. "
                "The team is identified by its two player nicknames. "
                "The team must have no associated match records before it can be deleted."
            ),
            example_messages=[
                "delete the team Alice and Bob",
                "remove Alice and Bob's team from the league",
                "delete the team formed by John and Sarah",
                "get rid of Mike and Emma's team",
            ],
        ),
    ]

    @classmethod
    def get(cls, name: str) -> IntentDefinition | None:
        return next((i for i in cls.INTENTS if i.name == name), None)
