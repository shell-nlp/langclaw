from collections.abc import Callable, Sequence
from typing import Any

from deepagents.backends import StateBackend
from deepagents.backends.protocol import BackendFactory, BackendProtocol
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.memory import MemoryMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from deepagents.middleware.skills import SkillsMiddleware
from deepagents.middleware.subagents import (
    CompiledSubAgent,
    GENERAL_PURPOSE_SUBAGENT,
    SubAgent,
    SubAgentMiddleware,
)
from deepagents.middleware.summarization import create_summarization_middleware
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    InterruptOnConfig,
    TodoListMiddleware,
)
from langchain.agents.middleware.types import AgentMiddleware
from langchain.agents.structured_output import ResponseFormat
from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer


BASE_AGENT_PROMPT = """You are a Deep Agent, an AI assistant that helps users accomplish tasks using tools. You respond with text and tool calls. The user can see your responses and tool outputs in real time.

## Core Behavior

- Be concise and direct. Don't over-explain unless asked.
- NEVER add unnecessary preamble (\"Sure!\", \"Great question!\", \"I'll now...\").
- Don't say \"I'll now do X\" — just do it.
- If the request is ambiguous, ask questions before acting.
- If asked how to approach something, explain first, then act.

## Professional Objectivity

- Prioritize accuracy over validating the user's beliefs
- Disagree respectfully when the user is incorrect
- Avoid unnecessary superlatives, praise, or emotional validation

## Doing Tasks

When the user asks you to do something:

1. **Understand first** — read relevant files, check existing patterns. Quick but thorough — gather enough evidence to start, then iterate.
2. **Act** — implement the solution. Work quickly but accurately.
3. **Verify** — check your work against what was asked, not against your own output. Your first attempt is rarely correct — iterate.

Keep working until the task is fully complete. Don't stop partway and explain what you would do — just do it. Only yield back to the user when the task is done or you're genuinely blocked.

**When things go wrong:**
- If something fails repeatedly, stop and analyze *why* — don't keep retrying the same approach.
- If you're blocked, tell the user what's wrong and ask for guidance.

## Progress Updates

For longer tasks, provide brief progress updates at reasonable intervals — a concise sentence recapping what you've done and what's next."""  # noqa: E501


def resolve_model(model: str | BaseChatModel) -> BaseChatModel:
    """Resolve a model string to a `BaseChatModel` instance.

    If `model` is already a `BaseChatModel`, returns it unchanged.

    String models are resolved via `init_chat_model`, with OpenAI models
    defaulting to the Responses API. See the `create_deep_agent` docstring for
    details on how to customize this behavior.

    Args:
        model: Model name string or pre-configured model instance.

    Returns:
        Resolved `BaseChatModel` instance.
    """
    if isinstance(model, BaseChatModel):
        return model
    if model.startswith("openai:"):
        # Use Responses API by default. To use chat completions, use
        # `model=init_chat_model("openai:...")`
        # To disable data retention with the Responses API, use
        # `model=init_chat_model("openai:...", use_responses_api=True, store=False, include=["reasoning.encrypted_content"])`
        return init_chat_model(model, use_responses_api=True)
    return init_chat_model(model)


def get_default_model() -> ChatAnthropic:
    """Get the default model for deep agents.

    Returns:
        `ChatAnthropic` instance configured with Claude Sonnet 4.6.
    """
    return ChatAnthropic(
        model_name="claude-sonnet-4-6",
    )


def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | SystemMessage | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph:

    model = get_default_model() if model is None else resolve_model(model)
    # TODO: 去除原本的backend,使用自己的后端
    from langclaw.langchain_api.middleware.sandbox_system_tool import SandboxSystemToolMiddleware

    backend = backend if backend is not None else (StateBackend)

    # Build general-purpose subagent with default middleware stack
    gp_middleware: list[AgentMiddleware[Any, Any, Any]] = [
        TodoListMiddleware(),
        # FilesystemMiddleware(backend=backend),
        SandboxSystemToolMiddleware(),
        create_summarization_middleware(model, backend),
        AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
        PatchToolCallsMiddleware(),
    ]
    if skills is not None:
        gp_middleware.append(SkillsMiddleware(backend=backend, sources=skills))
    if interrupt_on is not None:
        gp_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    general_purpose_spec: SubAgent = {  # ty: ignore[missing-typed-dict-key]
        **GENERAL_PURPOSE_SUBAGENT,
        "model": model,
        "tools": tools or [],
        "middleware": gp_middleware,
    }

    # Process user-provided subagents to fill in defaults for model, tools, and middleware
    processed_subagents: list[SubAgent | CompiledSubAgent] = []
    for spec in subagents or []:
        if "runnable" in spec:
            # CompiledSubAgent - use as-is
            processed_subagents.append(spec)
        else:
            # SubAgent - fill in defaults and prepend base middleware
            subagent_model = spec.get("model", model)
            subagent_model = resolve_model(subagent_model)

            # Build middleware: base stack + skills (if specified) + user's middleware
            subagent_middleware: list[AgentMiddleware[Any, Any, Any]] = [
                TodoListMiddleware(),
                # FilesystemMiddleware(backend=backend),
                SandboxSystemToolMiddleware(),
                create_summarization_middleware(subagent_model, backend),
                AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
                PatchToolCallsMiddleware(),
            ]
            subagent_skills = spec.get("skills")
            if subagent_skills:
                subagent_middleware.append(
                    SkillsMiddleware(backend=backend, sources=subagent_skills)
                )
            subagent_middleware.extend(spec.get("middleware", []))

            processed_spec: SubAgent = {  # ty: ignore[missing-typed-dict-key]
                **spec,
                "model": subagent_model,
                "tools": spec.get("tools", tools or []),
                "middleware": subagent_middleware,
            }
            processed_subagents.append(processed_spec)

    # Combine GP with processed user-provided subagents
    all_subagents: list[SubAgent | CompiledSubAgent] = [
        general_purpose_spec,
        *processed_subagents,
    ]

    # Build main agent middleware stack
    deepagent_middleware: list[AgentMiddleware[Any, Any, Any]] = [
        TodoListMiddleware(),
    ]
    if memory is not None:
        deepagent_middleware.append(MemoryMiddleware(backend=backend, sources=memory))
    if skills is not None:
        deepagent_middleware.append(SkillsMiddleware(backend=backend, sources=skills))
    deepagent_middleware.extend(
        [
            # FilesystemMiddleware(backend=backend),
            SandboxSystemToolMiddleware(),
            SubAgentMiddleware(
                backend=backend,
                subagents=all_subagents,
            ),
            create_summarization_middleware(model, backend),
            AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
            PatchToolCallsMiddleware(),
        ]
    )

    if middleware:
        deepagent_middleware.extend(middleware)
    if interrupt_on is not None:
        deepagent_middleware.append(HumanInTheLoopMiddleware(interrupt_on=interrupt_on))

    # Combine system_prompt with BASE_AGENT_PROMPT
    if system_prompt is None:
        final_system_prompt: str | SystemMessage = BASE_AGENT_PROMPT
    elif isinstance(system_prompt, SystemMessage):
        final_system_prompt = SystemMessage(
            content_blocks=[
                *system_prompt.content_blocks,
                {"type": "text", "text": f"\n\n{BASE_AGENT_PROMPT}"},
            ]
        )
    else:
        # String: simple concatenation
        final_system_prompt = system_prompt + "\n\n" + BASE_AGENT_PROMPT

    return create_agent(
        model,
        system_prompt=final_system_prompt,
        tools=tools,
        middleware=deepagent_middleware,
        response_format=response_format,
        context_schema=context_schema,
        checkpointer=checkpointer,
        store=store,
        debug=debug,
        name=name,
        cache=cache,
    ).with_config({"recursion_limit": 1000})
