"""Load and section-split fictional educational audit documents."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    document_id: str
    title: str
    version: str
    section: str
    text: str
    source: str

    @property
    def reference(self) -> str:
        return f"{self.document_id}:v{self.version}#{self.section}"


def _metadata(lines: list[str], key: str, fallback: str) -> str:
    prefix = f"{key}:"
    for line in lines[:8]:
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return fallback


def split_document(path: str | Path) -> list[DocumentChunk]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    document_id = _metadata(lines, "ID", source.stem.upper())
    title = _metadata(lines, "Título", source.stem.replace("_", " ").title())
    version = _metadata(lines, "Versión", "1.0")
    chunks: list[DocumentChunk] = []
    section = "general"
    buffer: list[str] = []

    def flush() -> None:
        content = "\n".join(buffer).strip()
        if content:
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    title=title,
                    version=version,
                    section=re.sub(r"[^a-zA-Z0-9_-]+", "-", section.lower()).strip("-"),
                    text=content,
                    source=source.name,
                )
            )

    for line in lines:
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
            buffer = [line]
        elif line.strip() not in {"---"} and not line.startswith(("ID:", "Título:", "Versión:")):
            buffer.append(line)
    flush()
    return chunks


def load_document_chunks(directory: str | Path) -> list[DocumentChunk]:
    root = Path(directory)
    if not root.is_dir():
        return []
    return [
        chunk
        for path in sorted(root.glob("*.md"))
        for chunk in split_document(path)
    ]
