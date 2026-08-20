import pytest

from scripts.chat_demo import should_exit


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("", True),
        ("quit", True),
        ("exit", True),
        ("q", True),
        ("  quit  ", True),
        ("what is my order?", False),
    ],
)
def test_should_exit(question: str, expected: bool) -> None:
    assert should_exit(question) is expected
