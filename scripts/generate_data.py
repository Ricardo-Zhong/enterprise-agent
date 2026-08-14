"""Generate deterministic, internally consistent data for NOVA Commerce."""

from __future__ import annotations

import argparse
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.commerce import Customer, Inventory, Order, OrderItem, OrderStatus, Product, Warehouse

FIRST_NAMES = ["Olivia", "Noah", "Mia", "Jack", "Amelia", "Leo", "Isla", "Henry", "Charlotte", "Luca"]
LAST_NAMES = ["Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Anderson", "Thomas", "Martin", "Lee"]
CATEGORIES = ["Home Office", "Mobile Accessories", "Audio", "Fitness", "Travel"]
WAREHOUSES = [
    ("SYD-01", "Sydney Distribution Centre", "Sydney", "NSW"),
    ("MEL-01", "Melbourne Distribution Centre", "Melbourne", "VIC"),
    ("BNE-01", "Brisbane Distribution Centre", "Brisbane", "QLD"),
    ("PER-01", "Perth Distribution Centre", "Perth", "WA"),
    ("ADL-01", "Adelaide Distribution Centre", "Adelaide", "SA"),
]


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def require_empty_database(session: SessionLocal) -> None:
    if session.scalar(select(Customer.id).limit(1)) is not None:
        raise RuntimeError("Database already has data. Do not seed it twice; use a fresh database for a new demo dataset.")


def create_customers(session: SessionLocal, count: int, rng: random.Random) -> list[Customer]:
    customers = []
    for index in range(1, count + 1):
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        customers.append(Customer(
            email=f"{first_name.lower()}.{last_name.lower()}{index}@example.com",
            first_name=first_name,
            last_name=last_name,
            phone=f"04{rng.randint(10_000_000, 99_999_999)}",
            created_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(1, 730)),
        ))
    session.add_all(customers)
    session.flush()
    return customers


def create_products(session: SessionLocal, count: int, rng: random.Random) -> list[Product]:
    products = []
    for index in range(1, count + 1):
        category = rng.choice(CATEGORIES)
        products.append(Product(
            sku=f"NOVA-{index:04d}",
            name=f"NOVA {category} Product {index:03d}",
            category=category,
            description=f"Synthetic NOVA Commerce {category.lower()} product, generated for agent development.",
            unit_price=Decimal(rng.randint(1999, 49999)) / Decimal(100),
        ))
    session.add_all(products)
    session.flush()
    return products


def create_warehouses(session: SessionLocal) -> list[Warehouse]:
    warehouses = [Warehouse(code=code, name=name, city=city, state=state) for code, name, city, state in WAREHOUSES]
    session.add_all(warehouses)
    session.flush()
    return warehouses


def create_inventory(session: SessionLocal, products: list[Product], warehouses: list[Warehouse], rng: random.Random) -> None:
    records = []
    for product in products:
        for warehouse in warehouses:
            on_hand = rng.randint(0, 250)
            records.append(Inventory(
                product_id=product.id,
                warehouse_id=warehouse.id,
                on_hand_quantity=on_hand,
                reserved_quantity=rng.randint(0, min(on_hand, 25)),
            ))
    session.add_all(records)


def create_orders(session: SessionLocal, customers: list[Customer], products: list[Product], count: int, rng: random.Random) -> None:
    statuses = list(OrderStatus)
    for index in range(1, count + 1):
        line_items = []
        for product in rng.sample(products, k=rng.randint(1, min(3, len(products)))):
            quantity = rng.randint(1, 3)
            line_items.append((product, quantity))
        subtotal = money(sum((product.unit_price * quantity for product, quantity in line_items), Decimal("0.00")))
        shipping_fee = Decimal("0.00") if subtotal >= Decimal("80.00") else Decimal("9.95")
        order = Order(
            order_number=f"NOVA-{100000 + index}",
            customer_id=rng.choice(customers).id,
            status=rng.choice(statuses),
            shipping_address=f"{rng.randint(1, 200)} Example Street, {rng.choice(['Sydney', 'Melbourne', 'Brisbane'])}",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total=money(subtotal + shipping_fee),
            created_at=datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 365)),
        )
        session.add(order)
        session.flush()
        session.add_all([
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_sku=product.sku,
                product_name=product.name,
                unit_price=product.unit_price,
                quantity=quantity,
            )
            for product, quantity in line_items
        ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NOVA Commerce demo data.")
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--products", type=int, default=500)
    parser.add_argument("--orders", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    with SessionLocal.begin() as session:
        require_empty_database(session)
        customers = create_customers(session, args.customers, rng)
        products = create_products(session, args.products, rng)
        warehouses = create_warehouses(session)
        create_inventory(session, products, warehouses, rng)
        create_orders(session, customers, products, args.orders, rng)
    print(f"Created {args.customers} customers, {args.products} products, {len(WAREHOUSES)} warehouses, and {args.orders} orders.")


if __name__ == "__main__":
    main()
