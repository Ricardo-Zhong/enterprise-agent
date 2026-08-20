from app.db.session import SessionLocal
from app.models.commerce import Customer, Order
from app.services.orders import lookup_customer_orders


def test_lookup_customer_orders_found() -> None:
    db = SessionLocal()
    try:
        customer = db.query(Customer).first()
        assert customer is not None, "seed data required: run scripts.generate_data first"

        result = lookup_customer_orders(db, customer.email.upper())

        assert result.found is True
        expected_count = (
            db.query(Order).filter(Order.customer_id == customer.id).count()
        )
        assert len(result.orders) == min(expected_count, 5)
    finally:
        db.close()


def test_lookup_customer_orders_sorted_most_recent_first() -> None:
    db = SessionLocal()
    try:
        customer = (
            db.query(Customer)
            .join(Order, Order.customer_id == Customer.id)
            .first()
        )
        assert customer is not None, "seed data required: run scripts.generate_data first"

        result = lookup_customer_orders(db, customer.email)

        dates = [order.created_at for order in result.orders]
        assert dates == sorted(dates, reverse=True)
    finally:
        db.close()


def test_lookup_customer_orders_not_found() -> None:
    db = SessionLocal()
    try:
        result = lookup_customer_orders(db, "nobody@example.com")

        assert result.found is False
        assert result.reason == "no_such_customer"
        assert result.orders == []
    finally:
        db.close()


def test_lookup_customer_orders_limit_is_clamped() -> None:
    db = SessionLocal()
    try:
        customer = db.query(Customer).first()
        assert customer is not None, "seed data required: run scripts.generate_data first"

        result = lookup_customer_orders(db, customer.email, limit=999)

        assert len(result.orders) <= 20
    finally:
        db.close()
