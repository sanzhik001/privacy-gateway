# src/llm_client.py
"""Единый интерфейс для облачных моделей.

Любой провайдер получает ТОЛЬКО уже замаскированный текст.
"""

import os

SYSTEM_PROMPT = (
    "Ты помощник. В тексте есть маркеры вида [ТИП_N#код], например "
    "[NAME_1#a1b2c3]. Это замаскированные данные. Не пытайся их "
    "угадать и сохраняй маркеры в ответе точно как есть."
)


class LLMProvider:
    """Базовый класс: каждый провайдер реализует generate()."""

    name = "base"

    def generate(self, masked_text: str) -> str:
        raise NotImplementedError


class MockProvider(LLMProvider):
    """Заглушка для локальных тестов. Это не настоящая модель."""

    name = "mock"

    def generate(self, masked_text: str) -> str:
        return f"Принято. Ваш запрос: {masked_text}"


class OpenAIProvider(LLMProvider):
    """Реальный вызов OpenAI. Ключ и модель берутся из .env."""

    name = "openai"

    def __init__(self):
        from openai import OpenAI

        key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL")
        if not key:
            raise RuntimeError("OPENAI_API_KEY не задан в .env")
        if not self.model:
            raise RuntimeError("OPENAI_MODEL не задан в .env")
        self._client = OpenAI(api_key=key, timeout=30, max_retries=1)

    def generate(self, masked_text: str) -> str:
        import openai

        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": masked_text},
                ],
            )
        except openai.OpenAIError as e:
            # Текст ошибки не пробрасываем: показываем только её тип.
            raise RuntimeError(f"Ошибка провайдера: {type(e).__name__}") from None
        return resp.choices[0].message.content or ""


def get_provider(name: str = "mock") -> LLMProvider:
    """Возвращает провайдера по имени: mock или openai."""
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"Неизвестный провайдер: {name}")
