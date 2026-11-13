# src/audit.py
"""Шифрованный журнал событий (AES-256-GCM).

В журнал можно записать только: статус, провайдера, количество находок
по типам и список типов. Исходный текст сюда передать нельзя: запись
принимает ровно эти поля и проверяет их формат.
"""

import base64
import json
import os
import re
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Привязываем шифртекст к назначению: запись нельзя выдать за данные
# другой системы с тем же ключом.
_AAD = b"privacy-gateway-audit-v1"
_KIND_RE = re.compile(r"^[A-Z_]{1,20}$")
_NAME_RE = re.compile(r"^[a-z_]{1,20}$")


def generate_key():
    """Новый случайный ключ 256 бит в текстовом виде (base64)."""
    return base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode()


def _load_key(key_b64):
    key = base64.urlsafe_b64decode(key_b64)
    if len(key) != 32:
        raise ValueError("Ключ должен быть длиной 256 бит")
    return key


class AuditLog:
    def __init__(self, path, key_b64=None):
        key_b64 = key_b64 or os.getenv("AUDIT_KEY")
        if not key_b64:
            raise RuntimeError("AUDIT_KEY не задан (см. gen_key.py)")
        self._aes = AESGCM(_load_key(key_b64))
        self.path = path

    def write(self, status, provider, found, kinds):
        """Записывает событие. Любые лишние данные отклоняются."""
        if not _NAME_RE.match(status) or not _NAME_RE.match(provider):
            raise ValueError("Недопустимый статус или провайдер")
        if not all(_KIND_RE.match(k) and isinstance(v, int)
                   for k, v in found.items()):
            raise ValueError("found: допустимы только {ТИП: число}")
        if not all(_KIND_RE.match(k) for k in kinds):
            raise ValueError("kinds: допустимы только имена типов")

        event = {"ts": int(time.time()), "status": status,
                 "provider": provider, "found": found, "kinds": list(kinds)}
        data = json.dumps(event, ensure_ascii=False).encode()
        nonce = os.urandom(12)  # новый для каждой записи, повторять нельзя
        blob = nonce + self._aes.encrypt(nonce, data, _AAD)
        with open(self.path, "ab") as f:
            f.write(base64.b64encode(blob) + b"\n")

    def read_all(self):
        """Расшифровывает журнал. Подмена записи вызывает InvalidTag."""
        events = []
        if not os.path.exists(self.path):
            return events
        with open(self.path, "rb") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                blob = base64.b64decode(line)
                data = self._aes.decrypt(blob[:12], blob[12:], _AAD)
                events.append(json.loads(data))
        return events