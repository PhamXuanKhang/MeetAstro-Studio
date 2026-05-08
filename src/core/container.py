"""
Dependency Injection Container for AI Meeting Assistant.

Provides centralized service management with lazy initialization.
Services are created on first access and cached for reuse.

Usage:
    from src.core.container import Container

    container = Container()
    analyzer = container.get_analyzer()
    transcriber = container.get_transcriber()

For testing, create a container with mock settings:
    container = Container(settings=mock_settings)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from src.config import Settings, get_settings

if TYPE_CHECKING:
    from src.modules.jira_client import JiraClient
    from src.providers.base_analyzer import BaseAnalyzer
    from src.providers.base_transcriber import BaseTranscriber


class Container:
    """
    Dependency injection container for application services.

    Provides lazy initialization of services with proper configuration.
    All services are created using the provided Settings instance,
    making it easy to inject mock configurations for testing.
    """

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """
        Initialize container with optional settings override.

        Args:
            settings: Settings instance to use. If None, uses get_settings().
        """
        self._settings = settings or get_settings()
        self._analyzer: Optional[BaseAnalyzer] = None
        self._transcriber: Optional[BaseTranscriber] = None
        self._diarize_transcriber: Optional[BaseTranscriber] = None
        self._jira_client: Optional[JiraClient] = None

    @property
    def settings(self) -> Settings:
        """Return the settings instance."""
        return self._settings

    def get_analyzer(self) -> BaseAnalyzer:
        """
        Get the analyzer service (lazy initialization).

        Returns OpenAIAnalyzer if API key is configured, otherwise MockAnalyzer.
        """
        if self._analyzer is None:
            if self._settings.openai_api_key:
                from src.providers.openai_analyzer import OpenAIAnalyzer
                self._analyzer = OpenAIAnalyzer(
                    api_key=self._settings.openai_api_key,
                    model=self._settings.openai_model,
                )
            else:
                from src.providers.mock_analyzer import MockAnalyzer
                self._analyzer = MockAnalyzer()
        return self._analyzer

    def get_transcriber(self) -> BaseTranscriber:
        """
        Get the transcriber service (lazy initialization).

        Returns OpenAITranscriber if API key is configured, otherwise raises.
        """
        if self._transcriber is None:
            if not self._settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for transcription")
            from src.providers.openai_transcriber import OpenAITranscriber
            self._transcriber = OpenAITranscriber(
                api_key=self._settings.openai_api_key,
            )
        return self._transcriber

    def get_diarize_transcriber(self) -> BaseTranscriber:
        """
        Get the diarization transcriber service (lazy initialization).

        Returns WhisperLiveKitDiarizeTranscriber when WHISPER_LIVEKIT_URL is set,
        otherwise falls back to OpenAIDiarizeTranscriber (requires OPENAI_API_KEY).
        """
        if self._diarize_transcriber is None:
            if self._settings.whisper_livekit_url:
                from src.providers.whisper_livekit_transcriber import (
                    WhisperLiveKitDiarizeTranscriber,
                )
                self._diarize_transcriber = WhisperLiveKitDiarizeTranscriber(
                    url=self._settings.whisper_livekit_url,
                )
            elif self._settings.openai_api_key:
                from src.providers.openai_diarize_transcriber import (
                    OpenAIDiarizeTranscriber,
                )
                self._diarize_transcriber = OpenAIDiarizeTranscriber(
                    api_key=self._settings.openai_api_key,
                )
            else:
                raise ValueError(
                    "No diarization provider configured. "
                    "Set WHISPER_LIVEKIT_URL or OPENAI_API_KEY."
                )
        return self._diarize_transcriber

    def get_jira_client(self) -> JiraClient:
        """
        Get the Jira client (lazy initialization).

        Returns JiraClient configured from settings.
        Client will operate in stub mode if credentials are missing.
        """
        if self._jira_client is None:
            from src.modules.jira_client import JiraClient
            self._jira_client = JiraClient(
                base_url=self._settings.jira_base_url,
                email=self._settings.jira_email,
                token=self._settings.jira_api_token,
                project_key=self._settings.jira_project_key,
            )
        return self._jira_client

    def reset(self) -> None:
        """Reset all cached services. Useful for testing."""
        self._analyzer = None
        self._transcriber = None
        self._diarize_transcriber = None
        self._jira_client = None


# Global container instance for convenience
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get the global container instance.

    Creates the container on first call using default settings.
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def set_container(container: Container) -> None:
    """
    Set the global container instance.

    Useful for testing to inject a container with mock settings.
    """
    global _container
    _container = container


def reset_container() -> None:
    """Reset the global container. Useful for testing."""
    global _container
    _container = None
