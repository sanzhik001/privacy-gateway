import json as _json

import pytest

from src import ollama_detector as od


class Resp:
    def __init__(self, content):
        self._c = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._c}}


TEXT = "Клиент Айгерим\nКлиент Бексултан\nКлиент Динара\nКлиент Мирас"


def test_truncated_reply_is_retried_on_halves(monkeypatch):
    def _post(url, json=None, timeout=None):
        chunk = json["messages"][1]["content"]
        if chunk.count("\n") >= 3:  # «обрезанный» ответ на 4 строки
            return Resp('{"names": ["Айг')
        names = [ln.split()[1] for ln in chunk.split("\n")]
        return Resp(_json.dumps({"names": names, "orgs": [], "locations": []}))

    monkeypatch.setattr(od.requests, "post", _post)
    out = od.find_entities(TEXT, "m")
    assert out["NAME"] == ["Айгерим", "Бексултан", "Динара", "Мирас"]


def test_network_error_is_not_split(monkeypatch):
    calls = []

    def _post(url, json=None, timeout=None):
        calls.append(1)
        raise od.requests.ConnectionError("down")

    monkeypatch.setattr(od.requests, "post", _post)
    with pytest.raises(RuntimeError):
        od.find_entities(TEXT, "m")
    assert len(calls) == 1


def test_single_line_bad_reply_raises(monkeypatch):
    monkeypatch.setattr(od.requests, "post",
                        lambda url, json=None, timeout=None: Resp("{bad"))
    with pytest.raises(RuntimeError):
        od.find_entities("Клиент Айгерим", "m")
