"""
ChannelContextMiddleware — injects channel/user metadata into agent state
before the agent runs, so tools and system prompts can reference it.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.runtime import Runtime


class ChannelContextMiddleware(AgentMiddleware):
    """
    Injects channel metadata (channel name, user_id, context_id) into
    the agent state before each invocation.

    The metadata is stored under ``state["channel_context"]`` and is
    available to all downstream middleware and tools via the configurable
    RunnableConfig or state extensions.
    """

    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # Metadata flows in through the RunnableConfig configurable dict.
        # Channels set: config["configurable"]["channel_context"] = {...}
        config = runtime.config if hasattr(runtime, "config") else {}
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        channel_ctx = configurable.get("channel_context", {})

        if not channel_ctx:
            return None

        # Surface metadata into the top-level state so tools/prompts can read it.
        return {"channel_context": channel_ctx}
