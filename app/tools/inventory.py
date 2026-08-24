"""tool_use definitions and handlers for inventory-related tools."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.inventory import check_inventory

CHECK_INVENTORY_TOOL = {
    "name": "check_inventory",
    "description": (
        "Check stock levels for a product SKU across warehouses. Optionally "
        "filter to a state to check local availability. Use this to answer "
        "'is X in stock' or 'where can I get X shipped from' questions. "
        "Returns found=false if the SKU doesn't exist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sku": {
                "type": "string",
                "description": "Product SKU, exact match.",
            },
            "state": {
                "type": "string",
                "description": "Optional two-letter Australian state code (e.g. 'NSW') to filter warehouses.",
            },
        },
        "required": ["sku"],
    },
}


def handle_check_inventory(tool_input: dict, db: Session) -> str:
    result = check_inventory(db, tool_input["sku"], state=tool_input.get("state"))
    return result.model_dump_json()
