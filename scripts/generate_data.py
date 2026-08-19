"""Generate deterministic, internally consistent data for NOVA Commerce.

设计原则(对应之前讨论的问题清单):
1. 订单状态和 created_at 挂钩,不是纯随机——订单越老,越可能已完成/已送达。
2. 库存不再独立随机生成:每个 SKU 先给一个初始库存(initial stock),
   订单按时间顺序生成时实时扣减对应仓库库存,最终 on_hand 是真实结果。
3. 新增 order_status_events,记录状态变更时间线,可用于"卡单预警"类工具。
4. 新增 shipments,状态与订单状态联动;故意留一部分 delayed / failed_delivery,
   给"异常检测 / 自动升级客服"逻辑提供可用数据。
5. 新增 returns,只从 delivered 订单里抽取一部分生成,带真实的退货原因分布。
6. Product 增加 cost_price,支撑定价/毛利率分析类工具。
7. Order 增加 fulfillment_warehouse_id,且发货仓库必须是该订单商品有库存的仓库。
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import random

from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.commerce import (
    Customer,
    Inventory,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusEvent,
    Product,
    Return,
    ReturnReason,
    ReturnStatus,
    Shipment,
    ShipmentStatus,
    Warehouse,
)

FIRST_NAMES = ["Olivia", "Kayla", "Rebekah", "Noah", "Mia", "Jack", "Amelia", "Leo", "Isla", "Henry", "Charlotte", "Luca"]
LAST_NAMES = ["Smith", "Jones", "Li", "Wong", "Chou", "Williams", "Brown", "Wilson", "Taylor", "Anderson", "Thomas", "Martin", "Lee"]
CATEGORIES = ["Home Office", "Mobile Accessories", "Audio", "Fitness", "Travel", "Clothing"]
CARRIERS = ["AusPost", "StarTrack", "Sendle", "CouriersPlease"]
RETURN_REASON_WEIGHTS = {
    ReturnReason.WRONG_SIZE: 0.35,
    ReturnReason.CHANGED_MIND: 0.25,
    ReturnReason.NOT_AS_DESCRIBED: 0.2,
    ReturnReason.QUALITY_ISSUE: 0.15,
    ReturnReason.DAMAGED: 0.05,
}
WAREHOUSES = [
    ("SYD-01", "Sydney Distribution Centre", "Sydney", "NSW"),
    ("MEL-01", "Melbourne Distribution Centre", "Melbourne", "VIC"),
    ("BNE-01", "Brisbane Distribution Centre", "Brisbane", "QLD"),
    ("PER-01", "Perth Distribution Centre", "Perth", "WA"),
    ("ADL-01", "Adelaide Distribution Centre", "Adelaide", "SA"),
]

NOW = datetime.now(timezone.utc)


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def weighted_choice(rng: random.Random, weights: dict) -> object:
    keys = list(weights.keys())
    values = list(weights.values())
    return rng.choices(keys, weights=values, k=1)[0]


def require_empty_database(session: SessionLocal) -> None:
    if session.scalar(select(Customer.id).limit(1)) is not None:
        raise RuntimeError(
            "Database already has data. Use --reset to wipe it, or point to a fresh database."
        )


def reset_database(session: SessionLocal) -> None:
    """按外键依赖顺序清空所有表，并重置 PostgreSQL 自增序列。"""
    session.execute(text("""
        TRUNCATE TABLE returns, shipments, order_status_events, order_items, orders,
        inventory, products, customers, warehouses
        RESTART IDENTITY CASCADE
    """))
    session.flush()


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
            created_at=NOW - timedelta(days=rng.randint(1, 730)),
        ))
    session.add_all(customers)
    session.flush()
    return customers


def create_products(session: SessionLocal, count: int, rng: random.Random) -> list[Product]:
    products = []
    for index in range(1, count + 1):
        category = rng.choice(CATEGORIES)
        unit_price = Decimal(rng.randint(1999, 49999)) / Decimal(100)
        # 成本按售价的 40%-60% 随机,给毛利率分析留数据基础
        cost_ratio = Decimal(rng.randint(40, 60)) / Decimal(100)
        products.append(Product(
            sku=f"NOVA-{index:04d}",
            name=f"NOVA {category} Product {index:03d}",
            category=category,
            description=f"Synthetic NOVA Commerce {category.lower()} product, generated for agent development.",
            unit_price=money(unit_price),
            cost_price=money(unit_price * cost_ratio),
        ))
    session.add_all(products)
    session.flush()
    return products


def create_warehouses(session: SessionLocal) -> list[Warehouse]:
    warehouses = [Warehouse(code=code, name=name, city=city, state=state) for code, name, city, state in WAREHOUSES]
    session.add_all(warehouses)
    session.flush()
    return warehouses


def create_initial_inventory(
    session: SessionLocal, products: list[Product], warehouses: list[Warehouse], rng: random.Random
) -> dict[tuple[int, int], Inventory]:
    """给每个 (product, warehouse) 组合一个初始库存,后续订单生成时会实时扣减。"""
    inventory_map: dict[tuple[int, int], Inventory] = {}
    for product in products:
        for warehouse in warehouses:
            inv = Inventory(
                product_id=product.id,
                warehouse_id=warehouse.id,
                on_hand_quantity=rng.randint(20, 300),
                reserved_quantity=0,
            )
            session.add(inv)
            inventory_map[(product.id, warehouse.id)] = inv
    session.flush()
    return inventory_map


def pick_fulfillment_warehouse(
    warehouses: list[Warehouse],
    inventory_map: dict[tuple[int, int], Inventory],
    product_id: int,
    quantity: int,
    rng: random.Random,
) -> Warehouse | None:
    """优先选有足够库存的仓库,找不到就返回 None(表示这个商品缺货,订单该走 backorder 逻辑)。"""
    candidates = [
        wh for wh in warehouses
        if inventory_map[(product_id, wh.id)].on_hand_quantity >= quantity
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


def status_timeline_for_age(age_days: int, rng: random.Random) -> tuple[OrderStatus, list[tuple[OrderStatus, int]]]:
    """
    根据订单距今天数,决定最终状态 + 状态变更时间线(每个状态相对 created_at 的偏移天数)。
    这是让"状态"和"时间"挂钩的核心函数,取代原来的纯随机 choice。
    """
    timeline = [(OrderStatus.PENDING, 0)]

    if age_days < 1:
        return OrderStatus.PENDING, timeline

    timeline.append((OrderStatus.PROCESSING, 1))
    if age_days < 2:
        return OrderStatus.PROCESSING, timeline

    ship_offset = rng.randint(1, 3)
    ship_day = 1 + ship_offset
    if age_days < ship_day:
        return OrderStatus.PROCESSING, timeline
    timeline.append((OrderStatus.SHIPPED, ship_day))

    deliver_offset = ship_offset + rng.randint(2, 5)
    roll = rng.random()

    if roll < 0.06:
        # 小比例订单卡在配送异常
        if age_days < deliver_offset:
            return OrderStatus.SHIPPED, timeline
        timeline.append((OrderStatus.DELAYED, deliver_offset))

        failed_day = deliver_offset + 3
        if age_days < failed_day:
            return OrderStatus.DELAYED, timeline
        timeline.append((OrderStatus.FAILED_DELIVERY, failed_day))
        return OrderStatus.FAILED_DELIVERY, timeline

    if age_days < deliver_offset:
        return OrderStatus.SHIPPED, timeline
    timeline.append((OrderStatus.OUT_FOR_DELIVERY, deliver_offset))

    delivered_day = deliver_offset + 1
    if age_days < delivered_day:
        return OrderStatus.OUT_FOR_DELIVERY, timeline
    timeline.append((OrderStatus.DELIVERED, delivered_day))

    return OrderStatus.DELIVERED, timeline


def create_orders(
    session: SessionLocal,
    customers: list[Customer],
    products: list[Product],
    warehouses: list[Warehouse],
    inventory_map: dict[tuple[int, int], Inventory],
    count: int,
    rng: random.Random,
) -> None:
    # 按时间顺序(从旧到新)生成,保证库存扣减符合先后顺序
    created_offsets = sorted((rng.randint(0, 365) for _ in range(count)), reverse=True)

    for index, days_ago in enumerate(created_offsets, start=1):
        created_at = NOW - timedelta(days=days_ago)
        candidate_products = rng.sample(products, k=rng.randint(1, min(3, len(products))))

        line_items = []
        fulfillment_warehouse = None
        for product in candidate_products:
            quantity = rng.randint(1, 3)
            wh = pick_fulfillment_warehouse(warehouses, inventory_map, product.id, quantity, rng)
            if wh is None:
                continue  # 该商品在所有仓库都缺货,跳过这一行(模拟真实缺货场景)
            if fulfillment_warehouse is None:
                fulfillment_warehouse = wh
            line_items.append((product, quantity))

        if not line_items:
            continue  # 整单都缺货,跳过(真实场景里这单会走 backorder,这里简化处理)

        subtotal = money(sum((p.unit_price * q for p, q in line_items), Decimal("0.00")))
        shipping_fee = Decimal("0.00") if subtotal >= Decimal("80.00") else Decimal("9.95")

        age_days = days_ago
        final_status, timeline = status_timeline_for_age(age_days, rng)

        order = Order(
            order_number=f"NOVA-{100000 + index}",
            customer_id=rng.choice(customers).id,
            status=final_status,
            shipping_address=f"{rng.randint(1, 200)} Example Street, {rng.choice(['Sydney', 'Melbourne', 'Brisbane'])}",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total=money(subtotal + shipping_fee),
            created_at=created_at,
            fulfillment_warehouse_id=fulfillment_warehouse.id if fulfillment_warehouse else None,
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

        # 扣减库存(只扣发货仓库的库存,模拟真实场景一单从一个仓库发货)
        if fulfillment_warehouse:
            for product, quantity in line_items:
                inv = inventory_map[(product.id, fulfillment_warehouse.id)]
                inv.on_hand_quantity = max(0, inv.on_hand_quantity - quantity)

        # 状态变更历史
        session.add_all([
            OrderStatusEvent(order_id=order.id, status=status, occurred_at=created_at + timedelta(days=offset))
            for status, offset in timeline
        ])

        # 物流记录:只有 processing 之后的订单才有
        shipped_statuses = {
            OrderStatus.SHIPPED, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED,
            OrderStatus.DELAYED, OrderStatus.FAILED_DELIVERY,
        }
        if final_status in shipped_statuses and fulfillment_warehouse:
            shipped_event = next((o for s, o in timeline if s == OrderStatus.SHIPPED), None)
            shipped_at = created_at + timedelta(days=shipped_event) if shipped_event is not None else None
            estimated_delivery = (shipped_at + timedelta(days=rng.randint(2, 5))) if shipped_at else None
            delivered_event = next((o for s, o in timeline if s == OrderStatus.DELIVERED), None)
            delivered_at = created_at + timedelta(days=delivered_event) if delivered_event is not None else None

            shipment_status_map = {
                OrderStatus.SHIPPED: ShipmentStatus.IN_TRANSIT,
                OrderStatus.OUT_FOR_DELIVERY: ShipmentStatus.OUT_FOR_DELIVERY,
                OrderStatus.DELIVERED: ShipmentStatus.DELIVERED,
                OrderStatus.DELAYED: ShipmentStatus.DELAYED,
                OrderStatus.FAILED_DELIVERY: ShipmentStatus.FAILED_DELIVERY,
            }
            session.add(Shipment(
                order_id=order.id,
                carrier=rng.choice(CARRIERS),
                tracking_number=f"TRK{rng.randint(10_000_000, 99_999_999)}",
                status=shipment_status_map[final_status],
                shipped_at=shipped_at,
                estimated_delivery_date=estimated_delivery,
                delivered_at=delivered_at,
            ))

        # 退货记录:只从 delivered 订单里抽 8% 左右生成
        if final_status == OrderStatus.DELIVERED and rng.random() < 0.08:
            requested_at = created_at + timedelta(days=rng.randint(6, 25))
            resolved = rng.random() < 0.7
            if resolved:
                # 已处理完的退货:大多数退款,少部分被拒
                status = weighted_choice(rng, {
                    ReturnStatus.REFUNDED: 0.7,
                    ReturnStatus.REJECTED: 0.3,
                })
            else:
                # 还没处理完的退货:只能是"已申请"或"已批准待退款"这类非终态
                status = weighted_choice(rng, {
                    ReturnStatus.REQUESTED: 0.6,
                    ReturnStatus.APPROVED: 0.4,
                })
            session.add(Return(
                order_id=order.id,
                reason=weighted_choice(rng, RETURN_REASON_WEIGHTS),
                status=status,
                requested_at=requested_at,
                resolved_at=requested_at + timedelta(days=rng.randint(1, 5)) if resolved else None,
                refund_amount=order.total if status == ReturnStatus.REFUNDED else None,
            ))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NOVA Commerce demo data.")
    parser.add_argument("--customers", type=int, default=1000)
    parser.add_argument("--products", type=int, default=500)
    parser.add_argument("--orders", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--reset", action="store_true", help="清空数据库后重新生成,方便重复调试")
    args = parser.parse_args()

    if args.customers <= 0 or args.products <= 0 or args.orders <= 0:
        raise SystemExit("--customers / --products / --orders 必须大于 0")

    rng = random.Random(args.seed)
    with SessionLocal.begin() as session:
        if args.reset:
            reset_database(session)
        else:
            require_empty_database(session)

        customers = create_customers(session, args.customers, rng)
        products = create_products(session, args.products, rng)
        warehouses = create_warehouses(session)
        inventory_map = create_initial_inventory(session, products, warehouses, rng)
        create_orders(session, customers, products, warehouses, inventory_map, args.orders, rng)

    print(
        f"Created {args.customers} customers, {args.products} products, "
        f"{len(WAREHOUSES)} warehouses, up to {args.orders} orders "
        f"(some skipped due to simulated stockouts)."
    )


if __name__ == "__main__":
    main()