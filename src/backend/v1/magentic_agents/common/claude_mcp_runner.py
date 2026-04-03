"""Claude + MCP Tool Runner — Executes agent tasks using Anthropic Claude with MCP tools.

Parallel to openai_mcp_runner.py but uses the Anthropic API with native
tool_use. Each agent's system prompt and MCP tool definitions are sent
to Claude, which decides which tools to call. Tool calls are forwarded
to the MCP server via the MCP SDK SSE client.
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

from .doc_generator import generate_and_upload_documents

logger = structlog.get_logger(__name__)

# Maximum tool-call rounds to prevent infinite loops
_MAX_TOOL_ROUNDS = 15

# Type alias for the progress callback
# (agent_name, tool_name, status, detail) -> None
ProgressCallback = Callable[
    [str, str, str, str],
    Coroutine[Any, Any, None],
]


def _mcp_tools_to_claude(
    tools: list[Any],
    requested_names: set[str] | None,
) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to Anthropic tool-use format."""
    claude_tools: list[dict[str, Any]] = []
    for tool in tools:
        name = tool.name
        if requested_names and name not in requested_names:
            continue

        description = (tool.description or f"MCP tool: {name}")[:1024]
        # MCP inputSchema is a JSON Schema dict
        input_schema = tool.inputSchema or {"type": "object", "properties": {}}

        claude_tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema,
        })
    return claude_tools


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
    # De-duplicate by (container, blob) in case the same blob was
    # uploaded more than once across retries.
    seen: set[tuple[str, str]] = set()
    unique: list[str] = []
    for raw in blob_uploads:
        try:
            obj = json.loads(raw)
            key = (obj.get("container", ""), obj.get("blob", ""))
            if key in seen:
                continue
            seen.add(key)
            # Check the raw JSON isn't already present in the LLM output
            if raw in final_text:
                continue
            unique.append(raw)
        except (json.JSONDecodeError, TypeError):
            continue

    if not unique:
        return final_text

    return final_text + "\n\n" + "\n".join(unique)


async def run_agent_with_claude(
    *,
    anthropic_client: Any,
    model: str,
    system_prompt: str,
    task: str,
    mcp_server_url: str,
    tool_names: list[str],
    agent_name: str = "agent",
    on_progress: ProgressCallback | None = None,
    subtask_label: str | None = None,
) -> dict[str, Any]:
    """Run an agent task using Anthropic Claude with MCP tool calling.

    This is the main entry point. It:
    1. Connects to the MCP server via SSE
    2. Lists tools and converts them to Claude tool-use format
    3. Sends the system prompt + task to Claude with tools
    4. Iterates through tool calls, executing them via MCP
    5. Returns the final text response

    Args:
        anthropic_client: An AsyncAnthropic client instance.
        model: The Claude model name (e.g. "claude-opus-4-20250514").
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
    _total_input_tokens = 0
    _total_output_tokens = 0
    _total_llm_calls = 0

    logger.info(
        "claude_mcp_run_start",
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
            claude_tools = _mcp_tools_to_claude(tools_result.tools, requested)

            logger.info(
                "claude_mcp_tools_resolved",
                agent=agent_name,
                total_mcp_tools=len(tools_result.tools),
                agent_tools=len(claude_tools),
            )

            # Track blob uploads so we can surface download links
            blob_uploads: list[str] = []

            # 2. Build initial messages
            messages: list[dict[str, Any]] = [
                {"role": "user", "content": task},
            ]

            kwargs: dict[str, Any] = {
                "model": model,
                "system": system_prompt,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 16384,
            }
            if claude_tools:
                kwargs["tools"] = claude_tools

            # 3. Iterative tool-calling loop
            #    Uses streaming to avoid Anthropic SDK timeout for
            #    long-running requests (SDK >= 0.85 raises ValueError
            #    when non-streaming requests may exceed 10 minutes).
            for round_num in range(_MAX_TOOL_ROUNDS):
                try:
                    async with anthropic_client.messages.stream(**kwargs) as stream:
                        response = await stream.get_final_message()
                except Exception as exc:
                    logger.error(
                        "claude_mcp_run_llm_error",
                        agent=agent_name,
                        round=round_num,
                        error_type=type(exc).__name__,
                        error_detail=str(exc)[:500],
                    )
                    raise

                # Accumulate token usage from this round
                _total_llm_calls += 1
                if hasattr(response, 'usage') and response.usage:
                    _total_input_tokens += getattr(response.usage, 'input_tokens', 0) or 0
                    _total_output_tokens += getattr(response.usage, 'output_tokens', 0) or 0

                # Check stop reason
                stop_reason = response.stop_reason

                # Extract text and tool_use blocks from content
                text_parts: list[str] = []
                tool_uses: list[Any] = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                    elif block.type == "tool_use":
                        tool_uses.append(block)

                # If no tool calls (end_turn or max_tokens), return final text
                if not tool_uses or stop_reason == "end_turn":
                    final_text = "\n".join(text_parts)
                    # Append blob upload metadata so frontend renders
                    # download links even if the LLM omits the raw JSON.
                    if blob_uploads:
                        final_text = _append_blob_uploads(
                            final_text, blob_uploads,
                        )
                    # Auto-generate Word/Excel documents from report output
                    try:
                        doc_uploads = await generate_and_upload_documents(
                            final_text, agent_name, subtask_label=subtask_label,
                        )
                        if doc_uploads:
                            blob_uploads.extend(doc_uploads)
                            final_text = _append_blob_uploads(
                                final_text, doc_uploads,
                            )
                    except Exception:
                        logger.exception("claude_doc_gen_failed", agent=agent_name)
                    logger.info(
                        "claude_mcp_run_complete",
                        agent=agent_name,
                        rounds=round_num + 1,
                        response_length=len(final_text),
                        prompt_tokens=_total_input_tokens,
                        completion_tokens=_total_output_tokens,
                    )
                    return {
                        "text": final_text,
                        "usage": {
                            "prompt_tokens": _total_input_tokens,
                            "completion_tokens": _total_output_tokens,
                            "total_tokens": _total_input_tokens + _total_output_tokens,
                            "llm_calls": _total_llm_calls,
                        },
                    }

                # Append the assistant message (with all content blocks).
                # We manually extract only the fields the API accepts —
                # model_dump() can include extra SDK-internal fields
                # (e.g. parsed_output) that cause 400 errors.
                serialized_content: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type == "text":
                        serialized_content.append({
                            "type": "text",
                            "text": block.text,
                        })
                    elif block.type == "tool_use":
                        serialized_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                messages.append({
                    "role": "assistant",
                    "content": serialized_content,
                })

                # Execute each tool call via MCP
                tool_results: list[dict[str, Any]] = []
                for tool_use in tool_uses:
                    fn_name = tool_use.name
                    fn_args = tool_use.input if isinstance(tool_use.input, dict) else {}
                    tool_use_id = tool_use.id

                    logger.info(
                        "claude_mcp_tool_call",
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
                        call_result = await session.call_tool(fn_name, fn_args)
                        tool_result_text = _extract_text_from_call_result(call_result)
                    except Exception as exc:
                        tool_result_text = f"Error calling {fn_name}: {exc}"
                        logger.exception(
                            "claude_mcp_tool_error",
                            agent=agent_name,
                            tool=fn_name,
                        )

                    logger.info(
                        "claude_mcp_tool_result",
                        agent=agent_name,
                        tool=fn_name,
                        result_length=len(tool_result_text),
                        result_preview=tool_result_text[:300],
                    )

                    # Notify progress: tool call completed
                    if on_progress:
                        try:
                            await on_progress(
                                agent_name, fn_name, "completed",
                                tool_result_text[:200],
                            )
                        except Exception:
                            pass  # Non-fatal

                    # Track blob uploads for download-link injection
                    if fn_name in _BLOB_UPLOAD_TOOLS:
                        blob_uploads.append(tool_result_text)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result_text,
                    })

                # Append tool results as a user message
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

                # Update kwargs for next iteration
                kwargs["messages"] = messages

            # ── Exhausted rounds — get a summary ───────────────────
            logger.warning(
                "claude_mcp_run_max_rounds",
                agent=agent_name,
                max_rounds=_MAX_TOOL_ROUNDS,
            )
            kwargs.pop("tools", None)
            messages.append({
                "role": "user",
                "content": (
                    "Please provide your final summary based on the "
                    "tool results above."
                ),
            })
            kwargs["messages"] = messages

            try:
                async with anthropic_client.messages.stream(**kwargs) as stream:
                    response = await stream.get_final_message()
                _total_llm_calls += 1
                if hasattr(response, 'usage') and response.usage:
                    _total_input_tokens += getattr(response.usage, 'input_tokens', 0) or 0
                    _total_output_tokens += getattr(response.usage, 'output_tokens', 0) or 0
                text_parts = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                final_text = "\n".join(text_parts)
                if blob_uploads:
                    final_text = _append_blob_uploads(
                        final_text, blob_uploads,
                    )
                # Auto-generate Word/Excel documents from report output
                try:
                    doc_uploads = await generate_and_upload_documents(
                        final_text, agent_name, subtask_label=subtask_label,
                    )
                    if doc_uploads:
                        final_text = _append_blob_uploads(
                            final_text, doc_uploads,
                        )
                except Exception:
                    logger.exception("claude_doc_gen_failed", agent=agent_name)
                return {
                    "text": final_text,
                    "usage": {
                        "prompt_tokens": _total_input_tokens,
                        "completion_tokens": _total_output_tokens,
                        "total_tokens": _total_input_tokens + _total_output_tokens,
                        "llm_calls": _total_llm_calls,
                    },
                }
            except Exception:
                logger.exception("claude_mcp_run_final_error", agent=agent_name)
                return {
                    "text": "Agent completed tool execution but failed to generate final summary.",
                    "usage": {
                        "prompt_tokens": _total_input_tokens,
                        "completion_tokens": _total_output_tokens,
                        "total_tokens": _total_input_tokens + _total_output_tokens,
                        "llm_calls": _total_llm_calls,
                    },
                }
