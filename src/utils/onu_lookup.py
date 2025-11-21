"""Lookup utilitario para tabela ONU (classe + grupo de embalagem).

Carrega uma unica vez `tabela_onu_com_pg.csv` (ou `tabela_onu.csv` como
fallback) e expõe um helper simples para buscar pelos dados mapeados
do número ONU.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from .config import BASE_DIR, DATA_DIR
from .logger import logger

def _candidate_paths() -> list[Path]:
    """Return candidate paths for the ONU table file."""
    filenames = ("tabela_onu_com_pg.csv", "tabela_onu.csv")
    paths = []
    for name in filenames:
        paths.extend(
            [
                DATA_DIR / name,           # user data dir
                BASE_DIR / name,           # repo root (dev)
                Path.cwd() / name,         # current working dir fallback
            ]
        )
    # Remove duplicates while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in paths:
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
    return unique

def _normalize_un(value: object) -> int | None:
    """Normalize UN number into int."""
    if value is None:
        return None
    try:
        s = str(value).strip()
        if not s:
            return None
        # Accept 1-4 digits with optional leading zeros
        if not s.isdigit():
            return None
        return int(s)
    except Exception:  # noqa: BLE001
        return None

@lru_cache(maxsize=1)
def load_onu_map() -> dict[int, dict[str, str]]:
    """Load ONU mapping from CSV (cached)."""
    candidates = _candidate_paths()
    found: Path | None = None
    for path in candidates:
        if path.exists():
            found = path
            break
    if not found:
        logger.warning("Tabela ONU nao encontrada em nenhum dos caminhos esperados.")
        return {}

    mapping: dict[int, dict[str, str]] = {}
    try:
        with found.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                num = _normalize_un(row.get("numero_onu"))
                if num is None:
                    continue
                mapping[num] = {
                    "classificacao_onu": (row.get("classificacao_onu") or "").strip(),
                    "grupo_embalagem": (row.get("grupo_embalagem") or "").strip(),
                    "descricao": (row.get("descricao") or "").strip(),
                }
        logger.info("Tabela ONU carregada de %s (%d registros)", found, len(mapping))
    except Exception as exc:  # noqa: BLE001
        logger.error("Falha ao carregar tabela ONU de %s: %s", found, exc)
        return {}
    return mapping

def lookup_un(number: object) -> dict[str, str | None]:
    """Return mapping entry for a given UN number (int/str)."""
    num = _normalize_un(number)
    if num is None:
        return None
    mapping = load_onu_map()
    return mapping.get(num)
