"""Inventory-related business logic, independent of any LLM/agent concerns."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.commerce import Inventory, Product, Warehouse
from app.schemas.inventory import InventoryResult, WarehouseStockOut


def check_inventory(db: Session, sku: str, state: str | None = None) -> InventoryResult:
    """Check stock levels for a SKU across warehouses, optionally filtered by state.

    Unlike order_number/customer_email, sku matching is case-sensitive exact
    match — that's what the tool contract promises the model.
    """
    product = db.query(Product).filter(Product.sku == sku.strip()).first()

    if product is None:
        return InventoryResult(found=False, reason="no_such_sku")

    query = (
        db.query(Inventory, Warehouse)
        .join(Warehouse, Inventory.warehouse_id == Warehouse.id)
        .filter(Inventory.product_id == product.id)
    )
    if state:
        query = query.filter(Warehouse.state == state.strip().upper())

    rows = query.all()

    return InventoryResult(
        found=True,
        sku=product.sku,
        warehouses=[
            WarehouseStockOut(
                warehouse_code=warehouse.code,
                city=warehouse.city,
                state=warehouse.state,
                on_hand_quantity=inventory.on_hand_quantity,
                available_quantity=inventory.on_hand_quantity - inventory.reserved_quantity,
            )
            for inventory, warehouse in rows
        ],
    )
