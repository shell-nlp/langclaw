"""
Provider registry — maps model strings to LangChain chat models.

Engineering rule: adding a new provider = one ProviderSpec entry + one field in ProvidersConfig.
No if-elif chains anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from langclaw.config.schema import ProvidersConfig

# ---------------------------------------------------------------------------
# ProviderSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderSpec:
    """Describes a single LLM provider and how to activate it."""

    name: str
    """Internal identifier (matches ProvidersConfig field name)."""

    env_key: str
    """Primary environment variable for the API key."""

    display_name: str
    """Human-readable name for status / CLI output."""

    keywords: tuple[str, ...] = field(default_factory=tuple)
    """Model name substrings that uniquely identify this provider."""

    env_base_key: str = ""
    """Env var for custom API base URL (e.g. OPENAI_API_BASE)."""

    is_gateway: bool = False
    """True if this provider can route to any model (e.g. OpenRouter)."""


# ---------------------------------------------------------------------------
# Built-in provider catalogue
# ---------------------------------------------------------------------------

PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="openai",
        env_key="OPENAI_API_KEY",
        env_base_key="OPENAI_BASE_URL",
        display_name="OpenAI",
        keywords=("gpt", "o1", "o3", "o4"),
    ),
    ProviderSpec(
        name="anthropic",
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        keywords=("claude",),
    ),
    ProviderSpec(
        name="google",
        env_key="GOOGLE_API_KEY",
        display_name="Google",
        keywords=("gemini", "palm"),
    ),
    ProviderSpec(
        name="openrouter",
        env_key="OPENROUTER_API_KEY",
        env_base_key="OPENROUTER_API_BASE",
        display_name="OpenRouter",
        is_gateway=True,
    ),
    ProviderSpec(
        name="azure_openai",
        env_key="AZURE_OPENAI_API_KEY",
        # AzureChatOpenAI reads AZURE_OPENAI_ENDPOINT (not AZURE_OPENAI_BASE_URL)
        env_base_key="AZURE_OPENAI_ENDPOINT",
        display_name="Azure OpenAI",
        keywords=("azure",),
    ),
]

# Fast lookup: name -> spec
_BY_NAME: dict[str, ProviderSpec] = {p.name: p for p in PROVIDERS}


# ---------------------------------------------------------------------------
# ProviderRegistry
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """
    Resolves a model string (e.g. ``"anthropic:claude-sonnet-4-5-20250929"``)
    to a configured LangChain BaseChatModel by injecting provider credentials
    from LangclawConfig into the environment before calling ``init_chat_model``.
    """

    def resolve_model(
        self,
        model_str: str,
        providers_cfg: ProvidersConfig,
        **model_kwargs: object,
    ) -> BaseChatModel:
        """
        Resolve *model_str* to a ``BaseChatModel``.

        The model string can be:
        - Prefixed:   ``"anthropic:claude-sonnet-4-5-20250929"``
        - Plain:      ``"claude-sonnet-4-5-20250929"`` (provider inferred from keywords)
        - Gateway:    ``"openrouter/openai/gpt-4.1"``
        """
        spec = self._match_spec(model_str)
        if spec:
            self._inject_env(spec, providers_cfg)
        return init_chat_model(model_str, **model_kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _match_spec(model_str: str) -> ProviderSpec | None:
        """Find the ProviderSpec that best matches *model_str*."""
        lower = model_str.lower()

        # 1. Explicit prefix match: "anthropic:claude-..."
        if ":" in lower:
            prefix = lower.split(":")[0].replace("-", "_")
            if prefix in _BY_NAME:
                return _BY_NAME[prefix]

        # 2. Keyword match on model name
        for spec in PROVIDERS:
            if any(kw in lower for kw in spec.keywords):
                return spec

        # 3. Fall back to gateway providers
        for spec in PROVIDERS:
            if spec.is_gateway and spec.name in lower:
                return spec

        return None

    @staticmethod
    def _inject_env(spec: ProviderSpec, providers_cfg: ProvidersConfig) -> None:
        """Set provider env vars from config (only if not already set in environment)."""
        provider_cfg = getattr(providers_cfg, spec.name, None)
        if provider_cfg is None:
            return

        if provider_cfg.api_key and not os.environ.get(spec.env_key):
            os.environ[spec.env_key] = provider_cfg.api_key

        if spec.env_base_key and provider_cfg.api_base and not os.environ.get(spec.env_base_key):
            os.environ[spec.env_base_key] = provider_cfg.api_base

        # Azure OpenAI requires OPENAI_API_VERSION in addition to the standard fields.
        # AzureChatOpenAI reads this env var directly.
        if spec.name == "azure_openai":
            api_version = getattr(provider_cfg, "api_version", "")
            if api_version and not os.environ.get("OPENAI_API_VERSION"):
                os.environ["OPENAI_API_VERSION"] = api_version

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def list_configured(self, providers_cfg: ProvidersConfig) -> list[dict[str, str]]:
        """Return a list of providers that have a key configured."""
        result = []
        for spec in PROVIDERS:
            cfg = getattr(providers_cfg, spec.name, None)
            has_key = bool((cfg and cfg.api_key) or os.environ.get(spec.env_key))
            result.append(
                {
                    "name": spec.name,
                    "display": spec.display_name,
                    "configured": "yes" if has_key else "no",
                    "gateway": "yes" if spec.is_gateway else "no",
                }
            )
        return result


# Module-level singleton — import this everywhere
provider_registry = ProviderRegistry()
