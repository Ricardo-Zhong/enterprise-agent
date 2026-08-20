"""Live smoke test: actually calls the configured LLM backend and prints the
reply. Excluded from the default `pytest` run (see pytest.ini) because it's
slow and its exact wording isn't deterministic. Run it explicitly:

    pytest tests/test_agent_runtime_live.py -m live_llm -s -v
"""

import pytest

from app.agent.runtime import run_agent_turn
from app.db.session import SessionLocal
from app.models.commerce import Order


@pytest.mark.live_llm
def test_agent_answers_a_real_order_question() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Order).first()
        assert existing is not None, "seed data required: run scripts.generate_data first"

        question = f"What is the status of order {existing.order_number}? Who is the customer and what items did they order?    "
        result = run_agent_turn(question, db)

        print(f"\nyou> {question}")
        for call in result.tool_calls:
            print(f"  [tool call] {call.name}({call.arguments})")
        print(f"agent> {result.text}")

        assert isinstance(result.text, str)
        assert len(result.text) > 0
        assert len(result.tool_calls) > 0, "expected the model to call at least one tool"
    finally:
        db.close()
