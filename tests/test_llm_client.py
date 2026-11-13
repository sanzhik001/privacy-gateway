import pytest

from src.llm_client import get_provider


def test_mock_provider_returns_text():
    answer = get_provider("mock").generate("привет [PHONE_1#abc123]")
    assert "[PHONE_1#abc123]" in answer


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_provider("несуществующий")