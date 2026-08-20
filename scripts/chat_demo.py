"""Manual smoke test for the agent loop against real seed data.

Not part of the pytest suite on purpose: a live LLM's exact wording isn't
deterministic, so this is for eyeballing behavior, not asserting fixed output.

Usage:
    python -m scripts.chat_demo "Where is my order NOVA-100001?"   # one-shot
    python -m scripts.chat_demo                                     # interactive
"""

import sys

from app.agent.runtime import AgentTurnResult, run_agent_turn
from app.db.session import SessionLocal


def should_exit(question: str) -> bool:
    normalized = question.strip().lower()
    return not normalized or normalized in {"q", "quit", "exit", "bye", "goodbye", "close", "stop", "end", "terminate"}


def _print_result(result: AgentTurnResult) -> None:
    for i, call in enumerate(result.tool_calls, start=1):
        status = "ERROR" if call.is_error else "ok"
        print(f"  [tool call {i}] {call.name}({call.arguments}) -> {status}")
    print(f"agent> {result.text}")


def main() -> None:
    db = SessionLocal()
    try:
        if len(sys.argv) > 1:
            question = " ".join(sys.argv[1:])
            if should_exit(question):
                return
            print(f"you> {question}")
            _print_result(run_agent_turn(question, db))
            return

        while True:
            try:
                question = input("you> ").strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break

            if should_exit(question):
                print("Bye!")
                break

            _print_result(run_agent_turn(question, db))
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
