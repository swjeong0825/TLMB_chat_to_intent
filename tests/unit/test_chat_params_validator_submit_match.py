"""SUBMIT_MATCH_RESULT chat params are optional — partial LLM extraction must not 400."""

from app.application.intent_identification.intent_registry import IntentRegistry
from app.application.parameter_resolution.chat_params_validator import ChatParamsValidator
from app.application.parameter_resolution.resolved_params import ResolvedParams


def test_submit_match_result_has_no_required_chat_params() -> None:
    intent = IntentRegistry.get("SUBMIT_MATCH_RESULT")
    assert intent is not None
    assert intent.required_chat_params == []
    assert len(intent.optional_chat_params) == 6


def test_submit_match_partial_extraction_passes_validation() -> None:
    intent = IntentRegistry.get("SUBMIT_MATCH_RESULT")
    assert intent is not None
    validator = ChatParamsValidator()
    params = ResolvedParams()

    extracted = {
        "pair1_player1_nickname": "Jae",
        "pair1_player2_nickname": None,
        "pair2_player1_nickname": "DK",
        "pair2_player2_nickname": None,
        "pair1_score": "6",
        "pair2_score": "4",
    }
    validator.validate(intent, extracted, params)

    assert params.get_str("pair1_player1_nickname") == "Jae"
    assert params.get_str("pair1_player2_nickname") is None
    assert params.get_str("pair2_player1_nickname") == "DK"
    assert params.get_str("pair2_score") == "4"
