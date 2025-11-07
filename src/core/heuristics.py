"""Heuristic extraction helpers for common FDS fields."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Mapping, Optional

from ..utils.logger import logger

NumberONUResult = Dict[str, object]


class HeuristicExtractor:
    """Rule-based fallback extractors operating on plain text."""

    ONU_PATTERN = re.compile(
        r"""
        (?:
            \b(?:UN|ONU)[\s#:;]{0,3}(\d{4})  # Patterns like UN1234 or ONU: 1234
            |
            \b(\d{4})\b                       # Bare 4 digits with word boundaries
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def extract(
        self,
        *,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Dict[str, Dict[str, object]]:
        """Return heuristic suggestions keyed by field name."""
        suggestions: Dict[str, Dict[str, object]] = {}

        numero_onu = self._extract_numero_onu(text, sections)
        if numero_onu:
            suggestions["numero_onu"] = numero_onu

        numero_cas = self._extract_numero_cas(text, sections)
        if numero_cas:
            suggestions["numero_cas"] = numero_cas

        classificacao = self._extract_classificacao(text, sections)
        if classificacao:
            suggestions["classificacao_onu"] = classificacao

        nome_produto = self._extract_nome_produto(text, sections)
        if nome_produto:
            suggestions["nome_produto"] = nome_produto

        fabricante = self._extract_fabricante(text, sections)
        if fabricante:
            suggestions["fabricante"] = fabricante

        grupo_embalagem = self._extract_grupo_embalagem(text, sections)
        if grupo_embalagem:
            suggestions["grupo_embalagem"] = grupo_embalagem

        return suggestions

    def _extract_numero_onu(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Find likely ONU numbers using regex matching."""
        search_space: Iterable[str]

        if sections:
            search_space = sections.values()
        else:
            search_space = [text]

        for block in search_space:
            match = self.ONU_PATTERN.search(block)
            if not match:
                continue

            number = match.group(1) or match.group(2)
            if not number:
                continue

            # Filter out obvious false positives outside valid ONU range.
            try:
                number_int = int(number)
            except ValueError:
                continue

            if not (4 <= number_int <= 3506):
                continue

            snippet = block[max(0, match.start() - 60) : match.end() + 60]
            logger.debug("Heuristic numero ONU detected: %s", number)
            return {
                "value": number,
                "confidence": 0.85,
                "context": snippet.strip(),
            }

        return None

    CAS_PATTERN = re.compile(r"\b\d{2,7}-\d{2}-\d\b")

    def _extract_numero_cas(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Locate CAS numbers in the text."""
        search_space: Iterable[str] = sections.values() if sections else [text]
        for block in search_space:
            match = self.CAS_PATTERN.search(block)
            if not match:
                continue
            snippet = block[max(0, match.start() - 60) : match.end() + 60]
            value = match.group(0)
            logger.debug("Heuristic numero CAS detected: %s", value)
            return {
                "value": value,
                "confidence": 0.8,
                "context": snippet.strip(),
            }
        return None

    CLASS_PATTERN = re.compile(
        r"\bclasse\s*(?:de\s*risco)?\s*(\d(?:\.\d)?)",
        re.IGNORECASE,
    )

    def _extract_classificacao(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Heuristic for UN hazard class."""
        search_space: Iterable[str] = sections.values() if sections else [text]
        for block in search_space:
            match = self.CLASS_PATTERN.search(block)
            if not match:
                continue
            value = match.group(1)
            snippet = block[max(0, match.start() - 60) : match.end() + 60]
            logger.debug("Heuristic classificacao ONU detected: %s", value)
            return {
                "value": value,
                "confidence": 0.78,
                "context": snippet.strip(),
            }
        return None

    PRODUCT_NAME_PATTERN = re.compile(
        r"(?P<label>(?:nome\s*(?:comercial|do\s+produto|do\s+produto\s+qu[íi]mico)|identifica(?:ç|c)[aã]o\s+do\s+produto|identificador\s+do\s+produto|produto))\s*[:\-]\s*(?P<value>.{3,120})",
        re.IGNORECASE,
    )

    def _extract_nome_produto(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Extract product name from Section 1."""
        search_space: Iterable[str]
        if sections and 1 in sections:
            search_space = [sections[1]]
        else:
            search_space = [text[:2000]]  # Check first 2000 chars
        
        for block in search_space:
            match = self.PRODUCT_NAME_PATTERN.search(block)
            if not match:
                continue
            value = match.group('value').strip()
            # Clean up common suffixes
            value = re.sub(r'\s*\(.*?\)\s*$', '', value)
            value = value.split('\n')[0].strip()
            snippet = block[max(0, match.start() - 40) : match.end() + 40]
            logger.debug("Heuristic nome produto detected: %s", value)
            return {
                "value": value,
                "confidence": 0.88 if re.search(r"nome\s+do\s+produto|nome\s*comercial", match.group('label'), re.IGNORECASE) else 0.75,
                "context": snippet.strip(),
            }
        return None

    MANUFACTURER_PATTERN = re.compile(
        r"(?P<label>(?:fabricante|fabricado\s+por|fornecedor(?:\/distribuidor)?|empresa|raz[aã]o\s+social))\s*[:\-]\s*(?P<value>.{3,120})",
        re.IGNORECASE,
    )

    def _extract_fabricante(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Extract manufacturer/supplier name."""
        search_space: Iterable[str]
        if sections and 1 in sections:
            search_space = [sections[1]]
        else:
            search_space = [text[:2000]]
        
        for block in search_space:
            match = self.MANUFACTURER_PATTERN.search(block)
            if not match:
                continue
            value = match.group('value').strip()
            value = value.split('\n')[0].strip()
            snippet = block[max(0, match.start() - 40) : match.end() + 40]
            logger.debug("Heuristic fabricante detected: %s", value)
            return {
                "value": value,
                "confidence": 0.8 if re.search(r"fabricante|fabricado\s+por|fornecedor", match.group('label'), re.IGNORECASE) else 0.72,
                "context": snippet.strip(),
            }
        return None

    PACKING_GROUP_PATTERN = re.compile(
        r"grupo\s*(?:de)?\s*embalagem\s*[:\-]?\s*(I{1,3}|III|II|I|1|2|3)\b",
        re.IGNORECASE,
    )

    def _extract_grupo_embalagem(
        self,
        text: str,
        sections: Optional[Mapping[int, str]] = None,
    ) -> Optional[NumberONUResult]:
        """Extract packing group (I, II, III)."""
        search_space: Iterable[str]
        if sections and 14 in sections:
            search_space = [sections[14]]
        else:
            search_space = [text]
        
        for block in search_space:
            match = self.PACKING_GROUP_PATTERN.search(block)
            if not match:
                continue
            value = match.group(1).upper()
            # Normalize to Roman numerals
            if value == "1":
                value = "I"
            elif value == "2":
                value = "II"
            elif value == "3":
                value = "III"
            snippet = block[max(0, match.start() - 50) : match.end() + 50]
            logger.debug("Heuristic grupo embalagem detected: %s", value)
            return {
                "value": value,
                "confidence": 0.80,
                "context": snippet.strip(),
            }
        return None
