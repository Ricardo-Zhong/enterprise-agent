# Enterprise AI Agent

A production-oriented learning project for NOVA Commerce, a synthetic Australian e-commerce company. It will combine relational business data, policy retrieval, and safe agent tool use.

## Day 1: run the foundation

1. Activate the Python virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Start PostgreSQL with pgvector: `docker compose up -d`
5. Run the API: `uvicorn app.main:app --reload`
6. Check [http://localhost:8000/health](http://localhost:8000/health) and [http://localhost:8000/docs](http://localhost:8000/docs).

## Planned architecture

```text
FastAPI API -> Agent runtime -> SQL tools / RAG tools -> PostgreSQL + pgvector
```

Day 2 adds the NOVA Commerce database schema and synthetic data generator.

## Day 2: create NOVA Commerce data

The structured business data lives in PostgreSQL. Policies and SOPs will be added separately as retrieval documents in the next stage.

```bash
python -m scripts.init_db
python -m scripts.generate_data
```

The default generator creates 1,000 customers, 500 products, 5 warehouses and 10,000 orders. For a quick local check, use:

```bash
python -m scripts.generate_data --customers 20 --products 30 --orders 100
```

The generator intentionally refuses to run if the database already has customers, preventing accidental duplicate demo data.
