"""Extractor for native PDF documents."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

import pdfplumber

from .base_extractor import BaseExtractor, ExtractionPayload
from ..utils.logger import logger


class PDFExtractor(BaseExtractor):
    """Extract text, metadata and tables from PDF files."""

    section_pattern = re.compile(
        r"(?:SECAO|SE\\u00c7\\u00c3O|SEÇÃO|Seção)\s+(\d+)[\s\-:]+(.+)",
        re.IGNORECASE,
    )

    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == ".pdf"

    def extract(self, file_path: Path) -> ExtractionPayload:
        logger.info("Extracting PDF: %s", file_path.name)
        text = self._extract_text(file_path)
        tables = self._extract_tables(file_path)
        metadata = self._extract_metadata(file_path)
        sections = self._split_sections(text)
        return self._build_payload(
            text=text,
            metadata=metadata,
            sections=sections,
            tables=tables,
        )

    def _extract_text(self, file_path: Path) -> str:
        parts = []
        with pdfplumber.open(file_path) as pdf:
            for page_index, page in enumerate(pdf.pages, start=1):
                parts.append(f"\n--- Pagina {page_index} ---\n")
                text = page.extract_text() or ""
                parts.append(text)
        return "".join(parts)

    def _extract_tables(self, file_path: Path) -> List[Dict[str, object]]:
        tables: List[Dict[str, object]] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_index, page in enumerate(pdf.pages, start=1):
                    for table in page.extract_tables():
                        tables.append({"page": page_index, "data": table})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to extract tables from %s: %s", file_path.name, exc)
        return tables

    def _extract_metadata(self, file_path: Path) -> Dict[str, object]:
        try:
            with pdfplumber.open(file_path) as pdf:
                pages = len(pdf.pages)
            return {"pages": pages}
        except Exception:
            return {"pages": None}

    def _split_sections(self, text: str) -> Dict[int, str]:
        sections: Dict[int, str] = {}
        matches = list(self.section_pattern.finditer(text))
        for index, match in enumerate(matches):
            section_number = int(match.group(1))
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            sections[section_number] = text[start:end].strip()
        return sections

