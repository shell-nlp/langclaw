"""
langclaw — production-ready multi-channel AI agent framework.

Quick start::

    from langclaw.config import load_config
    from langclaw.agents import create_claw_agent

    config = load_config()
    agent = create_claw_agent(config)
    result = agent.invoke({"messages": [{"role": "user", "content": "Hello!"}]})
"""

from langclaw.agents.builder import create_claw_agent
from langclaw.config.schema import LangclawConfig, load_config

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "create_claw_agent",
    "LangclawConfig",
    "load_config",
]
