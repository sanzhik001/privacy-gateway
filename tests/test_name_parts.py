from src.hybrid import HybridSession
from src.llm_client import LLMProvider
from src.pipeline import process_message


class Quiet(LLMProvider):
    name = "quiet"

    def generate(self, masked_text):
        return "ok"


TEXT = "Клиент: Я Жансерик Оспанов.\nОператор: Здравствуйте, Жансерик."


def test_first_name_repeated_alone_is_masked():
    m = HybridSession().mask(TEXT)
    assert "Жансерик" not in m
    assert "Оспанов" not in m
    assert "Здравствуйте" in m


def test_restore_is_exact():
    s = HybridSession()
    assert s.unmask(s.mask(TEXT)) == TEXT


def test_pipeline_not_blocked():
    assert process_message(TEXT, Quiet())["status"] == "ok"


def test_common_words_untouched():
    text = "Клиент: Здравствуйте, подскажите режим работы офиса в Алматы."
    assert HybridSession().mask(text) == text
