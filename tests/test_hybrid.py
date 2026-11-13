from src.audit import AuditLog, generate_key
from src.llm_client import LLMProvider
from src.pipeline import process_message


class Echo(LLMProvider):
    name = "echo"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return masked_text


DET = {"model": "test-model", "required": True}


def fake_detector(monkeypatch, names=(), orgs=()):
    monkeypatch.setattr("src.ollama_detector.find_entities",
                        lambda text, model: {"NAME": list(names),
                                             "ORG": list(orgs)})


def broken_detector(monkeypatch):
    def boom(text, model):
        raise RuntimeError("Ollama не отвечает")
    monkeypatch.setattr("src.ollama_detector.find_entities", boom)


def test_rules_alone_miss_unknown_name():
    echo = Echo()
    process_message("Отчёт подготовил Зхырбек.", echo)
    assert "Зхырбек" in echo.received[0]


def test_unknown_name_found_by_detector_is_masked(monkeypatch):
    fake_detector(monkeypatch, names=["Зхырбек"])
    echo = Echo()
    r = process_message("Отчёт подготовил Зхырбек.", echo, detector=DET)
    assert r["status"] == "ok"
    assert "Зхырбек" not in echo.received[0]
    assert "Зхырбек" in r["answer"]
    assert r["found"].get("NAME") == 1


def test_org_found_by_detector_is_masked(monkeypatch):
    fake_detector(monkeypatch, orgs=["Альфа-Бета Групп"])
    echo = Echo()
    process_message("Работаем с Альфа-Бета Групп.", echo, detector=DET)
    assert "Альфа" not in echo.received[0]


def test_required_detector_failure_blocks_request(monkeypatch):
    broken_detector(monkeypatch)
    echo = Echo()
    r = process_message("Привет", echo, detector=DET)
    assert r["status"] == "blocked_outbound"
    assert r["kinds"] == ["DETECTOR_DOWN"]
    assert echo.received == []


def test_missing_model_blocks_when_required():
    echo = Echo()
    r = process_message("Привет", echo,
                        detector={"model": None, "required": True})
    assert r["kinds"] == ["DETECTOR_DOWN"]
    assert echo.received == []


def test_optional_detector_failure_falls_back_to_rules(monkeypatch):
    broken_detector(monkeypatch)
    echo = Echo()
    r = process_message("Меня зовут Бексултан", echo,
                        detector={"model": "m", "required": False})
    assert r["status"] == "ok"
    assert "Бексултан" not in echo.received[0]


def test_common_word_from_detector_is_ignored(monkeypatch):
    fake_detector(monkeypatch, names=["Вера"])
    echo = Echo()
    process_message("Вера в будущее", echo, detector=DET)
    assert echo.received[0] == "Вера в будущее"


def test_name_inside_other_word_is_not_registered(monkeypatch):
    fake_detector(monkeypatch, names=["Зхырбек"])
    r = process_message("Зхырбекова пришла", Echo(), detector=DET)
    assert r["status"] == "ok"


def test_unused_detector_name_is_not_counted(monkeypatch):
    fake_detector(monkeypatch, names=["Абая"])
    r = process_message("Живу на ул. Абая 150", Echo(), detector=DET)
    assert r["found"].get("NAME") is None


def test_audit_accepts_detector_failure(monkeypatch, tmp_path):
    broken_detector(monkeypatch)
    log = AuditLog(str(tmp_path / "a.enc"), generate_key())
    process_message("Привет", Echo(), audit=log, detector=DET)
    assert log.read_all()[0]["kinds"] == ["DETECTOR_DOWN"]
