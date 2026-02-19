"""
Agent builder — always produces a deepagents deep agent.

Default skills and memory are bundled inside the package.
Callers extend (not replace) them via ``extra_tools`` and ``extra_skills``.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from langchain_core.language_models import BaseChatModel

from langclaw.config.schema import LangclawConfig
from langclaw.middleware.channel_context import ChannelContextMiddleware
from langclaw.middleware.guardrails import ContentFilterMiddleware, PIIMiddleware
from langclaw.middleware.rate_limit import RateLimitMiddleware
from langclaw.providers.registry import provider_registry

if TYPE_CHECKING:
    from langchain.agents.middleware import AgentMiddleware
    from langchain_core.tools import BaseTool

# ---------------------------------------------------------------------------
# Package-internal defaults
# ---------------------------------------------------------------------------

_DEFAULTS_DIR = Path(__file__).parent / "defaults"
_DEFAULT_SKILLS: list[str] = [str(_DEFAULTS_DIR / "skills")]
_DEFAULT_MEMORY: list[str] = [str(_DEFAULTS_DIR / "AGENTS.md")]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_claw_agent(
    config: LangclawConfig,
    *,
    extra_tools: list[BaseTool | Any] | None = None,
    extra_skills: list[str] | None = None,
    extra_middleware: list[AgentMiddleware] | None = None,
    model: BaseChatModel | None = None,
) -> Any:
    """
    Create a langclaw deep agent backed by ``deepagents.create_deep_agent``.

    The agent always starts with the built-in default skills (web-search,
    summarize) and default AGENTS.md memory. Extra capabilities stack on top.

    Args:
        config:           Loaded LangclawConfig.
        extra_tools:      Additional LangChain tools beyond the defaults.
        extra_skills:     Paths to directories containing ``SKILL.md`` files.
        extra_middleware: Additional ``AgentMiddleware`` instances inserted
                          after the built-in middleware stack.
        model:            Pre-built chat model. If omitted, resolved from config.

    Returns:
        A compiled LangGraph runnable (CompiledGraph) ready for ``.invoke``
        / ``.astream``.
    """
    try:
        from deepagents import create_deep_agent
        from deepagents.backends import FilesystemBackend
    except ImportError as exc:
        raise ImportError(
            "deepagents is required. Install with: uv add deepagents"
        ) from exc

    resolved_model = model or provider_registry.resolve_model(
        config.agents.model, config.providers
    )

    skills = _DEFAULT_SKILLS + list(extra_skills or [])
    tools = list(extra_tools or [])

    # Built-in middleware stack (order matters):
    #   1. ChannelContextMiddleware  — inject channel metadata first
    #   2. RateLimitMiddleware       — rate-check early, before expensive ops
    #   3. ContentFilterMiddleware   — block banned content before any LLM call
    #   4. PIIMiddleware             — redact PII from inbound messages
    #   5. caller-provided extras
    middleware: list[Any] = [
        ChannelContextMiddleware(),
        RateLimitMiddleware(rpm=config.agents.rate_limit_rpm),
        ContentFilterMiddleware(banned_keywords=config.agents.banned_keywords),
        PIIMiddleware(
            "azure_openai_api_key",
            detector=r"^[a-zA-Z0-9]{84}$",
            strategy="redact",
            apply_to_output=True,
            apply_to_tool_results=True,
        ),
        *(extra_middleware or []),
    ]

    return create_deep_agent(
        model=resolved_model,
        tools=tools,
        skills=skills,
        memory=_DEFAULT_MEMORY,
        backend=FilesystemBackend(root_dir=str(_DEFAULTS_DIR)),
        middleware=middleware,
    )
