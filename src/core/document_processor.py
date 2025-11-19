"""High-level document processing orchestration."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Any, cast

from ..database.duckdb_manager import DuckDBManager
from ..extractors.base_extractor import BaseExtractor, ExtractionPayload
from ..extractors.pdf_extractor import PDFExtractor
from ..utils.config import MAX_FILE_SIZE_MB, SUPPORTED_FORMATS
from ..utils.logger import logger
from .chunk_strategy import Chunk, ChunkStrategy
from .llm_client import LMStudioClient
from .heuristics import HeuristicExtractor
from .validator import validate_field


@dataclass(frozen=True)
class FieldExtractionConfig:
    """Configuration for extracting a specific field."""

    name: str
    label: str
    prompt_template: str


DEFAULT_FIELDS: List[FieldExtractionConfig] = [
    FieldExtractionConfig(
        name="numero_onu",
        label="Numero ONU",
        prompt_template=(
            "TAREFA: Extraia o numero ONU (UN number) do produto quimico.\n"
            "Se existir, responda apenas com o numero de quatro digitos.\n"
            "Se nao encontrar, responda exatamente com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
    FieldExtractionConfig(
        name="numero_cas",
        label="Numero CAS",
        prompt_template=(
            "TAREFA: Identifique o numero CAS do produto.\n"
            "Retorne no formato ####-##-# (ou similar com 2 a 7 digitos na primeira parte).\n"
            "Se nao encontrar, responda com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
    FieldExtractionConfig(
        name="classificacao_onu",
        label="Classificacao ONU",
        prompt_template=(
            "TAREFA: Extraia a classe ONU (classe de risco) do produto.\n"
            "Responda apenas com o numero da classe ou subclasse (ex.: 3, 2.3, 6.1).\n"
            "Se nao encontrar, responda com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
]

# Additional fields supported by the app (kept separate to preserve default behavior in tests)
ADDITIONAL_FIELDS: List[FieldExtractionConfig] = [
    FieldExtractionConfig(
        name="nome_produto",
        label="Nome do Produto",
        prompt_template=(
            "TAREFA: Identifique o nome completo do produto quimico.\n"
            "Extraia da Secao 1 (Identificacao do Produto).\n"
            "Responda apenas com o nome, sem informacoes adicionais.\n"
            "Se nao encontrar, responda com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
    FieldExtractionConfig(
        name="fabricante",
        label="Fabricante",
        prompt_template=(
            "TAREFA: Identifique o nome do fabricante ou fornecedor do produto.\n"
            "Extraia da Secao 1 (Identificacao da Empresa).\n"
            "Responda apenas com o nome da empresa.\n"
            "Se nao encontrar, responda com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
    FieldExtractionConfig(
        name="grupo_embalagem",
        label="Grupo de Embalagem",
        prompt_template=(
            "TAREFA: Identifique o grupo de embalagem para transporte.\n"
            "Deve ser I, II ou III (algarismos romanos).\n"
            "Extraia da Secao 14 (Informacoes sobre Transporte).\n"
            "Se nao encontrar, responda com 'NAO ENCONTRADO'.\n\n"
            "TRECHO DA FDS ({chunk_label}):\n{document_text}\n"
        ),
    ),
]


class DocumentProcessor:
    """Hand orchestrate extraction flow for a single document."""

    def __init__(
        self,
        *,
        db_manager: DuckDBManager,
        llm_client: LMStudioClient | None,
    online_search_client: Any | None = None,
        chunk_strategy: ChunkStrategy | None = None,
        extractors: Iterable[BaseExtractor] | None = None,
        fields: Iterable[FieldExtractionConfig] | None = None,
        heuristic_extractor: HeuristicExtractor | None = None,
        heuristic_confidence_skip: float = 0.82,
    ) -> None:
        self.db = db_manager
        self.llm = llm_client
        # Optional dedicated client for online search (e.g., Gemini)
        self.online_search = online_search_client
        self.chunk_strategy = chunk_strategy or ChunkStrategy()
        self.extractors = list(extractors or [PDFExtractor()])
        self.fields = list(fields or DEFAULT_FIELDS)
        self.heuristics = heuristic_extractor or HeuristicExtractor()
        self.heuristic_confidence_skip = heuristic_confidence_skip

    def process(self, file_path: Path, *, mode: str = "online") -> None:
        """Fully process a document path."""
        logger.info("Processing document %s", file_path)
        self._validate_file(file_path)

        mode_normalized = mode.lower()
        extractor = self._select_extractor(file_path)
        start = time.perf_counter()

        # Register document early so failures can be tracked in DB
        document_id = self.db.register_document(
            filename=file_path.name,
            file_path=file_path,
            file_size=file_path.stat().st_size,
            file_type=SUPPORTED_FORMATS.get(file_path.suffix.lower(), "Unknown"),
            num_pages=None,
        )

        try:
            data = extractor.extract(file_path)

            # Ensure proper typing for downstream functions
            full_text = str(data.get("text", ""))
            sections = cast(dict[int, str] | None, data.get("sections") if isinstance(data.get("sections"), dict) else None)
            chunks = self.chunk_strategy.make_chunks(
                text=full_text,
                sections=sections,
            )

            heuristic_hints = self.heuristics.extract(
                text=full_text,
                sections=sections,
            )

            # Always run local heuristics + LLM; online mode adds a later web completion step
            self._run_field_extractions(
                document_id,
                chunks,
                heuristic_hints,
                force_skip_llm=False,
            )
            elapsed = time.perf_counter() - start
            self.db.update_document_status(
                document_id,
                status="success",
                processing_time_seconds=elapsed,
            )
            logger.info("Document %s processed in %.2fs", file_path, elapsed)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - start
            self.db.update_document_status(
                document_id,
                status="failed",
                processing_time_seconds=elapsed,
                error_message=str(exc),
            )
            logger.exception("Failed to process document %s", file_path)
            raise
        finally:
            # After local extraction/LLM, perform online completion when requested
            try:
                if mode_normalized == "online":
                    self._search_online_for_missing_fields(document_id)
            except Exception:
                logger.exception("Online completion step failed for document %s", document_id)

    def _validate_file(self, file_path: Path) -> None:
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        file_size = file_path.stat().st_size
        if file_size > max_bytes:
            raise ValueError(
                f"Arquivo {file_path.name} excede o limite configurado de {MAX_FILE_SIZE_MB}MB."
            )

    def _select_extractor(self, file_path: Path) -> BaseExtractor:
        for extractor in self.extractors:
            if extractor.can_handle(file_path):
                return extractor
        raise ValueError(f"Nao ha extrator para o arquivo {file_path}")

    def _run_field_extractions(
        self,
        document_id: int,
        chunks: List[Chunk],
        heuristic_hints: dict[str, dict[str, object]],
        *,
        force_skip_llm: bool = False,
    ) -> None:
        if not chunks:
            logger.warning("Nenhum conteudo encontrado para o documento %s", document_id)
            return

        # If any heuristic has high confidence, skip LLM for all fields to save latency
        def _as_float(val: object, default: float = 0.0) -> float:
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                return float(str(val))
            except Exception:
                return default

        skip_all_llm = (
            force_skip_llm
            or any(_as_float(h.get("confidence"), 0.0) >= self.heuristic_confidence_skip for h in heuristic_hints.values())
            or not self.llm
        )

        for field in self.fields:
            best_result = dict(heuristic_hints.get(field.name, {}))
            if not best_result:
                best_result = {"value": "NAO ENCONTRADO", "confidence": 0.0, "context": ""}

            skip_llm = skip_all_llm or (_as_float(best_result.get("confidence", 0.0), 0.0) >= self.heuristic_confidence_skip)

            if self.llm and not skip_llm:
                for chunk in chunks:
                    prompt = field.prompt_template.format(
                        chunk_label=chunk.label,
                        document_text=chunk.text,
                        field_name=field.label,
                    )
                    response = self.llm.extract_field(
                        field_name=field.label,
                        prompt_template=prompt,
                    )

                    if _as_float(response.get("confidence", 0.0), 0.0) >= _as_float(best_result.get("confidence", 0.0), 0.0):
                        best_result = response

                    if _as_float(best_result.get("confidence", 0.0), 0.0) >= 0.95:
                        break

            status, message = validate_field(field.name, best_result)
            self.db.store_extraction(
                document_id=document_id,
                field_name=field.name,
                value=str(best_result["value"]),
                confidence=_as_float(best_result.get("confidence", 0.0), 0.0),
                context=str(best_result.get("context", "")),
                validation_status=status,
                validation_message=message,
            )
        
    # Online completion moved to 'process' based on selected mode
    
    def _search_online_for_missing_fields(self, document_id: int) -> None:
        """Search online for fields with low confidence or invalid status."""
        # Prefer a dedicated online search client if provided; otherwise reuse self.llm
        client = self.online_search or self.llm
        if not client:
            return
        
        # Get current field values
        field_details = self.db.get_field_details(document_id)

        # Identify missing or low-confidence fields
        missing_fields = []
        known_values = {}

        for field in self.fields:
            details = field_details.get(field.name, {})
            value = details.get("value", "NAO ENCONTRADO")
            confidence = float(cast(float, details.get("confidence", 0.0) or 0.0))
            status = details.get("validation_status", "invalid")

            # Collect known good values for search context
            if confidence >= 0.7 and value != "NAO ENCONTRADO":
                known_values[field.name] = value
            # Mark as missing if low confidence or invalid
            elif confidence < 0.7 or status == "invalid" or value == "NAO ENCONTRADO":
                missing_fields.append(field.name)
        
        # Always attempt to fetch incompatibilidades as an extra online-only field
        if "incompatibilidades" not in missing_fields:
            missing_fields.append("incompatibilidades")

        if not missing_fields:
            logger.info("All fields have acceptable confidence, skipping online search")
            return
        
        logger.info("Searching online for %d missing fields: %s", len(missing_fields), missing_fields)
        
        # Perform online search
        try:
            # Duck typing: client must implement search_online_for_missing_fields
            online_results = client.search_online_for_missing_fields(
                product_name=known_values.get("nome_produto"),
                cas_number=known_values.get("numero_cas"),
                un_number=known_values.get("numero_onu"),
                missing_fields=missing_fields,
            )
            
            # Store improved results
            for field_name, result in online_results.items():
                conf_val = float(cast(float, result.get("confidence", 0.0) or 0.0))
                if conf_val > 0.5:  # Only store if reasonably confident
                    status, message = validate_field(field_name, result)
                    self.db.store_extraction(
                        document_id=document_id,
                        field_name=field_name,
                        value=str(result["value"]),
                        confidence=conf_val,
                        context=f"Online search: {result.get('context', '')}",
                        validation_status=status,
                        validation_message=message,
                    )
                    logger.info("Updated %s from online search: %s (confidence: %.2f)", 
                               field_name, result["value"], result["confidence"])
        except Exception as exc:  # noqa: BLE001
            logger.error("Online search failed: %s", exc)

    def reprocess_online(self, document_id: int) -> None:
        """Run only the online search step again for a processed document.

        This does not re-read the file; it looks at current stored values and
        tries to fill missing/low-confidence fields via the configured online client.
        """
        self._search_online_for_missing_fields(document_id)
