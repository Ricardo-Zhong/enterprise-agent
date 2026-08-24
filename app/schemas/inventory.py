"""Output shapes for inventory-related services and tools."""

from __future__ import annotations

from pydantic import BaseModel


class WarehouseStockOut(BaseModel):
    warehouse_code: str
    city: str
    state: str
    on_hand_quantity: int
    available_quantity: int


class InventoryResult(BaseModel):
    """Matches the check_inventory tool contract in docs/tool_contracts.md."""

    found: bool
    reason: str | None = None
    sku: str | None = None
    warehouses: list[WarehouseStockOut] = []
