"""Google ADK and Gemini integration for ProofBid.

Imports remain lazy so the deterministic core works without the optional
``google`` dependency group installed.
"""


__all__ = [
    "AdkPlanner",
    "DEFAULT_GEMINI_MODEL",
    "GeminiAuthMode",
    "GeminiProviderAdapter",
    "GeminiProviderConfig",
    "PlannerExecutionError",
    "PlannerResponseError",
    "ProviderConfigurationError",
    "ProviderDependencyError",
]


def __getattr__(name: str):
    if name in {"AdkPlanner", "PlannerExecutionError", "PlannerResponseError"}:
        from . import adk_planner

        return getattr(adk_planner, name)
    if name in {
        "DEFAULT_GEMINI_MODEL",
        "GeminiAuthMode",
        "GeminiProviderAdapter",
        "GeminiProviderConfig",
        "ProviderConfigurationError",
        "ProviderDependencyError",
    }:
        from . import gemini

        return getattr(gemini, name)
    raise AttributeError(name)
