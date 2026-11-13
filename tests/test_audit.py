import base64

import pytest
from cryptography.exceptions import InvalidTag

from src.audit import AuditLog, generate_key


def make(tmp_path, key=None):
    return AuditLog(str(tmp_path / "audit.log"), key or generate_key())


def test_roundtrip(tmp_path):
    log = make(tmp_path)
    log.write("ok", "mock", {"NAME": 1, "PHONE": 2}, [])
    events = log.read_all()
    assert events[0]["status"] == "ok"
    assert events[0]["found"] == {"NAME": 1, "PHONE": 2}


def test_file_has_no_plaintext(tmp_path):
    log = make(tmp_path)
    log.write("ok", "mock", {"NAME": 1}, [])
    raw = (tmp_path / "audit.log").read_bytes()
    assert b"NAME" not in raw
    assert b"status" not in raw
    assert b"mock" not in raw


def test_same_event_gives_different_ciphertext(tmp_path):
    log = make(tmp_path)
    log.write("ok", "mock", {"NAME": 1}, [])
    log.write("ok", "mock", {"NAME": 1}, [])
    lines = (tmp_path / "audit.log").read_bytes().splitlines()
    assert lines[0] != lines[1]


def test_tampering_is_detected(tmp_path):
    log = make(tmp_path)
    log.write("ok", "mock", {"NAME": 1}, [])
    path = tmp_path / "audit.log"
    blob = bytearray(base64.b64decode(path.read_bytes().strip()))
    blob[-1] ^= 1  # меняем один бит
    path.write_bytes(base64.b64encode(bytes(blob)) + b"\n")
    with pytest.raises(InvalidTag):
        log.read_all()


def test_wrong_key_cannot_read(tmp_path):
    make(tmp_path, generate_key()).write("ok", "mock", {}, [])
    with pytest.raises(InvalidTag):
        make(tmp_path, generate_key()).read_all()


def test_cannot_log_free_text(tmp_path):
    log = make(tmp_path)
    with pytest.raises(ValueError):
        log.write("ok", "mock", {"Айгерим": 1}, [])
    with pytest.raises(ValueError):
        log.write("ok", "mock", {}, ["+7 701 234 56 78"])
    with pytest.raises(ValueError):
        log.write("пароль Secret123", "mock", {}, [])