from src.masker import MaskingSession


def test_same_phone_twice_gets_same_marker():
    s = MaskingSession()
    s.mask("Айгерим +7 701 234 56 78, Санжар +7 701 234 56 78")
    phones = [k for k in s.mapping if k.startswith("[PHONE_")]
    assert len(phones) == 1


def test_system_password_is_masked():
    s = MaskingSession()
    masked = s.mask("пароль системы 1284392")
    assert "1284392" not in masked


def test_employee_count_is_masked():
    s = MaskingSession()
    masked = s.mask("колво сотрудников 110000")
    assert "110000" not in masked