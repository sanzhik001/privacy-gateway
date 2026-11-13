from src.hybrid import HybridSession


def mask(text):
    return HybridSession(None).mask(text)


def test_password_with_exclamation():
    out = mask("логин: demo_buh, пароль: Qw7!pass-2026. Корпоративная карта")
    assert "Qw7" not in out
    assert "pass-2026" not in out
    assert "Корпоративная карта" in out


def test_password_before_comma():
    out = mask("Мой пароль: Secret123, составь жалобу")
    assert "Secret123" not in out
    assert ", составь жалобу" in out


def test_password_with_dots_inside():
    out = mask("пароль: a.b.c-77 сохранить")
    assert "a.b.c-77" not in out
    assert "b.c-77" not in out
