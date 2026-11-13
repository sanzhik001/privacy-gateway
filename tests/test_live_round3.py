from src.hybrid import HybridSession
from src.llm_client import LLMProvider
from src.pipeline import process_message


class Quiet(LLMProvider):
    name = "quiet"

    def generate(self, masked_text):
        return "ok"


def test_oblique_patronymic_next_to_name():
    m = HybridSession().mask("Согласовано с Ержановой Динарой Сериковной.")
    for w in ("Ержановой", "Динарой", "Сериковной"):
        assert w not in m


def test_oblique_alone_is_not_a_name():
    text = "Основной вопрос решён, вопрос был главной темой."
    assert HybridSession().mask(text) == text


def test_declined_form_of_detected_name():
    text = "Ты говорил с Бекарысом? Бекарыс сказал, что подпишет."
    s = HybridSession({"NAME": ["Бекарыс"]})
    m = s.mask(text)
    assert "Бекарыс" not in m
    assert s.unmask(m) == text


def test_declined_surname_from_rules():
    m = HybridSession().mask(
        "Вчера звонил Азамат Тлеуов. Передайте Азамату, что Тлеуову нужно подписать акт.")
    for w in ("Азамат", "Тлеуов", "Тлеуову"):
        assert w not in m


def test_city_not_taken_as_declined_name():
    m = HybridSession({"NAME": ["Алмат"]}).mask("Алмат живёт в Алматы.")
    assert "Алматы" in m
    assert "Алмат " not in m


def test_dialog_with_declined_name_not_blocked(monkeypatch):
    monkeypatch.setattr("src.ollama_detector.find_entities",
                        lambda text, model: {"NAME": ["Бекарыс"], "ORG": []})
    r = process_message("Менеджер: Ты говорил с Бекарысом?\n"
                        "Сотрудник: Да, Бекарыс всё подписал.",
                        Quiet(), detector={"model": "m", "required": True})
    assert r["status"] == "ok"
    assert "Да," in r["masked"]


def test_public_orgs_are_not_masked():
    text = "Национальный банк Казахстана и ТОО Ромашка подписали договор."
    m = HybridSession({"ORG": ["Национальный банк Казахстана", "Ромашка"]}).mask(text)
    assert "Национальный банк Казахстана" in m
    assert "Ромашка" not in m
