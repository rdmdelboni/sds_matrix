"""Simple text chunking helpers for the MVP pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..utils.config import CHUNK_SIZE

@dataclass(frozen=True)
class Chunk:
    """Represents a chunk of text that will be sent to the LLM."""

    label: str
    text: str

class ChunkStrategy:
    """Provide chunk sequences from extracted documents."""

    def __init__(self, max_characters: int | None = None) -> None:
        self.max_characters = max_characters or CHUNK_SIZE

    def make_chunks(self, text: str, sections: dict[int, str] | None = None) -> list[Chunk]:
        """Split text into manageable pieces prioritising FDS sections."""
        if sections:
            return [
                Chunk(label=f"Secao {section}", text=section_text)
                for section, section_text in sorted(sections.items())
                if section_text.strip()
            ]

        return list(self._split_by_length(text))

    def _split_by_length(self, text: str) -> Iterable[Chunk]:
        """Fallback chunking strategy based on character count."""
        max_chars = max(self.max_characters, 1000)
        segments: list[Chunk] = []
        for index in range(0, len(text), max_chars):
            segment = text[index : index + max_chars]
            segments.append(Chunk(label=f"Chunk {index // max_chars + 1}", text=segment))
        return segments
