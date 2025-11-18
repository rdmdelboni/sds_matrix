"""DuckDB persistence layer."""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Sequence

import duckdb

from ..utils.config import DUCKDB_FILE
from ..utils.logger import logger


@dataclass(slots=True)
class DocumentRecord:
    """Representation of a stored document."""

    id: int
    filename: str
    file_path: str
    status: str
    processed_at: Optional[datetime]
    error_message: Optional[str]


class DuckDBManager:
    """Lightweight wrapper for DuckDB operations used in the MVP."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DUCKDB_FILE
        self.conn = duckdb.connect(str(self.db_path))
        self._lock = threading.Lock()  # Thread-safe access to DuckDB connection
        logger.info("Connected to DuckDB database at %s", self.db_path)
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create the minimum schema if it is not present."""
        logger.debug("Ensuring DuckDB schema is ready.")
        with self._lock:
            # Create sequences for auto-increment behavior
            self.conn.execute("CREATE SEQUENCE IF NOT EXISTS documents_seq START 1;")
            self.conn.execute("CREATE SEQUENCE IF NOT EXISTS extractions_seq START 1;")

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id BIGINT PRIMARY KEY DEFAULT nextval('documents_seq'),
                    filename VARCHAR NOT NULL,
                    file_path VARCHAR NOT NULL,
                    file_hash VARCHAR UNIQUE NOT NULL,
                    file_size_bytes BIGINT,
                    file_type VARCHAR,
                    num_pages INTEGER,
                    status VARCHAR DEFAULT 'pending',
                    processed_at TIMESTAMP,
                    processing_time_seconds DOUBLE,
                    error_message TEXT
                );
                """
            )

            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS extractions (
                    id BIGINT PRIMARY KEY DEFAULT nextval('extractions_seq'),
                    document_id INTEGER NOT NULL,
                    field_name VARCHAR NOT NULL,
                    value TEXT,
                    confidence DOUBLE,
                    context TEXT,
                    validation_status VARCHAR,
                    validation_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    @staticmethod
    def calculate_hash(file_path: Path) -> str:
        """Return the SHA256 hash for the given file."""
        digest = hashlib.sha256()
        with file_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def register_document(
        self,
        filename: str,
        file_path: Path,
        file_size: int,
        file_type: str,
        num_pages: Optional[int] = None,
    ) -> int:
        """Create or reuse a document entry and return its id."""
        file_hash = self.calculate_hash(file_path)
        with self._lock:
            existing = self.conn.execute(
                "SELECT id FROM documents WHERE file_hash = ?",
                [file_hash],
            ).fetchone()

            if existing:
                logger.info("Document already registered: %s", filename)
                return existing[0]

            logger.info("Registering new document: %s", filename)
            result = self.conn.execute(
                """
                INSERT INTO documents (
                    filename,
                    file_path,
                    file_hash,
                    file_size_bytes,
                    file_type,
                    num_pages,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pending')
                RETURNING id;
                """,
                [filename, str(file_path), file_hash, file_size, file_type, num_pages],
            ).fetchone()

            if not result:
                raise RuntimeError("Failed to register document in database.")

            return int(result[0])

    def update_document_status(
        self,
        document_id: int,
        *,
        status: str,
        processing_time_seconds: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update a document status."""
        logger.info(
            "Updating document %s status to %s (error=%s)",
            document_id,
            status,
            error_message,
        )
        with self._lock:
            self.conn.execute(
                """
                UPDATE documents
                SET status = ?,
                    processed_at = CURRENT_TIMESTAMP,
                    processing_time_seconds = COALESCE(?, processing_time_seconds),
                    error_message = ?
                WHERE id = ?;
                """,
                [status, processing_time_seconds, error_message, document_id],
            )

    def store_extraction(
        self,
        document_id: int,
        field_name: str,
        value: str,
        confidence: float,
        context: str,
        validation_status: str,
        validation_message: Optional[str],
    ) -> None:
        """Persist an extraction result."""
        logger.debug(
            "Persisting extraction doc=%s field=%s value=%s",
            document_id,
            field_name,
            value,
        )
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO extractions (
                    document_id,
                    field_name,
                    value,
                    confidence,
                    context,
                    validation_status,
                    validation_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                [
                    document_id,
                    field_name,
                    value,
                    confidence,
                    context,
                    validation_status,
                    validation_message,
                ],
            )

    def fetch_documents(self, limit: int = 100) -> Sequence[DocumentRecord]:
        """Return recent documents for UI display."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT id, filename, file_path, status, processed_at, error_message
                FROM documents
                ORDER BY processed_at DESC NULLS LAST, id DESC
                LIMIT ?;
                """,
                [limit],
            ).fetchall()
            return [
                DocumentRecord(
                    id=row[0],
                    filename=row[1],
                    file_path=row[2],
                    status=row[3],
                    processed_at=row[4],
                    error_message=row[5],
                )
                for row in rows
            ]

    def fetch_extractions(self, document_id: int) -> Iterable[tuple[str, str, float]]:
        """Return extractions for a given document."""
        with self._lock:
            return self.conn.execute(
                """
                SELECT field_name, value, confidence
                FROM extractions
                WHERE document_id = ?
                ORDER BY field_name;
                """,
                [document_id],
            ).fetchall()

    def get_document_id(self, file_path: Path) -> Optional[int]:
        """Return the document id for a persisted path, if present."""
        with self._lock:
            row = self.conn.execute(
                "SELECT id FROM documents WHERE file_path = ?",
                [str(file_path)],
            ).fetchone()
            return int(row[0]) if row else None

    def get_field_details(self, document_id: int) -> dict[str, dict[str, object]]:
        """Return the latest value, confidence and validation metadata for each field."""
        with self._lock:
            rows = self.conn.execute(
                """
                SELECT field_name, value, confidence, validation_status, validation_message
                FROM extractions
                WHERE document_id = ?
                ORDER BY created_at DESC;
                """,
                [document_id],
            ).fetchall()
            details: dict[str, dict[str, object]] = {}
            for field_name, value, confidence, status, message in rows:
                if field_name in details:
                    continue
                details[field_name] = {
                    "value": value,
                    "confidence": confidence,
                    "validation_status": status,
                    "validation_message": message,
                }
            return details

    def get_field_values(self, document_id: int) -> dict[str, str]:
        """Return only the latest field values (compatibility helper)."""
        details = self.get_field_details(document_id)
        return {field: str(data.get("value") or "") for field, data in details.items()}

    def fetch_recent_results(self, limit: int = 100) -> list[dict[str, object]]:
        """Return aggregated results ready for GUI presentation."""
        query = """
            WITH latest AS (
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
                d.id,
                d.filename,
                d.status,
                d.processed_at,
                d.processing_time_seconds,
                    MAX(CASE WHEN latest.field_name = 'nome_produto' AND latest.rn = 1 THEN latest.value END) AS nome_produto,
                    MAX(CASE WHEN latest.field_name = 'nome_produto' AND latest.rn = 1 THEN latest.confidence END) AS nome_produto_confidence,
                    MAX(CASE WHEN latest.field_name = 'fabricante' AND latest.rn = 1 THEN latest.value END) AS fabricante,
                    MAX(CASE WHEN latest.field_name = 'fabricante' AND latest.rn = 1 THEN latest.confidence END) AS fabricante_confidence,
                MAX(CASE WHEN latest.field_name = 'numero_onu' AND latest.rn = 1 THEN latest.value END) AS numero_onu,
                MAX(CASE WHEN latest.field_name = 'numero_onu' AND latest.rn = 1 THEN latest.confidence END) AS numero_onu_confidence,
                MAX(CASE WHEN latest.field_name = 'numero_onu' AND latest.rn = 1 THEN latest.validation_status END) AS numero_onu_status,
                MAX(CASE WHEN latest.field_name = 'numero_onu' AND latest.rn = 1 THEN latest.validation_message END) AS numero_onu_message,
                MAX(CASE WHEN latest.field_name = 'numero_cas' AND latest.rn = 1 THEN latest.value END) AS numero_cas,
                MAX(CASE WHEN latest.field_name = 'numero_cas' AND latest.rn = 1 THEN latest.confidence END) AS numero_cas_confidence,
                MAX(CASE WHEN latest.field_name = 'numero_cas' AND latest.rn = 1 THEN latest.validation_status END) AS numero_cas_status,
                MAX(CASE WHEN latest.field_name = 'numero_cas' AND latest.rn = 1 THEN latest.validation_message END) AS numero_cas_message,
                MAX(CASE WHEN latest.field_name = 'classificacao_onu' AND latest.rn = 1 THEN latest.value END) AS classificacao_onu,
                MAX(CASE WHEN latest.field_name = 'classificacao_onu' AND latest.rn = 1 THEN latest.confidence END) AS classificacao_onu_confidence,
                MAX(CASE WHEN latest.field_name = 'classificacao_onu' AND latest.rn = 1 THEN latest.validation_status END) AS classificacao_onu_status,
                    MAX(CASE WHEN latest.field_name = 'classificacao_onu' AND latest.rn = 1 THEN latest.validation_message END) AS classificacao_onu_message,
                    MAX(CASE WHEN latest.field_name = 'grupo_embalagem' AND latest.rn = 1 THEN latest.value END) AS grupo_embalagem,
                    MAX(CASE WHEN latest.field_name = 'grupo_embalagem' AND latest.rn = 1 THEN latest.confidence END) AS grupo_embalagem_confidence,
                    MAX(CASE WHEN latest.field_name = 'incompatibilidades' AND latest.rn = 1 THEN latest.value END) AS incompatibilidades,
                    MAX(CASE WHEN latest.field_name = 'incompatibilidades' AND latest.rn = 1 THEN latest.confidence END) AS incompatibilidades_confidence
            FROM documents d
            LEFT JOIN latest ON latest.document_id = d.id
            WHERE d.status IN ('success', 'failed')
            GROUP BY d.id, d.filename, d.status, d.processed_at, d.processing_time_seconds
            ORDER BY d.processed_at DESC NULLS LAST, d.id DESC
            LIMIT ?;
        """
        with self._lock:
            rows = self.conn.execute(query, [limit]).fetchall()
            return [
                {
                    "id": row[0],
                    "filename": row[1],
                    "status": row[2],
                    "processed_at": row[3],
                    "processing_time_seconds": row[4],
                        "nome_produto": row[5],
                        "nome_produto_confidence": row[6],
                        "fabricante": row[7],
                        "fabricante_confidence": row[8],
                        "numero_onu": row[9],
                        "numero_onu_confidence": row[10],
                        "numero_onu_status": row[11],
                        "numero_onu_message": row[12],
                        "numero_cas": row[13],
                        "numero_cas_confidence": row[14],
                        "numero_cas_status": row[15],
                        "numero_cas_message": row[16],
                        "classificacao_onu": row[17],
                        "classificacao_onu_confidence": row[18],
                        "classificacao_onu_status": row[19],
                        "classificacao_onu_message": row[20],
                        "grupo_embalagem": row[21],
                        "grupo_embalagem_confidence": row[22],
                        "incompatibilidades": row[23],
                        "incompatibilidades_confidence": row[24],
                }
                for row in rows
            ]
