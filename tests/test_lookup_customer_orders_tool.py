import json

from app.db.session import SessionLocal
from app.models.commerce import Customer
from app.tools import execute_tool


def test_execute_tool_found_customer_is_not_an_error() -> None:
    db = SessionLocal()
    try:
        customer = db.query(Customer).first()
        assert customer is not None, "seed data required: run scripts.generate_data first"

        content, is_error = execute_tool(
            "lookup_customer_orders", {"customer_email": customer.email}, db
        )

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is True
    finally:
        db.close()


def test_execute_tool_missing_customer_is_not_an_error() -> None:
    """A nonexistent customer email is a normal business result, not a tool error."""
    db = SessionLocal()
    try:
        content, is_error = execute_tool(
            "lookup_customer_orders", {"customer_email": "nobody@example.com"}, db
        )

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is False
        assert payload["reason"] == "no_such_customer"
    finally:
        db.close()
