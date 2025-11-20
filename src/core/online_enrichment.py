"""Batch-oriented online enrichment utilities.

Provides per-row (document) processing that iterates over stored documents and
invokes online enrichment only where confidence is low or a field is missing.
This separates enrichment concerns from the core DocumentProcessor which
handles initial extraction + heuristics.
"""
# ruff: noqa: I001
from __future__ import annotations

from collections.abc import Sequence

from ..database.duckdb_manager import DuckDBManager  # noqa: I001
from ..database.duckdb_manager import DocumentRecord  # noqa: I001
from ..utils.config import (
    CONFIDENCE_THRESHOLD_LOW,
    CONFIDENCE_THRESHOLD_MID,
    REFINEMENT_MAX_ROUNDS,
)
from ..utils.logger import logger
from .document_processor import DocumentProcessor

class OnlineEnricher:
    """Coordinate per-document online + refinement passes.

    Minimal multi-pass logic (V1):
      Pass 1: call existing online search for missing fields.
      Pass 2 (optional): re-run if critical fields still below MID threshold.

    Future expansions (web crawling, per-field queries) will hook into the
    `_needs_refinement` decision.
    """

    def __init__(
        self,
        *,
        db: DuckDBManager,
        processor: DocumentProcessor,
        field_retriever=None,
    ) -> None:
        self.db = db
        self.processor = processor
        self.field_retriever = field_retriever

    # ---------------------- Public High-Level API ---------------------- #
    def enrich_all(self, limit: int = 200, only_success: bool = True) -> None:
        """Iterate documents and perform enrichment passes where needed."""
        docs: Sequence = self._select_documents(
            limit=limit, only_success=only_success
        )
        logger.info(
            "OnlineEnricher: starting batch for %d documents", len(docs)
        )
        for doc in docs:
            try:
                self.enrich_document(doc.id)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "OnlineEnricher: failed enrichment for doc %s", doc.id
                )

    def enrich_document(self, document_id: int) -> None:
        """Run online enrichment multi-pass for a single document."""
        field_details = self.db.get_field_details(document_id)
        if not field_details:
            logger.info(
                "Document %s has no extractions yet; skipping enrichment",
                document_id,
            )
            return

        # Optional pre-pass: per-field retrieval (web snippets)
        if self.field_retriever:
            known_vals = {
                k: field_details.get(k, {}).get("value")
                for k in ("nome_produto", "numero_cas", "numero_onu")
                if field_details.get(k, {}).get("value") not in (
                    None,
                    "",
                    "NAO ENCONTRADO",
                )
            }
            # Determine missing/low-confidence fields
            missing: list[str] = []
            for fname, data in field_details.items():
                val = str(data.get("value") or "")
                conf_raw = data.get("confidence", 0.0)
                try:
                    conf = (
                        float(conf_raw)
                        if isinstance(conf_raw, (int, float, str))
                        else 0.0
                    )
                except Exception:  # noqa: BLE001
                    conf = 0.0
                if val == "NAO ENCONTRADO" or conf < CONFIDENCE_THRESHOLD_LOW:
                    missing.append(fname)
            if missing:
                logger.info(
                    "OnlineEnricher: retrieval pre-pass for doc %s fields=%s",
                    document_id,
                    missing,
                )
                try:
                    self.field_retriever.retrieve_missing_fields(
                        document_id=document_id,
                        missing_fields=missing,
                        known=known_vals,
                    )
                    # Refresh field details after retrieval
                    field_details = self.db.get_field_details(document_id)
                except Exception:  # noqa: BLE001
                    logger.exception(
                        "OnlineEnricher: field retrieval failed for doc %s",
                        document_id,
                    )

        # Initial pass: processor reprocesses (ONU table + online search)
        logger.info("OnlineEnricher: pass 1 for document %s", document_id)
        self.processor.reprocess_online(document_id)

        # Targeted refinement rounds (vector + LLM on low-confidence fields)
        details_after = self.db.get_field_details(document_id)
        round_idx = 0
        while round_idx < REFINEMENT_MAX_ROUNDS:
            to_refine: list[str] = []
            for fname, data in details_after.items():
                val = str(data.get("value") or "")
                raw_conf = data.get("confidence", 0.0)
                try:
                    conf = (
                        float(raw_conf)
                        if isinstance(raw_conf, (int, float, str))
                        else 0.0
                    )
                except Exception:  # noqa: BLE001
                    conf = 0.0
                # Skip if already high or not extracted
                if val == "NAO ENCONTRADO":
                    continue  # wait for future passes / external search
                if conf >= CONFIDENCE_THRESHOLD_MID:
                    continue
                if conf < CONFIDENCE_THRESHOLD_LOW:
                    continue  # rely on retrieval/online search first
                to_refine.append(fname)
            if not to_refine:
                break
            logger.info(
                "OnlineEnricher: targeted refine round %d fields=%s doc=%s",
                round_idx + 1,
                to_refine,
                document_id,
            )
            try:
                self.processor.refine_fields(document_id, to_refine)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "OnlineEnricher: refine_fields failed doc=%s", document_id
                )
                break
            details_after = self.db.get_field_details(document_id)
            round_idx += 1

    # ---------------------------- Internals ---------------------------- #
    def _select_documents(
        self, *, limit: int, only_success: bool
    ) -> Sequence[DocumentRecord]:
        all_docs: Sequence[DocumentRecord] = self.db.fetch_documents(
            limit=limit
        )
        if not only_success:
            return all_docs
        return [d for d in all_docs if d.status == "success"]

    def _needs_refinement(
        self, field_details: dict[str, dict[str, object]]
    ) -> bool:
        """Return True if any critical field remains below thresholds."""
        critical_fields = {"numero_onu", "numero_cas", "classificacao_onu"}
        for name in critical_fields:
            data = field_details.get(name)
            if not data:
                return True
            raw_conf = data.get("confidence", 0.0)
            try:
                conf = (
                    float(raw_conf)
                    if isinstance(raw_conf, (int, float, str))
                    else 0.0
                )
            except Exception:  # noqa: BLE001
                conf = 0.0
            if conf < CONFIDENCE_THRESHOLD_LOW:
                return True
        # If critical above LOW but below MID -> refine.
        # require ANY critical below MID to trigger second pass.
        for n in critical_fields:
            raw_conf = field_details.get(n, {}).get("confidence", 0.0)
            try:
                conf_mid = (
                    float(raw_conf)
                    if isinstance(raw_conf, (int, float, str))
                    else 0.0
                )
            except Exception:  # noqa: BLE001
                conf_mid = 0.0
            if conf_mid < CONFIDENCE_THRESHOLD_MID:
                return True
        return False

__all__ = ["OnlineEnricher"]

__all__ = ["OnlineEnricher"]
