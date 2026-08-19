from app.db.session import SessionLocal
from app.models.commerce import Order, Shipment
from app.services.orders import get_order_status


def test_get_order_status_found() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Order).first()
        assert existing is not None, "seed data required: run scripts.generate_data first"

        result = get_order_status(db, existing.order_number.lower())

        assert result.found is True
        assert result.order_number == existing.order_number
        assert result.status == existing.status.value
        assert len(result.items) == len(existing.items)
    finally:
        db.close()


def test_get_order_status_includes_delivered_at() -> None:
    """Regression test: delivered_at was missing from ShipmentOut, which let
    the model fabricate a delivery date from created_at instead of admitting
    it didn't know (see docs/tool_contracts.md conventions)."""
    db = SessionLocal()
    try:
        existing = (
            db.query(Order)
            .join(Order.shipment)
            .filter(Shipment.delivered_at.isnot(None))
            .first()
        )
        assert existing is not None, "seed data required: need at least one delivered order"

        result = get_order_status(db, existing.order_number)

        assert result.shipment is not None
        assert result.shipment.delivered_at == existing.shipment.delivered_at.isoformat()
    finally:
        db.close()


def test_get_order_status_not_found() -> None:
    db = SessionLocal()
    try:
        result = get_order_status(db, "NOVA-000000")

        assert result.found is False
        assert result.reason == "no_such_order"
        assert result.order_number is None
    finally:
        db.close()
