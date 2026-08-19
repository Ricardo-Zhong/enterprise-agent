"""Output shapes for order-related services and tools."""

from __future__ import annotations

from pydantic import BaseModel


class OrderItemOut(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: str


class ShipmentOut(BaseModel):
    carrier: str
    tracking_number: str
    status: str
    estimated_delivery_date: str | None = None
    delivered_at: str | None = None


class ReturnOut(BaseModel):
    reason: str
    status: str
    requested_at: str
    refund_amount: str | None = None


class OrderStatusResult(BaseModel):
    """Matches the get_order_status tool contract in docs/tool_contracts.md."""

    found: bool
    reason: str | None = None
    order_number: str | None = None
    status: str | None = None
    created_at: str | None = None
    total: str | None = None
    items: list[OrderItemOut] = []
    shipment: ShipmentOut | None = None
    return_request: ReturnOut | None = None
