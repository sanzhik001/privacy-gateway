from src.llm_client import LLMProvider
from src.pipeline import process_message


class Spy(LLMProvider):
    name = "spy"

    def generate(self, masked_text):
        return "Ок"


def test_forgot_password_phrase_is_not_blocked():
    r = process_message("Забыл пароль и не могу войти.", Spy())
    assert r["status"] == "ok"
    assert "пароль" in r["masked"]


def test_real_password_is_masked_and_not_blocked():
    r = process_message("мой пароль: Secret123", Spy())
    assert r["status"] == "ok"
    assert "Secret123" not in r["masked"]
