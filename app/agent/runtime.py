"""The tool_use loop: send a message, execute any tools the model calls, feed
the results back, and repeat until the model produces a final text answer.

Provider-agnostic: which LLM backend (cloud Anthropic or local Ollama) is
used is decided by app.agent.providers.get_provider, based on the
AGENT_PROVIDER setting. This module only deals in the normalized
AssistantTurn/ToolCall/ToolResult shapes and never sees a provider's native
request/response format.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.agent.providers import ToolResult, get_provider
from app.tools import execute_tool

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a customer support assistant for NOVA Commerce, an Australian "
    "e-commerce company. Use the available tools to look up real order, "
    "customer, and inventory data before answering. Never guess at order "
    "numbers, statuses, or stock levels. If a tool result does not include a "
    "piece of information the user asked for (e.g. an exact date), say you "
    "don't have that information instead of inferring or guessing it from "
    "other fields."
)

MAX_TOOL_ITERATIONS = 5


@dataclass
class ToolCallRecord:
    """One executed tool call, kept for inspection/testing — not sent back
    to the model (that's what ToolResult is for)."""

    name: str
    arguments: dict
    result: str
    is_error: bool


@dataclass
class AgentTurnResult:
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


def run_agent_turn(user_message: str, db: Session) -> AgentTurnResult:
    """Run one user turn to completion, including any tool calls.

    Returns the model's final text reply plus a record of every tool call
    made along the way, in the order they happened.
    """
    provider = get_provider(SYSTEM_PROMPT)
    turn = provider.send_user_message(user_message)
    call_log: list[ToolCallRecord] = []

    for _ in range(MAX_TOOL_ITERATIONS):
        if not turn.tool_calls:
            return AgentTurnResult(text=turn.text or "", tool_calls=call_log)

        results = []
        for call in turn.tool_calls:
            logger.info("Model called tool %s with input %r", call.name, call.arguments)
            content, is_error = execute_tool(call.name, call.arguments, db)
            call_log.append(
                ToolCallRecord(
                    name=call.name, arguments=call.arguments, result=content, is_error=is_error
                )
            )
            results.append(
                ToolResult(id=call.id, name=call.name, content=content, is_error=is_error)
            )

        turn = provider.send_tool_results(results)

    return AgentTurnResult(
        text="I wasn't able to finish that request after several tool calls. Please try rephrasing.",
        tool_calls=call_log,
    )
