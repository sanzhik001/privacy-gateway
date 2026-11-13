import re
from pathlib import Path

from src import ollama_detector as od


def _answers():
    found = set()
    for name in ("holdout_scored.txt", "holdout_extra.txt"):
        path = Path("data") / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "|||" in line and not line.startswith("#"):
                for s in line.partition("|||")[2].split(";;"):
                    s = s.strip()
                    if len(s) >= 4 and re.search(r"[A-Za-zА-Яа-яЁё]", s):
                        found.add(s)
    return found


def test_prompt_does_not_contain_test_answers():
    leaked = [s for s in _answers() if s.lower() in od.SYSTEM.lower()]
    assert leaked == [], leaked
