import json as _json

from src import ollama_detector as od


class Resp:
    def __init__(self, content):
        self._c = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"message": {"content": self._c}}


def test_pieces_are_short_and_complete():
    text = ("Первое предложение про Айгерим. " * 5
            + "Второе про Бексултана! Третье про Динару?")
    pieces = od._small_pieces(text, size=60)
    assert all(len(p) <= 60 or "." not in p[:-1] for p in pieces)
    joined = " ".join(pieces)
    for name in ("Айгерим", "Бексултана", "Динару"):
        assert name in joined


def test_each_piece_is_sent_separately(monkeypatch):
    sent = []

    def _post(url, json=None, timeout=None):
        piece = json["messages"][1]["content"]
        sent.append(piece)
        names = [w.strip(".!?,") for w in piece.split() if w[0].isupper()]
        return Resp(_json.dumps({"names": names, "orgs": [], "locations": []}))

    monkeypatch.setattr(od.requests, "post", _post)
    monkeypatch.setattr(od, "PIECE_CHARS", 40)
    text = "Звонил Темирлан утром. Потом пришла Айгерке из бухгалтерии."
    out = od.find_entities(text, "m")
    assert len(sent) == 2
    assert "Айгерке" in out["NAME"]
