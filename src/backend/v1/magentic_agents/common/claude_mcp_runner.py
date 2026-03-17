"""Claude + MCP Tool Runner — Executes agent tasks using Anthropic Claude with MCP tools.

Parallel to openai_mcp_runner.py but uses the Anthropic API with native
tool_use. Each agent's system prompt and MCP tool definitions are sent
to Claude, which decides which tools to call. Tool calls are forwarded
to the MCP server via the MCP SDK SSE client.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Coroutine

import structlog
from mcp import ClientSession
from mcp.client.sse import sse_client

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
) -> str:
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
        The final text response from Claude after all tool calls.
    """
    sse_url = f"{mcp_server_url.rstrip('/')}/sse"
    requested = set(tool_names) if tool_names else None

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
                    logger.info(
                        "claude_mcp_run_complete",
                        agent=agent_name,
                        rounds=round_num + 1,
                        response_length=len(final_text),
                    )
                    return final_text

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
                text_parts = []
                for block in response.content:
                    if block.type == "text":
                        text_parts.append(block.text)
                return "\n".join(text_parts)
            except Exception:
                logger.exception("claude_mcp_run_final_error", agent=agent_name)
                return (
                    "Agent completed tool execution but failed to "
                    "generate final summary."
                )
