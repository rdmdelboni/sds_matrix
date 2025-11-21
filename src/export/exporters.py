"""Export utilities for processed FDS data."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

from ..utils.config import DUCKDB_FILE
from ..utils.logger import logger

EXPORT_QUERY = """
WITH latest_extractions AS (
    SELECT
        e.document_id,
        e.field_name,
        e.value,
        e.confidence,
        e.validation_status,
        e.validation_message,
        ROW_NUMBER() OVER (
            PARTITION BY e.document_id, e.field_name
            ORDER BY e.created_at DESC
        ) AS rn
    FROM extractions e
)
SELECT
    d.filename,
    d.status,
    d.processed_at,
    d.processing_time_seconds,
    -- Additional fields
    MAX(CASE WHEN le.field_name = 'nome_produto' AND le.rn = 1 THEN le.value END) AS nome_produto,
    MAX(CASE WHEN le.field_name = 'nome_produto' AND le.rn = 1 THEN le.confidence END) AS nome_produto_confidence,
    MAX(CASE WHEN le.field_name = 'nome_produto' AND le.rn = 1 THEN le.validation_status END) AS nome_produto_status,
    MAX(CASE WHEN le.field_name = 'nome_produto' AND le.rn = 1 THEN le.validation_message END) AS nome_produto_validation_message,
    MAX(CASE WHEN le.field_name = 'fabricante' AND le.rn = 1 THEN le.value END) AS fabricante,
    MAX(CASE WHEN le.field_name = 'fabricante' AND le.rn = 1 THEN le.confidence END) AS fabricante_confidence,
    MAX(CASE WHEN le.field_name = 'fabricante' AND le.rn = 1 THEN le.validation_status END) AS fabricante_status,
    MAX(CASE WHEN le.field_name = 'fabricante' AND le.rn = 1 THEN le.validation_message END) AS fabricante_validation_message,
    MAX(CASE WHEN le.field_name = 'grupo_embalagem' AND le.rn = 1 THEN le.value END) AS grupo_embalagem,
    MAX(CASE WHEN le.field_name = 'grupo_embalagem' AND le.rn = 1 THEN le.confidence END) AS grupo_embalagem_confidence,
    MAX(CASE WHEN le.field_name = 'grupo_embalagem' AND le.rn = 1 THEN le.validation_status END) AS grupo_embalagem_status,
    MAX(CASE WHEN le.field_name = 'grupo_embalagem' AND le.rn = 1 THEN le.validation_message END) AS grupo_embalagem_validation_message,
    -- Core fields
    MAX(CASE WHEN le.field_name = 'numero_onu' AND le.rn = 1 THEN le.value END) AS numero_onu,
    MAX(CASE WHEN le.field_name = 'numero_onu' AND le.rn = 1 THEN le.confidence END) AS numero_onu_confidence,
    MAX(CASE WHEN le.field_name = 'numero_onu' AND le.rn = 1 THEN le.validation_status END) AS numero_onu_status,
    MAX(CASE WHEN le.field_name = 'numero_onu' AND le.rn = 1 THEN le.validation_message END) AS numero_onu_validation_message,
    MAX(CASE WHEN le.field_name = 'numero_cas' AND le.rn = 1 THEN le.value END) AS numero_cas,
    MAX(CASE WHEN le.field_name = 'numero_cas' AND le.rn = 1 THEN le.confidence END) AS numero_cas_confidence,
    MAX(CASE WHEN le.field_name = 'numero_cas' AND le.rn = 1 THEN le.validation_status END) AS numero_cas_status,
    MAX(CASE WHEN le.field_name = 'numero_cas' AND le.rn = 1 THEN le.validation_message END) AS numero_cas_validation_message,
    MAX(CASE WHEN le.field_name = 'classificacao_onu' AND le.rn = 1 THEN le.value END) AS classificacao_onu,
    MAX(CASE WHEN le.field_name = 'classificacao_onu' AND le.rn = 1 THEN le.confidence END) AS classificacao_onu_confidence,
    MAX(CASE WHEN le.field_name = 'classificacao_onu' AND le.rn = 1 THEN le.validation_status END) AS classificacao_onu_status,
    MAX(CASE WHEN le.field_name = 'classificacao_onu' AND le.rn = 1 THEN le.validation_message END) AS classificacao_onu_validation_message
FROM documents d
LEFT JOIN latest_extractions le ON le.document_id = d.id
WHERE d.status IN ('success', 'failed')
GROUP BY d.id, d.filename, d.status, d.processed_at, d.processing_time_seconds
ORDER BY d.processed_at DESC NULLS LAST, d.id DESC
"""

def load_results(limit: int | None = None) -> pd.DataFrame:
    """Return processed results as a DataFrame."""
    query = EXPORT_QUERY
    if limit:
        query = f"""
        SELECT * FROM (
            {EXPORT_QUERY}
        )
        LIMIT {int(limit)}
        """
    with duckdb.connect(str(DUCKDB_FILE)) as conn:
        logger.info("Loading results from DuckDB")
        df = conn.execute(query).df()
    return df

def export_to_csv(path: Path, limit: int | None = None) -> Path:
    """Export the processed data to CSV."""
    df = load_results(limit=limit)
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Results exported to CSV at %s", path)
    return path

def export_to_excel(path: Path, limit: int | None = None) -> Path:
    """Export the processed data to Excel."""
    df = load_results(limit=limit)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Resultados", index=False)
    logger.info("Results exported to Excel at %s", path)
    return path
