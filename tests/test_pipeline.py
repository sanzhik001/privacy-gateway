from src.llm_client import LLMProvider
from src.pipeline import process_message


class SpyProvider(LLMProvider):
    """Запоминает всё, что получил. Ничего не отправляет в сеть."""
    name = "spy"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return "Ок"


def test_provider_never_sees_originals():
    spy = SpyProvider()
    text = ("Меня зовут Айгерим, телефон +7 701 234 56 78, "
            "пароль: Secret123, карта 4111 1111 1111 1111, "
            "почта test@example.com")
    process_message(text, spy)
    assert spy.received
    for original in ["Айгерим", "+7 701 234 56 78", "Secret123",
                     "4111 1111 1111 1111", "test@example.com"]:
        assert all(original not in r for r in spy.received)


def test_date_in_text_is_not_a_leak():
    result = process_message("Встреча 2026-10-12", SpyProvider())
    assert result["status"] == "ok"


def test_name_repeated_without_trigger_never_reaches_provider():
    spy = SpyProvider()
    process_message("Меня зовут Айгерим. Айгерим любит чай.", spy)
    assert all("Айгерим" not in r for r in spy.received)