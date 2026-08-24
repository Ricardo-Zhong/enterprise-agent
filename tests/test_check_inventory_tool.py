import json

from app.db.session import SessionLocal
from app.models.commerce import Product
from app.tools import execute_tool


def test_execute_tool_found_sku_is_not_an_error() -> None:
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "seed data required: run scripts.generate_data first"

        content, is_error = execute_tool("check_inventory", {"sku": product.sku}, db)

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is True
        assert payload["sku"] == product.sku
    finally:
        db.close()


def test_execute_tool_missing_sku_is_not_an_error() -> None:
    """A nonexistent SKU is a normal business result, not a tool error."""
    db = SessionLocal()
    try:
        content, is_error = execute_tool("check_inventory", {"sku": "NOVA-9999"}, db)

        assert is_error is False
        payload = json.loads(content)
        assert payload["found"] is False
        assert payload["reason"] == "no_such_sku"
    finally:
        db.close()
