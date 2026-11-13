import io

import pytest

from src.doc_reader import read_document
from src.extended import iin_check_digit
from src.scanner import preview, report_rows, scan_text


def make_iin(prefix="90010130"):
    for n in range(1000):
        first11 = prefix + f"{n:03d}"
        d = iin_check_digit(first11)
        if d is not None:
            return first11 + str(d)


def kinds(result):
    return {f["kind"] for f in result["findings"]}


def test_finds_main_types_and_risk():
    res = scan_text("Меня зовут Бексултан Нурланов, телефон +7 701 234 56 78, "
                    "почта test@example.com, пароль: Secret123")
    assert {"NAME", "PHONE", "EMAIL", "PASSWORD"} <= kinds(res)
    risks = {f["kind"]: f["risk"] for f in res["findings"]}
    assert risks["PASSWORD"] == "critical"
    assert risks["NAME"] == "high"


def test_bin_label_from_context():
    res = scan_text(f"ТОО Ромашка, БИН {make_iin()}")
    assert "БИН" in {f["label"] for f in res["findings"]}


def test_iin_label_from_context():
    res = scan_text(f"Сотрудник, ИИН {make_iin()}")
    assert "ИИН" in {f["label"] for f in res["findings"]}


def test_unlabeled_12_digits_is_ambiguous():
    res = scan_text(f"номер {make_iin()} проверьте")
    assert "ИИН/БИН" in {f["label"] for f in res["findings"]}


def test_report_does_not_expose_full_values():
    res = scan_text("пароль: Secret123, телефон +7 701 234 56 78")
    shown = str(report_rows(res))
    assert "Secret123" not in shown
    assert "701 234 56 78" not in shown


def test_line_numbers():
    res = scan_text("первая\nТелефон +7 701 234 56 78\nтретья")
    phone = [f for f in res["findings"] if f["kind"] == "PHONE"][0]
    assert phone["lines"] == [2]


def test_blocked_phrase_is_reported():
    res = scan_text("Документ строго конфиденциально")
    assert "строго конфиденциально" in res["blocked_phrases"]


def test_clean_document_has_no_findings():
    res = scan_text("Отчёт по финансам за квартал")
    assert res["findings"] == []
    assert res["masked"] == "Отчёт по финансам за квартал"


def test_extra_names_from_detector_are_masked():
    res = scan_text("Отчёт подготовил Зхырбек.", {"NAME": ["Зхырбек"]})
    assert "Зхырбек" not in res["masked"]
    assert "NAME" in kinds(res)


def test_extra_orgs_from_detector_are_masked():
    res = scan_text("Работаем с Альфа-Бета Групп.", {"ORG": ["Альфа-Бета Групп"]})
    assert "Альфа" not in res["masked"]


def test_preview():
    assert preview("abc") == "***"
    assert "Secret123" not in preview("Secret123")


def test_reader_text_encodings():
    assert read_document("a.txt", "Привет".encode("utf-8")) == "Привет"
    assert read_document("a.txt", "Привет".encode("cp1251")) == "Привет"


def test_reader_rejects_unknown_format():
    with pytest.raises(ValueError):
        read_document("a.exe", b"x")


def test_reader_docx():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Меня зовут Бексултан")
    buf = io.BytesIO()
    d.save(buf)
    assert "Бексултан" in read_document("a.docx", buf.getvalue())
