"""tool_use definitions and handlers for order-related tools."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.orders import get_order_status, lookup_customer_orders

GET_ORDER_STATUS_TOOL = {
    "name": "get_order_status",
    "description": (
        "Look up a single order's status, items, and shipment info by its exact "
        "order number. Use this only when the user has provided or referenced a "
        "specific order number (e.g. 'NOVA-2024-00123'). If the user hasn't given "
        "an order number, ask them for one or use lookup_customer_orders instead. "
        "Returns found=false if the order number does not exist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order_number": {
                "type": "string",
                "description": "Exact order number, e.g. 'NOVA-2024-00123'. Case-insensitive.",
            }
        },
        "required": ["order_number"],
    },
}


def handle_get_order_status(tool_input: dict, db: Session) -> str:
    result = get_order_status(db, tool_input["order_number"])
    return result.model_dump_json()


LOOKUP_CUSTOMER_ORDERS_TOOL = {
    "name": "lookup_customer_orders",
    "description": (
        "List a customer's recent orders (order number, status, total, date) "
        "by their email address. Use this when the user asks about 'my "
        "orders' or 'recent orders' without giving a specific order number. "
        "This returns summaries only — call get_order_status with the "
        "order_number if the user wants full detail on one of them."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_email": {
                "type": "string",
                "description": "Customer's email address.",
            },
            "limit": {
                "type": "integer",
                "description": "Max orders to return, default 5, max 20.",
                "minimum": 1,
                "maximum": 20,
            },
        },
        "required": ["customer_email"],
    },
}


def handle_lookup_customer_orders(tool_input: dict, db: Session) -> str:
    result = lookup_customer_orders(
        db,
        tool_input["customer_email"],
        limit=tool_input.get("limit", 5),
    )
    return result.model_dump_json()
