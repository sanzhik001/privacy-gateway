from src.extra_rules import FinalSession

TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"


def test_token_masked_and_never_restored():
    s = FinalSession()
    masked = s.mask(f"API_TOKEN = \"{TOKEN}\"")
    assert TOKEN not in masked
    assert TOKEN not in s.unmask(masked)


def test_password_in_connection_url():
    masked = FinalSession().mask("postgresql://admin:Qwerty2026@host.local/crm")
    assert "Qwerty2026" not in masked


def test_key_value_secret():
    masked = FinalSession().mask("SECRET_KEY = abc12345xyz")
    assert "abc12345xyz" not in masked


def test_ip_address_masked():
    masked = FinalSession().mask("сервер 10.0.0.5 недоступен")
    assert "10.0.0.5" not in masked
    assert "[IP_1#" in masked


def test_ip_not_taken_for_money():
    masked = FinalSession().mask("узел 192.168.100.200")
    assert "192.168.100.200" not in masked
    assert "[IP_" in masked


def test_version_number_untouched():
    text = "версия 1.2.3 готова"
    assert FinalSession().mask(text) == text


def test_identity_document():
    masked = FinalSession().mask("Удостоверение личности N12345678 выдано")
    assert "12345678" not in masked


def test_medical_keyword():
    masked = FinalSession().mask("диагноз ВИЧ, наблюдается")
    assert "ВИЧ" not in masked


def test_clean_text_untouched():
    text = "Объясни разницу между кредитом и лизингом простыми словами"
    assert FinalSession().mask(text) == text