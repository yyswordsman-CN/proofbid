"""Credential-minimizing Gemini model adapter for Google ADK."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from importlib.metadata import PackageNotFoundError, version
from typing import Mapping

from ...planning import PlanningError


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"
_MODEL_RE = re.compile(r"^gemini-[a-z0-9][a-z0-9.-]{1,95}$")
_TRUE_VALUES = {"1", "true"}


class ProviderConfigurationError(PlanningError):
    reason_code = "PROVIDER_CONFIGURATION_INVALID"


class ProviderDependencyError(PlanningError):
    reason_code = "PROVIDER_DEPENDENCY_MISSING"


class GeminiAuthMode(str, Enum):
    API_KEY = "api_key"
    VERTEX_AI = "vertex_ai"


@dataclass(frozen=True, slots=True)
class GeminiProviderConfig:
    model: str
    auth_mode: GeminiAuthMode
    timeout_seconds: float = 60.0
    max_attempts: int = 2

    def __post_init__(self) -> None:
        if not _MODEL_RE.fullmatch(self.model) or self.model.endswith("-latest"):
            raise ProviderConfigurationError(
                "Gemini model must be an explicit model id such as gemini-3.5-flash."
            )
        if not 1.0 <= self.timeout_seconds <= 300.0:
            raise ProviderConfigurationError("Gemini timeout must be between 1 and 300 seconds.")
        if not 1 <= self.max_attempts <= 3:
            raise ProviderConfigurationError("Gemini retry attempts must be between 1 and 3.")

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        environ: Mapping[str, str] | None = None,
        timeout_seconds: float = 60.0,
        max_attempts: int = 2,
    ) -> "GeminiProviderConfig":
        env = os.environ if environ is None else environ
        configured_model = model or env.get("PROOFBID_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL
        requested_auth = (env.get("PROOFBID_GEMINI_AUTH") or "auto").strip().casefold()
        enterprise_raw = env.get("GOOGLE_GENAI_USE_ENTERPRISE")
        vertex_raw = env.get("GOOGLE_GENAI_USE_VERTEXAI")
        enterprise_enabled = (
            enterprise_raw.strip().casefold() in _TRUE_VALUES
            if enterprise_raw is not None
            else None
        )
        vertex_enabled = (
            vertex_raw.strip().casefold() in _TRUE_VALUES
            if vertex_raw is not None
            else None
        )
        cloud_enabled = (
            enterprise_enabled
            if enterprise_enabled is not None
            else bool(vertex_enabled)
        )
        has_api_key = bool(
            env.get("GEMINI_API_KEY", "").strip()
            or env.get("GOOGLE_API_KEY", "").strip()
        )

        valid_auth_modes = {
            "auto",
            GeminiAuthMode.API_KEY.value,
            GeminiAuthMode.VERTEX_AI.value,
        }
        if requested_auth not in valid_auth_modes:
            raise ProviderConfigurationError(
                "PROOFBID_GEMINI_AUTH must be auto, api_key, or vertex_ai."
            )
        if requested_auth == GeminiAuthMode.API_KEY.value and cloud_enabled:
            raise ProviderConfigurationError(
                "API key mode conflicts with enabled Google Cloud/Vertex AI mode."
            )
        if requested_auth == GeminiAuthMode.VERTEX_AI.value or (
            requested_auth == "auto" and cloud_enabled
        ):
            if not cloud_enabled:
                raise ProviderConfigurationError(
                    "Google Cloud mode requires GOOGLE_GENAI_USE_ENTERPRISE=true "
                    "or GOOGLE_GENAI_USE_VERTEXAI=true."
                )
            if not env.get("GOOGLE_CLOUD_PROJECT", "").strip():
                raise ProviderConfigurationError(
                    "Vertex AI mode requires GOOGLE_CLOUD_PROJECT."
                )
            if not env.get("GOOGLE_CLOUD_LOCATION", "").strip():
                raise ProviderConfigurationError(
                    "Vertex AI mode requires GOOGLE_CLOUD_LOCATION."
                )
            auth_mode = GeminiAuthMode.VERTEX_AI
        else:
            if not has_api_key:
                raise ProviderConfigurationError(
                    "Gemini API mode requires GEMINI_API_KEY or GOOGLE_API_KEY."
                )
            auth_mode = GeminiAuthMode.API_KEY

        return cls(
            model=configured_model,
            auth_mode=auth_mode,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        )


class GeminiProviderAdapter:
    """Build an ADK Gemini model without copying credentials into application state."""

    provider_name = "google.gemini"

    def __init__(self, config: GeminiProviderConfig) -> None:
        self.config = config

    @property
    def configured_model(self) -> str:
        return self.config.model

    @property
    def auth_mode(self) -> str:
        return self.config.auth_mode.value

    @property
    def timeout_seconds(self) -> float:
        return self.config.timeout_seconds

    def package_versions(self) -> tuple[str, str]:
        try:
            return version("google-adk"), version("google-genai")
        except PackageNotFoundError as exc:
            raise ProviderDependencyError(
                "Install the ProofBid google extra before using the Gemini adapter."
            ) from exc

    def build_model(self):
        try:
            from google.adk.models import Gemini
            from google.genai import types
        except ImportError as exc:
            raise ProviderDependencyError(
                "Install the ProofBid google extra before using the Gemini adapter."
            ) from exc

        retry_options = types.HttpRetryOptions(
            attempts=self.config.max_attempts,
            initial_delay=1.0,
            max_delay=4.0,
            exp_base=2.0,
            jitter=0.2,
            http_status_codes=[408, 429, 500, 502, 503, 504],
        )
        return Gemini(
            model=self.config.model,
            client_kwargs={
                "enterprise": self.config.auth_mode is GeminiAuthMode.VERTEX_AI,
            },
            retry_options=retry_options,
        )


__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "GeminiAuthMode",
    "GeminiProviderAdapter",
    "GeminiProviderConfig",
    "ProviderConfigurationError",
    "ProviderDependencyError",
]
