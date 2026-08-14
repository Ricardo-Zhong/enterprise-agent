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
