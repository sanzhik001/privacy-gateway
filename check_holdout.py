"""Покрытие и ложные срабатывания.
data/holdout_scored.txt и data/holdout_extra.txt: текст ||| секрет1 ;; секрет2
data/holdout_clean.txt: по одной фразе, которая меняться не должна.
Запуск: python check_holdout.py                         (только правила)
        python check_holdout.py qwen2.5:3b qwen3.5:4b   (и с моделями)"""

import sys
import time

from src.llm_client import LLMProvider
from src.pipeline import process_message


class Quiet(LLMProvider):
    name = "quiet"

    def generate(self, masked_text):
        return "ok"


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [ln.strip() for ln in f
                    if ln.strip() and not ln.startswith("#")]
    except FileNotFoundError:
        return []


SCORED = read("data/holdout_scored.txt") + read("data/holdout_extra.txt")
CLEAN = read("data/holdout_clean.txt")


def call(text, detector):
    r = process_message(text, Quiet(), detector=detector)
    if r["kinds"] == ["DETECTOR_DOWN"]:
        raise SystemExit("Ollama недоступна: запусти приложение и проверь модель.")
    return r


def run(label, detector):
    start = time.time()
    total = hidden = 0
    for i, row in enumerate(SCORED, 1):
        text, _, tail = row.partition("|||")
        secrets = [s.strip() for s in tail.split(";;") if s.strip()]
        r = call(text.strip(), detector)
        total += len(secrets)
        if r["masked"] is None:  # запрос заблокирован, наружу не ушёл
            hidden += len(secrets)
            continue
        open_ = [s for s in secrets if s in r["masked"]]
        hidden += len(secrets) - len(open_)
        if open_:
            print(f"  [{label}] строка {i}: ОТКРЫТО {open_}")
    print(f"[{label}] скрыто {hidden} из {total}, {time.time() - start:.1f} с")
    return hidden


def run_clean(label, detector):
    changed = 0
    for text in CLEAN:
        r = call(text, detector)
        if r["masked"] != text:
            changed += 1
            print(f"  [{label}] ИЗМЕНЕНО: {text!r} -> {r['masked']!r}")
    print(f"[{label}] ложных срабатываний: {changed} из {len(CLEAN)}")


base = run("правила", None)
run_clean("правила", None)
for model in sys.argv[1:]:
    det = {"model": model, "required": True}
    both = run(f"правила + {model}", det)
    run_clean(f"правила + {model}", det)
    print(f"Прирост от {model}: {both - base:+d}\n")
