from typing import Annotated, NotRequired, cast

from deepagents.backends.utils import sanitize_tool_call_id
from deepagents.middleware._utils import append_to_system_message
from deepagents.middleware.filesystem import (
    _build_evicted_content,
    _create_content_preview,
    _extract_text_from_message,
)
from langchain.agents.middleware import AgentMiddleware
from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from loguru import logger

from langclaw.langchain_api.tools.sandbox import (
    edit_file,
    execute_tool,
    get_backend,
    glob_tool,
    grep_tool,
    ls_tool,
    read_file,
    write_file,
)

FILESYSTEM_SYSTEM_PROMPT = """## Following Conventions

- Read files before editing — understand existing content before making changes
- Mimic existing style, naming conventions, and patterns

## Filesystem Tools `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`

You have access to a filesystem which you can interact with using these tools.
All file paths must start with a /. Follow the tool docs for the available tools, and use pagination (offset/limit) when reading large files.

- ls: list files in a directory (requires absolute path)
- read_file: read a file from the filesystem
- write_file: write to a file in the filesystem
- edit_file: edit a file in the filesystem
- glob: find files matching a pattern (e.g., "**/*.py")
- grep: search for text within files

## Large Tool Results

When a tool result is too large, it may be offloaded into the filesystem instead of being returned inline. In those cases, use `read_file` to inspect the saved result in chunks, or use `grep` within `/large_tool_results/` if you need to search across offloaded tool results and do not know the exact file path. Offloaded tool results are stored under `/large_tool_results/<tool_call_id>`."""
EXECUTION_SYSTEM_PROMPT = """## Execute Tool `execute`

You have access to an `execute` tool for running shell commands in a sandboxed environment.
Use this tool to run commands, scripts, tests, builds, and other shell operations.

- execute: run a shell command in the sandbox (returns output and exit code)"""
TOOLS_EXCLUDED_FROM_EVICTION = (
    "ls",
    "glob",
    "grep",
    "read_file",
    "edit_file",
    "write_file",
)
TOO_LARGE_TOOL_MSG = """Tool result too large, the result of this tool call {tool_call_id} was saved in the filesystem at this path: {file_path}

You can read the result from the filesystem by using the read_file tool, but make sure to only read part of the result at a time.

You can do this by specifying an offset and limit in the read_file tool call. For example, to read the first 100 lines, you can use the read_file tool with offset=0 and limit=100.

Here is a preview showing the head and tail of the result (lines of the form `... [N lines truncated] ...` indicate omitted lines in the middle of the content):

{content_sample}
"""


NUM_CHARS_PER_TOKEN = 4
from langchain.agents.middleware import AgentState
from opensandbox.config import ConnectionConfigSync
from opensandbox.sync.adapters.factory import AdapterFactorySync

from langclaw.langchain_api.sandbox.open_sandbox import DOMAIN


def dict_merge(left: dict[str, str], right: dict[str, str]) -> dict[str, str]:
    if left is None:
        left = {}
    result = left | right
    return result


class SandboxSystemToolState(AgentState):
    """沙箱系统工具中间件状态"""

    sandbox_id_dict: NotRequired[Annotated[dict[str, str], dict_merge]]


class SandboxSystemToolMiddleware(AgentMiddleware):
    """沙箱系统工具中间件"""

    tools = [
        execute_tool,
        ls_tool,
        read_file,
        write_file,
        grep_tool,
        glob_tool,
        edit_file,
    ]
    state_schema = SandboxSystemToolState

    def __init__(self, tool_token_limit_before_evict: int | None = 20000) -> None:
        self._tool_token_limit_before_evict = tool_token_limit_before_evict

    async def abefore_agent(self, state, runtime):
        user_id = runtime.context.user_id
        backend = get_backend(runtime, state)
        sandbox_id = backend.sandbox.id
        return {"sandbox_id_dict": {user_id: sandbox_id}}

    async def aafter_agent(self, state, runtime):
        # config = ConnectionConfigSync(domain=DOMAIN)
        # factory = AdapterFactorySync(config)
        # sandbox_service = factory.create_sandbox_service()
        user_id = runtime.context.user_id
        # sandbox_id = state["sandbox_id_dict"][user_id]
        backend = get_backend(runtime, state)
        sandbox_id = backend.sandbox.id
        backend.sandbox.kill()
        # sandbox_service.kill_sandbox(sandbox_id)
        logger.warning(f"用户 **{user_id}** 的沙箱 ID 为 {sandbox_id} 已被杀死")
        return None

    def wrap_model_call(
        self,
        request,
        handler,
    ):
        prompt_parts = [FILESYSTEM_SYSTEM_PROMPT, EXECUTION_SYSTEM_PROMPT]
        system_prompt = "\n\n".join(prompt_parts).strip()
        new_system_message = append_to_system_message(
            request.system_message, system_prompt
        )
        request = request.override(system_message=new_system_message)
        return handler(request)

    async def awrap_model_call(self, request, handler):
        return await self.wrap_model_call(request, handler)

    def wrap_tool_call(self, request, handler):
        if (
            self._tool_token_limit_before_evict is None
            or request.tool_call["name"] in TOOLS_EXCLUDED_FROM_EVICTION
        ):
            return handler(request)

        tool_result = handler(request)
        return self._intercept_large_tool_result(tool_result, request.runtime)

    async def awrap_tool_call(self, request, handler):
        if (
            self._tool_token_limit_before_evict is None
            or request.tool_call["name"] in TOOLS_EXCLUDED_FROM_EVICTION
        ):
            return await handler(request)

        tool_result = await handler(request)
        return self._intercept_large_tool_result(tool_result, request.runtime)

    def _process_large_message(
        self,
        message: ToolMessage,
        resolved_backend,
    ):

        if not self._tool_token_limit_before_evict:
            return message, None

        content_str = _extract_text_from_message(message)

        # Check if content exceeds eviction threshold
        if (
            len(content_str)
            <= NUM_CHARS_PER_TOKEN * self._tool_token_limit_before_evict
        ):
            return message, None

        # Write content to filesystem
        sanitized_id = sanitize_tool_call_id(message.tool_call_id)
        file_path = f"/large_tool_results/{sanitized_id}"
        result = resolved_backend.write(file_path, content_str)
        if result.error:
            return message, None

        # Create preview showing head and tail of the result
        content_sample = _create_content_preview(content_str)
        replacement_text = TOO_LARGE_TOOL_MSG.format(
            tool_call_id=message.tool_call_id,
            file_path=file_path,
            content_sample=content_sample,
        )

        evicted = _build_evicted_content(message, replacement_text)
        processed_message = ToolMessage(
            content=cast("str | list[str | dict]", evicted),
            tool_call_id=message.tool_call_id,
            name=message.name,
            id=message.id,
            artifact=message.artifact,
            status=message.status,
            additional_kwargs=dict(message.additional_kwargs),
            response_metadata=dict(message.response_metadata),
        )
        return processed_message, result.files_update

    def _intercept_large_tool_result(
        self, tool_result: ToolMessage | Command, runtime: ToolRuntime
    ) -> ToolMessage | Command:
        if isinstance(tool_result, ToolMessage):
            resolved_backend = get_backend(runtime)
            processed_message, files_update = self._process_large_message(
                tool_result,
                resolved_backend,
            )
            return (
                Command(
                    update={
                        "files": files_update,
                        "messages": [processed_message],
                    }
                )
                if files_update is not None
                else processed_message
            )

        if isinstance(tool_result, Command):
            update = tool_result.update
            if update is None:
                return tool_result
            command_messages = update.get("messages", [])
            accumulated_file_updates = dict(update.get("files", {}))
            resolved_backend = get_backend(runtime)
            processed_messages = []
            for message in command_messages:
                if not isinstance(message, ToolMessage):
                    processed_messages.append(message)
                    continue

                processed_message, files_update = self._process_large_message(
                    message,
                    resolved_backend,
                )
                processed_messages.append(processed_message)
                if files_update is not None:
                    accumulated_file_updates.update(files_update)
            return Command(
                update={
                    **update,
                    "messages": processed_messages,
                    "files": accumulated_file_updates,
                }
            )
        msg = f"Unreachable code reached in _intercept_large_tool_result: for tool_result of type {type(tool_result)}"
        raise AssertionError(msg)
