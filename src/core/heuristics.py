"""Heuristic extraction helpers for common FDS fields."""

from __future__ import annotations

import re
from typing import Iterable, Mapping

from ..utils.logger import logger

NumberONUResult = dict[str, object]

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

    # Common UN numbers and their classes
    UN_CLASS_MAP = {
        "1005": "2.3",  # Ammonia, anhydrous
        "1011": "2.1",  # Butane
        "1017": "2.3",  # Chlorine
        "1075": "2.1",  # Petroleum gases, liquefied
        "1170": "3",    # Ethanol
        "1203": "3",    # Gasoline
        "1230": "3",    # Methanol
        "1791": "8",    # Hypochlorite solution
        "1824": "8",    # Sodium hydroxide solution
        "1830": "8",    # Sulfuric acid
        "1863": "3",    # Fuel, aviation, turbine engine
        "1978": "2.1",  # Propane
        "1993": "3",    # Flammable liquid, n.o.s.
        "2433": "6.1",  # Chloronitrotoluenes, liquid
        "3077": "9",    # Environmentally hazardous substance, solid
        "3082": "9",    # Environmentally hazardous substance, liquid
        "3264": "8",    # Corrosive liquid, acidic, inorganic, n.o.s.
    }

    def extract(
        self,
        *,
        text: str,
        sections: Mapping[int, str | None] = None,
    ) -> dict[str, dict[str, object]]:
        """Return heuristic suggestions keyed by field name."""
        # Pre-process text to mask phone numbers
        masked_text = self._mask_phone_numbers(text)
        masked_sections = None
        if sections:
            masked_sections = {k: self._mask_phone_numbers(v) for k, v in sections.items()}

        suggestions: dict[str, dict[str, object]] = {}

        numero_onu = self._extract_numero_onu(masked_text, masked_sections)
        if numero_onu:
            suggestions["numero_onu"] = numero_onu

        numero_cas = self._extract_numero_cas(masked_text, masked_sections)
        if numero_cas:
            suggestions["numero_cas"] = numero_cas

        # Pass found ONU value to class extractor
        onu_val = str(numero_onu["value"]) if numero_onu else None
        classificacao = self._extract_classificacao(masked_text, masked_sections, onu_number=onu_val)
        if classificacao:
            suggestions["classificacao_onu"] = classificacao

        nome_produto = self._extract_nome_produto(masked_text, masked_sections)
        if nome_produto:
            suggestions["nome_produto"] = nome_produto

        fabricante = self._extract_fabricante(masked_text, masked_sections)
        if fabricante:
            suggestions["fabricante"] = fabricante

        grupo_embalagem = self._extract_grupo_embalagem(masked_text, masked_sections)
        if grupo_embalagem:
            suggestions["grupo_embalagem"] = grupo_embalagem

        incompatibilidades = self._extract_incompatibilidades(
            masked_text,
            masked_sections,
        )
        if incompatibilidades:
            suggestions["incompatibilidades"] = incompatibilidades

        return suggestions

    def _mask_phone_numbers(self, text: str) -> str:
        """Replace phone numbers with [PHONE] placeholder to avoid false positives."""
        # Patterns to mask
        patterns = [
            # 0800 sequences (e.g. 0800 707 7022, 0800 17 2020)
            r'\b0800\s+\d{2,4}\s+\d{3,4}\b',
            r'\b0800\s+\d{3,4}\b',
            # International (e.g. +55 21 3958-1449)
            r'(?:\+\d{1,3}[\s-]?)?(?:\(?\d{2,3}\)?[\s-]?)?\d{3,5}[\s-]?\d{3,5}',
            # Standard BR (e.g. (11) 4349-1359)
            r'\(\d{2,3}\)\s*\d{4,5}[-\s]\d{4}',
        ]
        
        masked = text
        for pat in patterns:
            masked = re.sub(pat, "[PHONE]", masked)
        return masked

    def _extract_numero_onu(
        self,
        text: str,
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
        """Find likely ONU numbers using regex matching."""
        search_space: Iterable[str]

        if sections:
            search_space = sections.values()
        else:
            search_space = [text]

        best_match: NumberONUResult | None = None

        for block in search_space:
            # Find all matches in the block
            matches = list(self.ONU_PATTERN.finditer(block))
            
            for match in matches:
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

                # Check context for "UN" or "ONU" prefix
                has_prefix = bool(match.group(1))
                
                # Heuristic: If it looks like a year (19xx or 20xx) and has NO prefix, skip it
                if not has_prefix and (1900 <= number_int <= 2100):
                    # Check if it's part of a date pattern nearby (slash, dash, or DOT)
                    snippet_wide = block[max(0, match.start() - 20) : match.end() + 20]
                    if re.search(r'\d{1,2}[/.-]\d{1,2}[/.-]' + number, snippet_wide) or \
                       re.search(number + r'[/.-]\d{1,2}[/.-]\d{1,2}', snippet_wide):
                        continue
                    # Also skip if preceded by "Date" or "Data"
                    if re.search(r'(?:data|date)\s*(?:de)?\s*(?:preparaç|revis|emiss|validade|impress).*?' + number, snippet_wide, re.IGNORECASE):
                        continue
                    # Skip if preceded by month name (e.g. "novembro de 2022")
                    months = r"(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)"
                    if re.search(months + r"\s*(?:de)?\s*" + number, snippet_wide, re.IGNORECASE):
                        continue
                    # Skip if it looks like a version year "NBR 14725:2023"
                    if re.search(r':\s*' + number, snippet_wide):
                        continue

                # Heuristic: Filter out decimal parts (e.g. 1,0779)
                # Check immediate predecessor char
                if match.start() > 0 and block[match.start()-1] in ",.":
                    continue

                # Heuristic: Filter out parts of CAS numbers (e.g. 1303 in 1303-96-4)
                if not has_prefix:
                    # Check if followed immediately by dash and digits, or preceded by digits and dash
                    snippet_wide = block[max(0, match.start() - 20) : match.end() + 20]
                    if re.search(number + r'-\d{2}-\d', snippet_wide) or \
                       re.search(r'\d{2,7}-' + number + r'-\d', snippet_wide):
                        continue

                snippet = block[max(0, match.start() - 60) : match.end() + 60]
                
                candidate = {
                    "value": number,
                    "confidence": 0.95 if has_prefix else 0.85,
                    "context": snippet.strip(),
                }

                # If we found a prefixed match, it's very likely the correct one. Return immediately.
                if has_prefix:
                    return candidate
                
                # Otherwise, keep the first valid bare number as a fallback, 
                # but keep looking for a prefixed one.
                if best_match is None:
                    best_match = candidate

        return best_match

    CAS_PATTERN = re.compile(r"\b\d{2,7}-\d{2}-\d\b")

    def _extract_numero_cas(
        self,
        text: str,
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
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
        sections: Mapping[int, str | None] = None,
        onu_number: str | None = None,
    ) -> NumberONUResult | None:
        """Heuristic for UN hazard class."""
        # First, try to infer from UN number if available
        if onu_number and onu_number in self.UN_CLASS_MAP:
            inferred_class = self.UN_CLASS_MAP[onu_number]
            logger.debug("Inferred class %s from UN %s", inferred_class, onu_number)
            return {
                "value": inferred_class,
                "confidence": 0.7,  # Medium confidence for inference
                "context": f"Inferred from UN {onu_number}",
            }

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
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
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
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
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
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
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

    # New pattern for incompatibilities. Often appears in Section 10 (Estabilidade e reatividade)
    # Example labels: "Incompatibilidades", "Incompatível com", "Materiais incompatíveis"
    INCOMPATIBILIDADES_PATTERN = re.compile(
        r"(?P<label>(?:materiais?\s+incompat[ií]veis?|incompat[ií]vel\s+com|incompatibilidades?))\s*[:\-]?\s*(?P<value>.{3,200})",
        re.IGNORECASE,
    )

    def _extract_incompatibilidades(
        self,
        text: str,
        sections: Mapping[int, str | None] = None,
    ) -> NumberONUResult | None:
        """Extract chemical incompatibilities list.

        Strategy:
        1. Prefer dedicated section (10) if provided by upstream splitter.
        2. Fallback to whole text scan limited to first 8000 characters to avoid noise.
        3. Trim trailing sentence breaks and line wraps.
        """
        search_space: Iterable[str]
        if sections and 10 in sections:
            # Section 10: Estabilidade e reatividade typically hosts incompatibilities
            search_space = [sections[10]]
        else:
            search_space = [text[:8000]]

        for block in search_space:
            match = self.INCOMPATIBILIDADES_PATTERN.search(block)
            if not match:
                continue
            raw_value = match.group("value").strip()
            # Stop at first line break or end of sentence to keep concise
            raw_value = raw_value.split("\n")[0].strip()
            # Truncate overly long listings while keeping whole last token
            if len(raw_value) > 200:
                raw_value = raw_value[:200].rsplit(" ", 1)[0] + "…"
            snippet = block[max(0, match.start() - 60) : match.end() + 60]
            logger.debug("Heuristic incompatibilidades detected: %s", raw_value)
            return {
                "value": raw_value,
                "confidence": 0.75 if re.search(r"incompat", match.group("label"), re.IGNORECASE) else 0.65,
                "context": snippet.strip(),
            }
        return None
