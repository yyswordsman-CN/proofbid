from __future__ import annotations

import pytest

from proofbid.adapters.google.gemini import (
    DEFAULT_GEMINI_MODEL,
    GeminiAuthMode,
    GeminiProviderConfig,
    ProviderConfigurationError,
)


def test_api_key_configuration_never_stores_secret() -> None:
    secret = "sentinel-secret-value"
    config = GeminiProviderConfig.from_env(environ={"GEMINI_API_KEY": secret})

    assert config.model == DEFAULT_GEMINI_MODEL
    assert config.auth_mode is GeminiAuthMode.API_KEY
    assert secret not in repr(config)


def test_vertex_configuration_requires_project_and_location() -> None:
    with pytest.raises(ProviderConfigurationError, match="GOOGLE_CLOUD_PROJECT"):
        GeminiProviderConfig.from_env(
            environ={"GOOGLE_GENAI_USE_ENTERPRISE": "true"}
        )

    config = GeminiProviderConfig.from_env(
        environ={
            "GOOGLE_GENAI_USE_ENTERPRISE": "true",
            "GOOGLE_CLOUD_PROJECT": "synthetic-project",
            "GOOGLE_CLOUD_LOCATION": "us-central1",
        }
    )
    assert config.auth_mode is GeminiAuthMode.VERTEX_AI


def test_missing_credentials_and_drifting_model_alias_fail_closed() -> None:
    with pytest.raises(ProviderConfigurationError, match="requires GEMINI_API_KEY"):
        GeminiProviderConfig.from_env(environ={})
    with pytest.raises(ProviderConfigurationError, match="explicit model id"):
        GeminiProviderConfig.from_env(
            model="gemini-flash-latest",
            environ={"GOOGLE_API_KEY": "synthetic"},
        )


def test_explicit_api_key_mode_rejects_vertex_environment() -> None:
    with pytest.raises(ProviderConfigurationError, match="conflicts"):
        GeminiProviderConfig.from_env(
            environ={
                "PROOFBID_GEMINI_AUTH": "api_key",
                "GOOGLE_GENAI_USE_ENTERPRISE": "true",
                "GOOGLE_CLOUD_PROJECT": "synthetic-project",
                "GOOGLE_CLOUD_LOCATION": "us-central1",
                "GOOGLE_API_KEY": "synthetic",
            }
        )


def test_enterprise_environment_takes_sdk_compatible_precedence() -> None:
    config = GeminiProviderConfig.from_env(
        environ={
            "GOOGLE_GENAI_USE_ENTERPRISE": "false",
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "GOOGLE_API_KEY": "synthetic",
        }
    )
    assert config.auth_mode is GeminiAuthMode.API_KEY

    with pytest.raises(ProviderConfigurationError, match="requires GEMINI_API_KEY"):
        GeminiProviderConfig.from_env(
            environ={"GOOGLE_GENAI_USE_ENTERPRISE": "yes"}
        )
