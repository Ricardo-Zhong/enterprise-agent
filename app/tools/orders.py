"""tool_use definitions and handlers for order-related tools."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.orders import get_order_status

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
