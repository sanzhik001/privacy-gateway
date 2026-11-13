import base64
import json

import pytest

from src.audit import AuditLog, generate_key
from src.llm_client import LLMProvider, get_provider
from src.more_rules import UltimateSession
from src.pipeline import process_message


class Recorder(LLMProvider):
    name = "recorder"

    def __init__(self):
        self.received = []

    def generate(self, masked_text):
        self.received.append(masked_text)
        return "Ок"


class Fixed(LLMProvider):
    name = "fixed"

    def __init__(self, answer):
        self.answer = answer

    def generate(self, masked_text):
        return self.answer


class Failing(LLMProvider):
    name = "failing"

    def generate(self, masked_text):
        raise RuntimeError("Ошибка провайдера: RateLimitError")


SECRET_TEXT = (
    "Меня зовут Бексултан, телефон +7 701 234 56 78, пароль: Secret123, "
    "живу на ул. Абая 150, кв. 12, дата рождения: 12.05.1990, "
    "ник @aigerim_test, машина 123ABC02, заявка EMP-4821"
)
SECRETS = ["Бексултан", "701 234 56 78", "Secret123", "Абая",
           "12.05.1990", "aigerim_test", "123ABC02", "EMP-4821"]


@pytest.mark.parametrize("text", ["", " ", "\n\n"])
def test_empty_input_does_not_crash(text):
    assert process_message(text, Recorder())["status"] == "ok"


def test_provider_error_is_reported_not_raised():
    r = process_message("Привет", Failing())
    assert r["status"] == "provider_error"
    assert r["answer"] is None
    assert r["masked"] is not None


def test_provider_error_is_written_to_audit(tmp_path):
    log = AuditLog(str(tmp_path / "a.enc"), generate_key())
    process_message("Привет", Failing(), audit=log)
    assert log.read_all()[0]["status"] == "provider_error"


def test_provider_never_sees_originals():
    rec = Recorder()
    process_message(SECRET_TEXT, rec)
    assert rec.received, "запрос заблокирован, модель его не получила"
    for s in SECRETS:
        assert s not in rec.received[0], s


def test_audit_never_contains_user_text(tmp_path):
    path = tmp_path / "audit.enc"
    log = AuditLog(str(path), generate_key())
    process_message(SECRET_TEXT, Recorder(), audit=log)
    raw = path.read_bytes().decode("latin-1")
    events = json.dumps(log.read_all(), ensure_ascii=False)
    for s in SECRETS:
        assert s not in raw
        assert s not in events


def test_inbound_leak_is_blocked():
    r = process_message("Привет", Fixed("Звоните +7 702 333 44 55"))
    assert r["status"] == "blocked_inbound"
    assert r["answer"] is None


def test_forged_markers_are_not_restored():
    s = UltimateSession()
    s.mask("Меня зовут Бексултан")
    forged = f"Привет [NAME_9#{s.nonce}] и [NAME_1#abc123]"
    assert s.unmask(forged) == forged


def test_blocked_marker_never_restored():
    s = UltimateSession()
    s.mask("пароль: Secret123")
    marker = list(s.mapping)[0]
    out = s.unmask(f"Ваш {marker}")
    assert "Secret123" not in out
    assert "[удалено системом]" in out


@pytest.mark.parametrize("text", [
    "", "[", "]]]", "[NAME_1#", "[[PHONE_1#abcdef]]", "\x00", "[A_1#zzzzzz]",
])
def test_unmask_survives_garbage(text):
    assert isinstance(UltimateSession().unmask(text), str)


def test_many_entities_roundtrip():
    text = "; ".join(f"+7 701 {i:03d} 45 67" for i in range(300))
    s = UltimateSession()
    masked = s.mask(text)
    assert "+7 701" not in masked
    assert len(s.mapping) == 300
    assert s.unmask(masked) == text


@pytest.mark.parametrize("text", [
    "Забыл пароль и не могу войти.", "Встреча 2026-10-12",
    "Каспийское море", "Вера в будущее, Мир и Роза.",
    "Используем AES-256-GCM, SHA-256 и UTF-8", "Версия 1.2.3 готова",
    "Сумма 110000", "Объясни разницу между кредитом и лизингом",
    "Нужен пароль для входа", "Сбросить пароль от почты",
    "Цена 5 USD за штуку", "Заказ номер 7 готов",
])
def test_benign_phrases_are_not_blocked(text):
    # Ловит расхождения маскировщика и цензора (как было с «пароль и»).
    assert process_message(text, Recorder())["status"] == "ok"


def test_audit_without_key_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("AUDIT_KEY", raising=False)
    with pytest.raises(RuntimeError):
        AuditLog(str(tmp_path / "a.enc"))


def test_audit_rejects_short_key(tmp_path):
    short = base64.urlsafe_b64encode(b"x" * 16).decode()
    with pytest.raises(ValueError):
        AuditLog(str(tmp_path / "a.enc"), short)


@pytest.mark.parametrize("line", [b"not-base64!!", b"AAAA", b"\xff\xfe"])
def test_corrupted_audit_file_raises(tmp_path, line):
    path = tmp_path / "a.enc"
    path.write_bytes(line + b"\n")
    with pytest.raises(Exception):
        AuditLog(str(path), generate_key()).read_all()


def test_openai_without_model_raises(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    with pytest.raises(RuntimeError):
        get_provider("openai")
