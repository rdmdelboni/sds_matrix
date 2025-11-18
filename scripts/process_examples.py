"""Command-line helper to process PDFs stored in the examples folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _extend_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    src_dir = base_dir / "src"
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    return base_dir


BASE_DIR = _extend_path()

from src.core.chunk_strategy import ChunkStrategy  # noqa: E402
from src.core.document_processor import DocumentProcessor  # noqa: E402
from src.core.llm_client import LMStudioClient  # noqa: E402
from src.database.duckdb_manager import DuckDBManager  # noqa: E402
from src.utils.file_utils import list_supported_files  # noqa: E402
from src.utils.logger import logger  # noqa: E402


def _init_llm(disable_llm: bool) -> LMStudioClient | None:
    if disable_llm:
        logger.info("LLM usage disabled via CLI flag; relying on heuristics only.")
        return None
    try:
        client = LMStudioClient()
        if not client.test_connection():
            logger.warning("LLM server not reachable; continuing with heuristics only.")
            return None
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise LLM client: %s", exc)
        return None


def process_examples(use_llm: bool) -> None:
    examples_dir = BASE_DIR / "examples"

    if not examples_dir.exists():
        raise SystemExit(f"Examples directory not found: {examples_dir}")

    files = list_supported_files(examples_dir)
    if not files:
        logger.warning("No supported documents found in %s", examples_dir)
        return

    logger.info("Processing %s examples from %s", len(files), examples_dir)

    db_manager = DuckDBManager()
    llm_client = _init_llm(disable_llm=not use_llm)

    processor = DocumentProcessor(
        db_manager=db_manager,
        llm_client=llm_client,
        chunk_strategy=ChunkStrategy(),
    )

    for path in files:
        try:
            processor.process(path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Processing failed for %s: %s", path.name, exc)

    results = db_manager.fetch_recent_results(limit=len(files))
    logger.info("Finished. Summary of extracted fields:\n")
    for row in results:
        logger.info(
            "%s -> ONU: %s (%.2f, %s) | CAS: %s (%.2f, %s) | Classe: %s (%.2f, %s)",
            row["filename"],
            row.get("numero_onu") or "-",
            row.get("numero_onu_confidence") or 0.0,
            row.get("numero_onu_status") or "-",
            row.get("numero_cas") or "-",
            row.get("numero_cas_confidence") or 0.0,
            row.get("numero_cas_status") or "-",
            row.get("classificacao_onu") or "-",
            row.get("classificacao_onu_confidence") or 0.0,
            row.get("classificacao_onu_status") or "-",
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Process sample FDS documents from the examples folder.",
    )
    parser.add_argument(
        "--heuristics-only",
        action="store_true",
        help="Skip LM Studio calls and rely solely on heuristic extraction.",
    )
    args = parser.parse_args()
    process_examples(use_llm=not args.heuristics_only)


if __name__ == "__main__":
    main()
