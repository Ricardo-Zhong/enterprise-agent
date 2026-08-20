"""Central registry: maps tool names to their tool_use definitions and Python
handlers, and dispatches execution so that a handler failure always becomes a
structured (content, is_error) pair instead of an uncaught exception reaching
the agent loop.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.tools.orders import (
    GET_ORDER_STATUS_TOOL,
    LOOKUP_CUSTOMER_ORDERS_TOOL,
    handle_get_order_status,
    handle_lookup_customer_orders,
)

logger = logging.getLogger(__name__)

TOOL_DEFINITIONS = [GET_ORDER_STATUS_TOOL, LOOKUP_CUSTOMER_ORDERS_TOOL]

_HANDLERS: dict[str, Callable[[dict, Session], str]] = {
    "get_order_status": handle_get_order_status,
    "lookup_customer_orders": handle_lookup_customer_orders,
}


def execute_tool(name: str, tool_input: dict, db: Session) -> tuple[str, bool]:
    """Run a tool by name. Returns (content, is_error). Never raises."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"Unknown tool: {name}", True

    try:
        return handler(tool_input, db), False
    except Exception:
        logger.exception("Tool '%s' failed with input=%r", name, tool_input)
        return "Internal error executing tool.", True
