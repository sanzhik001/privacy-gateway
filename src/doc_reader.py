# src/doc_reader.py
"""Чтение документов: txt, md, csv, log, json, docx, pdf."""

import io

TEXT_EXT = {".txt", ".md", ".csv", ".log", ".json"}


def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", errors="replace")


def read_document(name: str, data: bytes) -> str:
    ext = "." + name.lower().rsplit(".", 1)[-1] if "." in name else ""
    if ext in TEXT_EXT:
        return _decode(data)
    if ext == ".docx":
        import docx

        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for table in d.tables:
            for row in table.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    raise ValueError(f"Формат не поддерживается: {ext or 'без расширения'}")
