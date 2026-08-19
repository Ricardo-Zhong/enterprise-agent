import json

from app.db.session import SessionLocal
from app.models.commerce import Order
from app.tools import TOOL_DEFINITIONS, execute_tool


def test_tool_definitions_include_get_order_status() -> None:
    names = [tool["name"] for tool in TOOL_DEFINITIONS]
    assert "get_order_status" in names


def test_execute_tool_found_order_is_not_an_error() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Order).first()
        assert existing is not None, "seed data required: run scripts.generate_data first"

        content, is_error = execute_tool(
            "get_order_status", {"order_number": existing.order_number}, db
        )

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is True
        assert payload["order_number"] == existing.order_number
    finally:
        db.close()


def test_execute_tool_missing_order_is_not_an_error() -> None:
    """A nonexistent order number is a normal business result, not a tool error."""
    db = SessionLocal()
    try:
        content, is_error = execute_tool(
            "get_order_status", {"order_number": "NOVA-000000"}, db
        )

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is False
        assert payload["reason"] == "no_such_order"
    finally:
        db.close()


def test_execute_tool_unknown_tool_name_is_an_error() -> None:
    db = SessionLocal()
    try:
        content, is_error = execute_tool("cancel_order", {}, db)

        assert is_error is True
        assert "Unknown tool" in content
    finally:
        db.close()


def test_execute_tool_bad_input_is_caught_as_an_error() -> None:
    """A handler crash (e.g. missing required key) must not raise past execute_tool."""
    db = SessionLocal()
    try:
        content, is_error = execute_tool("get_order_status", {}, db)

        assert is_error is True
        assert content == "Internal error executing tool."
    finally:
        db.close()
