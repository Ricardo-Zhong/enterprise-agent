# Tool Contracts

Design-time reference for agent tools before they are implemented. Every tool
should be filled into this template and reviewed here *before* writing the
corresponding `app/services/*.py` and `app/tools/*.py` code.

Target tool-calling interface: Anthropic Messages API `tool_use`
(`input_schema` blocks below follow that JSON Schema format directly).

## Design checklist (fill this in for every new tool)

1. **name** — verb_noun, snake_case
2. **One-line purpose**
3. **When to use / when NOT to use** — especially the boundary with similar tools
4. **input_schema** — JSON Schema: types, required fields, formats, enums
5. **Success output shape**
6. **"Not found" / empty-result output shape** (a normal business result, not an error)
7. **Error output shape** (caught by the tool-execution layer, returned with `is_error: true`, never an uncaught exception)
8. **Side effects** — read-only or write? idempotent?
9. **Authorization / scope** — what data boundary does this tool enforce (e.g. current `customer_id`)?
10. **Response size** — does this need pagination/truncation to stay token-cheap?

## Conventions used across all tools

- Dates/timestamps: ISO 8601 strings (e.g. `"2024-11-02T03:15:00Z"`), never raw `datetime` objects or mixed formats.
- Money: strings (e.g. `"129.99"`), never floats — avoids float-precision artifacts reaching the model.
- "Not found" and "error" are different things: not-found is a normal `found: false` business result; error means the tool execution itself failed (DB down, bad input) and must be caught, not raised into the agent loop.
- If a tool omits a field the model might be asked about, the model may fabricate a plausible-looking value from other fields rather than admitting it doesn't know (observed live: it reused `created_at` as a delivery date when `delivered_at` was missing). Contracts should include every field a user could reasonably ask about, and the system prompt should explicitly instruct the model to say "I don't have that" rather than infer.
- Prefer list tools returning summaries only, with a separate detail tool for drill-down, rather than one tool returning deeply nested payloads.
- Once a tool's schema is in use, treat it like a versioned API — removing/renaming required fields is a breaking change.

---

## `get_order_status`

**Purpose**: Look up a single order's status, items, and shipment info by its exact order number.

**When to use**: The user has provided or referenced a specific order number.
**When NOT to use**: The user hasn't given an order number (e.g. "my recent orders") — use `lookup_customer_orders` instead. Don't guess an order number.

```json
{
  "name": "get_order_status",
  "description": "Look up a single order's status, items, and shipment info by its exact order number. Use this only when the user has provided or referenced a specific order number (e.g. 'NOVA-2024-00123'). If the user hasn't given an order number, ask them for one or use lookup_customer_orders instead. Returns found=false if the order number does not exist.",
  "input_schema": {
    "type": "object",
    "properties": {
      "order_number": {
        "type": "string",
        "description": "Exact order number, e.g. 'NOVA-2024-00123'. Case-insensitive."
      }
    },
    "required": ["order_number"]
  }
}
```

Success output:
```json
{
  "found": true,
  "order_number": "NOVA-2024-00123",
  "status": "shipped",
  "created_at": "2024-11-02T03:15:00Z",
  "total": "129.99",
  "items": [
    {"sku": "NC-SHOE-042", "name": "...", "quantity": 1, "unit_price": "129.99"}
  ],
  "shipment": {
    "carrier": "AusPost",
    "tracking_number": "...",
    "status": "in_transit",
    "estimated_delivery_date": "2024-11-08",
    "delivered_at": null
  },
  "return_request": null
}
```

`delivered_at` is null until the shipment actually has a delivery timestamp; do not confuse it with `estimated_delivery_date`. This field was added after a live test showed the model fabricating a delivery date from `created_at` when it was missing — see the "Conventions" note below.

Not found:
```json
{"found": false, "reason": "no_such_order"}
```

Not authorized (if the order exists but doesn't belong to the current session's customer — deliberately does NOT reveal that the order exists, to avoid leaking other customers' data):
```json
{"found": false, "reason": "not_authorized"}
```

- **Side effects**: read-only
- **Authorization**: must verify the order belongs to the current `customer_id` in context, if the caller is a customer-scoped session
- **Response size**: single order, no pagination needed

---

## `lookup_customer_orders`

**Purpose**: List a customer's recent orders (summaries only) by email address.

**When to use**: The user asks about "my orders" / "recent orders" without a specific order number.
**When NOT to use**: The user wants full detail on one known order — call `get_order_status` instead.

```json
{
  "name": "lookup_customer_orders",
  "description": "List a customer's recent orders (order number, status, total, date) by their email address. Use this when the user asks about 'my orders' or 'recent orders' without giving a specific order number. This returns summaries only — call get_order_status with the order_number if the user wants full detail on one of them.",
  "input_schema": {
    "type": "object",
    "properties": {
      "customer_email": {"type": "string", "description": "Customer's email address."},
      "limit": {"type": "integer", "description": "Max orders to return, default 5, max 20.", "minimum": 1, "maximum": 20}
    },
    "required": ["customer_email"]
  }
}
```

Success output:
```json
{
  "found": true,
  "orders": [
    {"order_number": "NOVA-2024-00123", "status": "shipped", "total": "129.99", "created_at": "2024-11-02T03:15:00Z"}
  ]
}
```

Not found (no customer with that email, or customer has zero orders — consider whether these two cases need distinct `reason` values):
```json
{"found": false, "reason": "no_such_customer"}
```

- **Side effects**: read-only
- **Authorization**: same customer-scope question as above — decide whether `customer_email` is trusted input or must match the session's own identity
- **Response size**: capped by `limit` (default 5, max 20) — deliberately summaries only, not full item/shipment detail

---

## `check_inventory`

**Purpose**: Check stock levels for a product SKU across warehouses, optionally filtered by state.

**When to use**: "Is X in stock" / "where can X ship from" questions.

```json
{
  "name": "check_inventory",
  "description": "Check stock levels for a product SKU across warehouses. Optionally filter to a state to check local availability. Use this to answer 'is X in stock' or 'where can I get X shipped from' questions. Returns not_found if the SKU doesn't exist.",
  "input_schema": {
    "type": "object",
    "properties": {
      "sku": {"type": "string", "description": "Product SKU, exact match."},
      "state": {"type": "string", "description": "Optional two-letter Australian state code (e.g. 'NSW') to filter warehouses."}
    },
    "required": ["sku"]
  }
}
```

Success output (`available_quantity` is pre-computed as `on_hand - reserved` by the service layer — never let the model do this arithmetic):
```json
{
  "found": true,
  "sku": "NC-SHOE-042",
  "warehouses": [
    {"warehouse_code": "SYD1", "city": "Sydney", "state": "NSW", "on_hand_quantity": 42, "available_quantity": 37}
  ]
}
```

Not found:
```json
{"found": false, "reason": "no_such_sku"}
```

- **Side effects**: read-only
- **Authorization**: none (product/inventory data isn't customer-scoped)
- **Response size**: bounded by warehouse count (currently 5 per README) — no pagination needed yet

---

## Not yet designed

- Write-style tools (cancel order, initiate return/refund) — deliberately deferred until read-only tools are working end-to-end; these need a separate confirmation/approval design.
- Policy/RAG lookup tool (pgvector-backed) — mentioned in the planned architecture but not started.
