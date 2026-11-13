"""Диагностика: показывает код ошибки OpenAI (тестовая фраза без данных)."""
import os

import openai
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                       max_retries=0, timeout=30)
try:
    r = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL"),
        messages=[{"role": "user", "content": "Скажи привет одним словом."}],
    )
    print("Ответ:", r.choices[0].message.content)
except openai.APIStatusError as e:
    print("HTTP:", e.status_code)
    print("code:", getattr(e, "code", None))
    print("message:", getattr(e, "message", None))
