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


def patch_post(monkeypatch, content, calls=None):
    def _post(url, json=None, timeout=None):
        if calls is not None:
            calls.append(url)
        return Resp(content)
    monkeypatch.setattr(od.requests, "post", _post)


def test_refuses_remote_host():
    with pytest.raises(RuntimeError):
        od.find_entities("текст", "m", url="http://example.com:11434")
    with pytest.raises(RuntimeError):
        od.list_models(url="http://192.168.0.5:11434")


def test_cloud_model_is_refused():
    with pytest.raises(RuntimeError):
        od.find_entities("текст", "gemma4:cloud")


def test_cloud_models_are_hidden_from_list(monkeypatch):
    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "qwen2.5:3b"},
                               {"name": "gemma4:cloud"}]}

    monkeypatch.setattr(od.requests, "get", lambda url, timeout=None: R())
    assert od.list_models() == ["qwen2.5:3b"]


def test_hallucinations_are_dropped(monkeypatch):
    answer = _json.dumps({"names": ["Айгерим", "Выдуманный", "айгерим"],
                          "orgs": ["Ромашка", "ig"]})
    patch_post(monkeypatch, answer)
    out = od.find_entities("Айгерим работает в Ромашка", "m")
    assert out == {"NAME": ["Айгерим"], "ORG": ["Ромашка"], "LOCATION": []}


def test_non_json_raises(monkeypatch):
    patch_post(monkeypatch, "это не json")
    with pytest.raises(RuntimeError):
        od.find_entities("текст", "m")


def test_wrong_shape_is_safe(monkeypatch):
    patch_post(monkeypatch, _json.dumps({"names": "строка", "orgs": [1, None]}))
    assert od.find_entities("текст", "m") == {"NAME": [], "ORG": [], "LOCATION": []}


def test_long_text_is_split_into_chunks(monkeypatch):
    calls = []
    patch_post(monkeypatch, _json.dumps({"names": [], "orgs": []}), calls)
    od.find_entities("Айгерим\n" * 1000, "m")
    assert len(calls) >= 3
