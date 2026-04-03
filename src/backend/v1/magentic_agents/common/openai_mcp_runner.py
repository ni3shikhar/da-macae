"""OpenAI + MCP Tool Runner — Executes agent tasks using Azure OpenAI with MCP tools.

When Azure AI Foundry is not available, this module provides a direct
integration between Azure OpenAI (function calling) and the MCP tool
server. Each agent's system prompt and MCP tool definitions are sent
to the OpenAI API, which decides which tools to call. Tool calls are
forwarded to the MCP server via the MCP SDK SSE client.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

# Tool names whose results are blob upload confirmations.
# When detected, the raw JSON is appended to the final output so the
# frontend can render download links automatically.
_BLOB_UPLOAD_TOOLS = {"storage_upload_blob"}

import structlog
from mcp import ClientSession
from mcp.client.sse import sse_client

from .doc_generator import generate_documents_with_summary

logger = structlog.get_logger(__name__)

# Maximum tool-call rounds to prevent infinite loops
_MAX_TOOL_ROUNDS = 15

# Type alias for the progress callback
# (agent_name, tool_name, status, detail) -> None
ProgressCallback = Callable[
    [str, str, str, str],
    Coroutine[Any, Any, None],
]


def _mcp_tools_to_openai(
    tools: list[Any],
    requested_names: set[str] | None,
) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to OpenAI function-calling format."""
    openai_tools: list[dict[str, Any]] = []
    for tool in tools:
        name = tool.name
        if requested_names and name not in requested_names:
            continue

        description = (tool.description or f"MCP tool: {name}")[:1024]
        # MCP inputSchema is a JSON Schema dict
        parameters = tool.inputSchema or {"type": "object", "properties": {}}

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        })
    return openai_tools


def _extract_text_from_call_result(result: Any) -> str:
    """Extract text content from an MCP CallToolResult."""
    if not result or not result.content:
        return ""
    parts: list[str] = []
    for item in result.content:
        if hasattr(item, "text"):
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


def _append_blob_uploads(final_text: str, blob_uploads: list[str]) -> str:
    """Append blob upload JSON metadata to the agent's final text.

    The frontend ``FormattedContent`` component automatically detects
    inline ``{"status":"uploaded","container":"...","blob":"..."}`` JSON
    and renders a download card with a link.  By appending the raw tool
    results here we guarantee the user always sees a clickable download
    link, even when the LLM summarises the upload in prose without
    including the raw JSON.
    """
    seen: set[tuple[str, str]] = set()
    unique: list[str] = []
    for raw in blob_uploads:
        try:
            obj = json.loads(raw)
            key = (obj.get("container", ""), obj.get("blob", ""))
            if key in seen:
                continue
            seen.add(key)
            if raw in final_text:
                continue
            unique.append(raw)
        except (json.JSONDecodeError, TypeError):
            continue

    if not unique:
        return final_text

    return final_text + "\n\n" + "\n".join(unique)


async def run_agent_with_openai(
    *,
    openai_client: Any,
    model: str,
    system_prompt: str,
    task: str,
    mcp_server_url: str,
    tool_names: list[str],
    agent_name: str = "agent",
    on_progress: ProgressCallback | None = None,
    subtask_label: str | None = None,
) -> dict[str, Any]:
    """Run an agent task using Azure OpenAI with MCP tool calling.

    This is the main entry point. It:
    1. Connects to the MCP server via SSE
    2. Lists tools and converts them to OpenAI function format
    3. Sends the system prompt + task to OpenAI with tools
    4. Iterates through tool calls, executing them via MCP
    5. Returns the final text response

    Args:
        openai_client: An AsyncAzureOpenAI client instance.
        model: The deployment name (e.g. "gpt-4.1").
        system_prompt: The agent's system prompt.
        task: The user/orchestrator task for this agent.
        mcp_server_url: URL of the MCP tool server (SSE endpoint base).
        tool_names: List of MCP tool names this agent can use.
        agent_name: Name of the agent (for logging).
        on_progress: Optional async callback for streaming tool-call progress.

    Returns:
        A dict with 'text' (final response) and 'usage' (token counts).
    """
    sse_url = f"{mcp_server_url.rstrip('/')}/sse"
    requested = set(tool_names) if tool_names else None

    # Accumulate token usage across all LLM rounds
    _total_prompt_tokens = 0
    _total_completion_tokens = 0
    _total_llm_calls = 0

    logger.info(
        "openai_mcp_run_start",
        agent=agent_name,
        model=model,
        tools_requested=len(tool_names),
        mcp_url=sse_url,
        task_preview=task[:200],
    )

    # ── Connect to MCP server and run the agentic loop ─────────────
    async with sse_client(sse_url, timeout=30, sse_read_timeout=300) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # 1. List tools from MCP server
            tools_result = await session.list_tools()
            openai_tools = _mcp_tools_to_openai(tools_result.tools, requested)

            logger.info(
                "openai_mcp_tools_resolved",
                agent=agent_name,
                total_mcp_tools=len(tools_result.tools),
                agent_tools=len(openai_tools),
            )

            # Track blob uploads so we can surface download links
            blob_uploads: list[str] = []

            # 2. Build initial messages
            messages: list[dict[str, Any]] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 4096,
            }
            if openai_tools:
                kwargs["tools"] = openai_tools
                kwargs["tool_choice"] = "auto"

            # 3. Iterative tool-calling loop
            for round_num in range(_MAX_TOOL_ROUNDS):
                try:
                    response = await openai_client.chat.completions.create(**kwargs)
                except Exception:
                    logger.exception(
                        "openai_mcp_run_llm_error",
                        agent=agent_name,
                        round=round_num,
                    )
                    raise

                # Accumulate token usage from this round
                _total_llm_calls += 1
                if hasattr(response, 'usage') and response.usage:
                    _total_prompt_tokens += getattr(response.usage, 'prompt_tokens', 0) or 0
                    _total_completion_tokens += getattr(response.usage, 'completion_tokens', 0) or 0

                choice = response.choices[0]
                message = choice.message

                # If no tool calls, we have the final response
                if not message.tool_calls:
                    final_text = message.content or ""
                    if blob_uploads:
                        final_text = _append_blob_uploads(
                            final_text, blob_uploads,
                        )
                    # Auto-generate Word/Excel documents from report output
                    # Show summary in chat, full details in document
                    try:
                        doc_result = await generate_documents_with_summary(
                            final_text, agent_name, subtask_label=subtask_label,
                        )
                        if doc_result:
                            blob_uploads.extend(doc_result.uploads)
                            # Replace full text with summary + download links
                            final_text = _append_blob_uploads(
                                doc_result.summary, doc_result.uploads,
                            )
                    except Exception:
                        logger.exception("openai_doc_gen_failed", agent=agent_name)
                    logger.info(
                        "openai_mcp_run_complete",
                        agent=agent_name,
                        rounds=round_num + 1,
                        response_length=len(final_text),
                        prompt_tokens=_total_prompt_tokens,
                        completion_tokens=_total_completion_tokens,
                    )
                    return {
                        "text": final_text,
                        "usage": {
                            "prompt_tokens": _total_prompt_tokens,
                            "completion_tokens": _total_completion_tokens,
                            "total_tokens": _total_prompt_tokens + _total_completion_tokens,
                            "llm_calls": _total_llm_calls,
                        },
                    }

                # Append the assistant message (with tool_calls)
                messages.append(message.model_dump())

                # Execute each tool call via MCP
                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    try:
                        fn_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        fn_args = {}

                    logger.info(
                        "openai_mcp_tool_call",
                        agent=agent_name,
                        tool=fn_name,
                        round=round_num + 1,
                        args_preview=str(fn_args)[:200],
                    )

                    # Notify progress: tool call starting
                    if on_progress:
                        try:
                            await on_progress(
                                agent_name, fn_name, "calling",
                                f"Calling {fn_name}..."
                            )
                        except Exception:
                            pass  # Non-fatal

                    try:
                        call_result = await session.call_tool(
                            fn_name, fn_args
                        )
                        tool_result = _extract_text_from_call_result(call_result)
                    except Exception as exc:
                        tool_result = f"Error calling {fn_name}: {exc}"
                        logger.exception(
                            "openai_mcp_tool_error",
                            agent=agent_name,
                            tool=fn_name,
                        )

                    logger.info(
                        "openai_mcp_tool_result",
                        agent=agent_name,
                        tool=fn_name,
                        result_length=len(tool_result),
                        result_preview=tool_result[:300],
                    )

                    # Notify progress: tool call completed
                    if on_progress:
                        try:
                            await on_progress(
                                agent_name, fn_name, "completed",
                                tool_result[:200],
                            )
                        except Exception:
                            pass  # Non-fatal

                    # Track blob uploads for download-link injection
                    if fn_name in _BLOB_UPLOAD_TOOLS:
                        blob_uploads.append(tool_result)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })

                # Update kwargs for next iteration
                kwargs["messages"] = messages

            # ── Exhausted rounds — get a summary ───────────────────
            logger.warning(
                "openai_mcp_run_max_rounds",
                agent=agent_name,
                max_rounds=_MAX_TOOL_ROUNDS,
            )
            kwargs.pop("tools", None)
            kwargs.pop("tool_choice", None)
            messages.append({
                "role": "user",
                "content": (
                    "Please provide your final summary based on the "
                    "tool results above."
                ),
            })
            kwargs["messages"] = messages

            try:
                response = await openai_client.chat.completions.create(**kwargs)
                _total_llm_calls += 1
                if hasattr(response, 'usage') and response.usage:
                    _total_prompt_tokens += getattr(response.usage, 'prompt_tokens', 0) or 0
                    _total_completion_tokens += getattr(response.usage, 'completion_tokens', 0) or 0
                final_text = response.choices[0].message.content or ""
                if blob_uploads:
                    final_text = _append_blob_uploads(
                        final_text, blob_uploads,
                    )
                # Auto-generate Word/Excel documents from report output
                # Show summary in chat, full details in document
                try:
                    doc_result = await generate_documents_with_summary(
                        final_text, agent_name, subtask_label=subtask_label,
                    )
                    if doc_result:
                        # Replace full text with summary + download links
                        final_text = _append_blob_uploads(
                            doc_result.summary, doc_result.uploads,
                        )
                except Exception:
                    logger.exception("openai_doc_gen_failed", agent=agent_name)
                return {
                    "text": final_text,
                    "usage": {
                        "prompt_tokens": _total_prompt_tokens,
                        "completion_tokens": _total_completion_tokens,
                        "total_tokens": _total_prompt_tokens + _total_completion_tokens,
                        "llm_calls": _total_llm_calls,
                    },
                }
            except Exception:
                logger.exception("openai_mcp_run_final_error", agent=agent_name)
                return {
                    "text": "Agent completed tool execution but failed to generate final summary.",
                    "usage": {
                        "prompt_tokens": _total_prompt_tokens,
                        "completion_tokens": _total_completion_tokens,
                        "total_tokens": _total_prompt_tokens + _total_completion_tokens,
                        "llm_calls": _total_llm_calls,
                    },
                }
