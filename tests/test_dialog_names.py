from src.llm_client import LLMProvider
from src.more_rules import UltimateSession
from src.pipeline import process_message


class Quiet(LLMProvider):
    name = "quiet"

    def generate(self, masked_text):
        return "ok"


def test_greeting_after_speaker_label_is_not_a_name():
    m = UltimateSession().mask("Клиент: Здравствуйте, меня зовут Алибек.")
    assert "Здравствуйте" in m
    assert "Алибек" not in m


def test_service_word_after_speaker_label_is_not_a_name():
    assert "Счёт" in UltimateSession().mask("Клиент: Счёт 8800112244.")


def test_real_name_after_label_still_masked():
    m = UltimateSession().mask("Сотрудник: Бексултан Нурланов")
    assert "Бексултан" not in m


def test_dialog_is_not_blocked_by_guard():
    r = process_message("Клиент: Здравствуйте, у меня вопрос.", Quiet())
    assert r["status"] == "ok"
