from app.db.session import SessionLocal
from app.models.commerce import Inventory, Product
from app.services.inventory import check_inventory


def test_check_inventory_found() -> None:
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "seed data required: run scripts.generate_data first"

        expected_warehouse_count = (
            db.query(Inventory).filter(Inventory.product_id == product.id).count()
        )

        result = check_inventory(db, product.sku)

        assert result.found is True
        assert result.sku == product.sku
        assert len(result.warehouses) == expected_warehouse_count
    finally:
        db.close()


def test_check_inventory_available_quantity_is_on_hand_minus_reserved() -> None:
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "seed data required: run scripts.generate_data first"

        result = check_inventory(db, product.sku)

        inventory_by_warehouse_code = {
            row.warehouse.code: row
            for row in db.query(Inventory).filter(Inventory.product_id == product.id).all()
        }
        for wh in result.warehouses:
            row = inventory_by_warehouse_code[wh.warehouse_code]
            assert wh.on_hand_quantity == row.on_hand_quantity
            assert wh.available_quantity == row.on_hand_quantity - row.reserved_quantity
    finally:
        db.close()


def test_check_inventory_filtered_by_state() -> None:
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "seed data required: run scripts.generate_data first"

        result = check_inventory(db, product.sku, state="nsw")

        assert result.found is True
        assert all(wh.state == "NSW" for wh in result.warehouses)
    finally:
        db.close()


def test_check_inventory_sku_is_case_sensitive() -> None:
    """The contract promises exact match, unlike order_number/customer_email."""
    db = SessionLocal()
    try:
        product = db.query(Product).first()
        assert product is not None, "seed data required: run scripts.generate_data first"

        result = check_inventory(db, product.sku.lower())

        assert result.found is False
    finally:
        db.close()


def test_check_inventory_not_found() -> None:
    db = SessionLocal()
    try:
        result = check_inventory(db, "NOVA-9999")

        assert result.found is False
        assert result.reason == "no_such_sku"
        assert result.warehouses == []
    finally:
        db.close()
