"""Order-related business logic, independent of any LLM/agent concerns."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.commerce import Order
from app.schemas.orders import OrderItemOut, OrderStatusResult, ReturnOut, ShipmentOut


def get_order_status(db: Session, order_number: str) -> OrderStatusResult:
    """Look up a single order by its (case-insensitive) order number."""
    order = (
        db.query(Order)
        .filter(func.lower(Order.order_number) == order_number.strip().lower())
        .first()
    )

    if order is None:
        return OrderStatusResult(found=False, reason="no_such_order")

    shipment = None
    if order.shipment is not None:
        shipment = ShipmentOut(
            carrier=order.shipment.carrier,
            tracking_number=order.shipment.tracking_number,
            status=order.shipment.status.value,
            estimated_delivery_date=(
                order.shipment.estimated_delivery_date.isoformat()
                if order.shipment.estimated_delivery_date
                else None
            ),
            delivered_at=(
                order.shipment.delivered_at.isoformat()
                if order.shipment.delivered_at
                else None
            ),
        )

    return_request = None
    if order.return_request is not None:
        return_request = ReturnOut(
            reason=order.return_request.reason.value,
            status=order.return_request.status.value,
            requested_at=order.return_request.requested_at.isoformat(),
            refund_amount=(
                str(order.return_request.refund_amount)
                if order.return_request.refund_amount is not None
                else None
            ),
        )

    return OrderStatusResult(
        found=True,
        order_number=order.order_number,
        status=order.status.value,
        created_at=order.created_at.isoformat(),
        total=str(order.total),
        items=[
            OrderItemOut(
                sku=item.product_sku,
                name=item.product_name,
                quantity=item.quantity,
                unit_price=str(item.unit_price),
            )
            for item in order.items
        ],
        shipment=shipment,
        return_request=return_request,
    )
