"""Base classes for document extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

ExtractedTables = list[dict[str, object]]

class ExtractionPayload(dict[str, object]):
    """Typed alias for extracted data maps."""

class BaseExtractor(ABC):
    """Common interface for document extractors."""

    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        """Return True if the extractor supports the file."""

    @abstractmethod
    def extract(self, file_path: Path) -> ExtractionPayload:
        """Return the extracted content for the file."""

    def _build_payload(
        self,
        *,
        text: str,
        metadata: dict[str, object | None] = None,
        sections: dict[int, str | None] = None,
        tables: ExtractedTables | None = None,
    ) -> ExtractionPayload:
        """Helper to standardise extractor output."""
        return ExtractionPayload(
            text=text,
            metadata=metadata or {},
            sections=sections or {},
            tables=tables or [],
        )
