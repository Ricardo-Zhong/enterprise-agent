"""Manual smoke test for the agent loop against real seed data.

Not part of the pytest suite on purpose: a live LLM's exact wording isn't
deterministic, so this is for eyeballing behavior, not asserting fixed output.

Usage:
    python -m scripts.chat_demo "Where is my order NOVA-100001?"   # one-shot
    python -m scripts.chat_demo                                     # interactive
"""

import sys

from app.agent.runtime import run_agent_turn
from app.db.session import SessionLocal


def main() -> None:
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            question = " ".join(sys.argv[1:])
            print(f"you> {question}")
            print(f"agent> {run_agent_turn(question, db)}")
            return

        while True:
            question = input("you> ").strip()
            if not question:
                break
            print(f"agent> {run_agent_turn(question, db)}\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
