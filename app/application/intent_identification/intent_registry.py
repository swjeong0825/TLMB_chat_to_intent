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
                "The user wants to see the current win/loss standings for all teams "
                "in the league, ranked by wins."
            ),
            example_messages=[
                "show me the standings",
                "who's winning the league?",
                "what's the current leaderboard?",
                "who's at the top of the table?",
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

        # ── WRITE INTENTS ─────────────────────────────────────────────────────

        IntentDefinition(
            name="SUBMIT_MATCH_RESULT",
            intent_type=IntentType.WRITE,
            confidence_threshold=75,
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
                "The user wants to record a doubles match result. They describe which two players "
                "were on each team and what the score was. New players and teams are automatically "
                "registered if they haven't played before."
            ),
            example_messages=[
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
            confidence_threshold=80,
            required_request_params=[_LEAGUE_ID_PARAM, _HOST_TOKEN_PARAM],
            required_chat_params=[
                ParamDef("team1_player1_nickname", str, "First player of team 1 — used to identify the match"),
                ParamDef("team1_player2_nickname", str, "Second player of team 1 — used to identify the match"),
                ParamDef("team2_player1_nickname", str, "First player of team 2 — used to identify the match"),
                ParamDef("team2_player2_nickname", str, "Second player of team 2 — used to identify the match"),
                ParamDef("new_team1_score", str, "Corrected score for team 1 as a non-negative integer string"),
                ParamDef("new_team2_score", str, "Corrected score for team 2 as a non-negative integer string"),
            ],
            description=(
                "The admin/host wants to correct the score of a previously recorded match. "
                "The match is identified by the four player nicknames across both teams."
            ),
            example_messages=[
                "fix the score for Alice and Bob vs Charlie and Diana — it should be 6-2 not 6-3",
                "correct the match score: John and Sarah vs Mike and Emma was actually 7-5",
                "the score for Alice/Bob versus Charlie/Diana was wrong, change it to 6 to 4",
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
