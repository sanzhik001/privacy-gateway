from src.masker import MaskingSession


def test_name_after_trigger_is_masked():
    masked = MaskingSession().mask("Меня зовут Айгерим, телефон +7 701 234 56 78")
    assert "Айгерим" not in masked
    assert "Меня зовут [NAME_1#" in masked


def test_full_name_is_one_marker():
    masked = MaskingSession().mask("Меня зовут Айгерим Нурлановна Сейтова.")
    assert "Айгерим" not in masked
    assert "Сейтова" not in masked


def test_same_name_same_marker():
    s = MaskingSession()
    s.mask("Меня зовут Санжар. Моё имя Санжар.")
    assert len(s.mapping) == 1


def test_name_is_restored_for_user():
    s = MaskingSession()
    s.mask("Меня зовут Айгерим")
    marker = list(s.mapping)[0]
    assert "Айгерим" in s.unmask(f"Здравствуйте, {marker}!")


def test_kazakh_letters():
    masked = MaskingSession().mask("Меня зовут Әсел")
    assert "Әсел" not in masked


def test_text_without_names_is_untouched():
    text = "Отчёт по финансам за квартал"
    assert MaskingSession().mask(text) == text