"""
Composition root — wires abstract ports to concrete implementations and
constructs the full pipeline with all dependencies injected.

This is the ONLY place that imports from both application/intents layers
and infrastructure. The application and intent layers never instantiate
infrastructure classes directly.

LLM provider is selected via the LLM_PROVIDER environment variable:
  groq    → GroqProvider   (set GROQ_API_KEY)
  openai  → OpenAIProvider (set OPENAI_API_KEY)
  google  → GoogleProvider (set GOOGLE_API_KEY)  [not yet implemented]
"""

import os
from functools import lru_cache

from app.application.chat_handler import ChatHandler
from app.application.intent_identification.intent_identifier import IntentIdentifier
from app.application.parameter_resolution.chat_params_extractor import ChatParamsExtractor
from app.application.parameter_resolution.chat_params_validator import ChatParamsValidator
from app.application.parameter_resolution.parameter_resolver import ParameterResolver
from app.application.parameter_resolution.request_params_validator import RequestParamsValidator
from app.infrastructure.config.settings import get_settings
from app.infrastructure.providers.read_only_backend_client import ReadOnlyBackendClient
from app.intents.base_intent_handler import BaseIntentHandler
from app.intents.handlers.delete_match_handler import DeleteMatchHandler
from app.intents.handlers.delete_team_handler import DeleteTeamHandler
from app.intents.handlers.edit_match_score_handler import EditMatchScoreHandler
from app.intents.handlers.edit_player_nickname_handler import EditPlayerNicknameHandler
from app.intents.handlers.get_match_history_by_player_handler import GetMatchHistoryByPlayerHandler
from app.intents.handlers.get_match_history_handler import GetMatchHistoryHandler
from app.intents.handlers.get_roster_handler import GetRosterHandler
from app.intents.handlers.get_standings_by_player_handler import GetStandingsByPlayerHandler
from app.intents.handlers.get_standings_handler import GetStandingsHandler
from app.intents.handlers.submit_match_result_handler import SubmitMatchResultHandler
from app.ports.llm_provider import LLMProvider


def _create_llm_provider() -> LLMProvider:
    """
    Factory: reads LLM_PROVIDER and instantiates the matching provider.
    Supported values (case-insensitive): groq | openai | google
    """
    provider_name = os.getenv("LLM_PROVIDER", "groq").lower().strip()

    if provider_name == "groq":
        from app.infrastructure.providers.groq_provider import GroqProvider
        return GroqProvider()

    if provider_name == "openai":
        from app.infrastructure.providers.openai_provider import OpenAIProvider
        return OpenAIProvider()

    if provider_name == "google":
        raise NotImplementedError(
            "GoogleProvider is not yet implemented. "
            "Set LLM_PROVIDER to 'groq' or 'openai'."
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider_name}'. "
        "Valid values: groq, openai, google."
    )


@lru_cache
def _build_chat_handler() -> ChatHandler:
    settings = get_settings()

    # Infrastructure
    llm_provider = _create_llm_provider()
    gateway = ReadOnlyBackendClient(settings)
    base_url = settings.backend_base_url

    # Intent handlers
    handler_registry: dict[str, BaseIntentHandler] = {
        "GET_STANDINGS": GetStandingsHandler(gateway),
        "GET_STANDINGS_BY_PLAYER": GetStandingsByPlayerHandler(gateway),
        "GET_MATCH_HISTORY": GetMatchHistoryHandler(gateway),
        "GET_MATCH_HISTORY_BY_PLAYER": GetMatchHistoryByPlayerHandler(gateway),
        "GET_ROSTER": GetRosterHandler(gateway),
        "SUBMIT_MATCH_RESULT": SubmitMatchResultHandler(base_url),
        "EDIT_PLAYER_NICKNAME": EditPlayerNicknameHandler(gateway, base_url),
        "EDIT_MATCH_SCORE": EditMatchScoreHandler(gateway, base_url),
        "DELETE_MATCH": DeleteMatchHandler(gateway, base_url),
        "DELETE_TEAM": DeleteTeamHandler(gateway, base_url),
    }

    # Application layer
    intent_identifier = IntentIdentifier(llm_provider)
    parameter_resolver = ParameterResolver(
        request_params_validator=RequestParamsValidator(),
        chat_params_extractor=ChatParamsExtractor(llm_provider),
        chat_params_validator=ChatParamsValidator(),
    )

    return ChatHandler(
        intent_identifier=intent_identifier,
        parameter_resolver=parameter_resolver,
        handler_registry=handler_registry,
    )


def get_chat_handler() -> ChatHandler:
    return _build_chat_handler()
