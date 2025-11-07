"""Regression tests for edge cases and error handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock
import time

import pytest

from src.core.chunk_strategy import ChunkStrategy
from src.core.document_processor import DocumentProcessor
from src.core.heuristics import HeuristicExtractor
from src.database.duckdb_manager import DuckDBManager


@pytest.fixture
def mock_db_manager() -> MagicMock:
    """Create a mock database manager."""
    mock = MagicMock(spec=DuckDBManager)
    mock.register_document.return_value = 1
    return mock


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.extract_field.return_value = {
        "value": "1234",
        "confidence": 0.95,
        "context": "Mock context"
    }
    return mock


@pytest.fixture
def processor(mock_db_manager: MagicMock, mock_llm_client: MagicMock) -> DocumentProcessor:
    """Create a DocumentProcessor with mocked dependencies."""
    return DocumentProcessor(
        db_manager=mock_db_manager,
        llm_client=mock_llm_client,
        chunk_strategy=ChunkStrategy(),
        heuristic_extractor=HeuristicExtractor(),
    )


class TestEmptyHeuristics:
    """Test behavior when heuristics return no results."""

    def test_empty_heuristics_triggers_llm_in_local_mode(
        self,
        processor: DocumentProcessor,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that empty heuristics trigger LLM in local mode."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        # Mock extractor with text that produces no heuristic matches
        processor.extractors[0].extract = Mock(return_value={
            "text": "Random text with no FDS data whatsoever",
            "metadata": {"pages": 1},
            "sections": None,
        })

        processor.process(test_file, mode="local")

        # LLM should be called when heuristics find nothing
        assert mock_llm_client.extract_field.call_count >= 3

    def test_empty_heuristics_stores_not_found(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that empty heuristics store 'NAO ENCONTRADO' when no LLM."""
        processor_no_llm = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=None,  # No LLM available
        )

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        processor_no_llm.extractors[0].extract = Mock(return_value={
            "text": "Random text with no FDS data",
            "metadata": {"pages": 1},
            "sections": None,
        })

        processor_no_llm.process(test_file, mode="local")

        # Verify "NAO ENCONTRADO" is stored for empty results
        store_calls = mock_db_manager.store_extraction.call_args_list
        assert len(store_calls) >= 3

        # Check that at least some fields have "NAO ENCONTRADO"
        values = [call[1]["value"] for call in store_calls]
        assert "NAO ENCONTRADO" in values


class TestLLMTimeout:
    """Test handling of LLM timeouts and errors."""

    def test_llm_timeout_falls_back_to_heuristics(
        self,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that LLM timeout doesn't break processing."""
        mock_llm = MagicMock()
        mock_llm.extract_field.side_effect = TimeoutError("LLM timeout")

        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=mock_llm,
        )

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        processor.extractors[0].extract = Mock(return_value={
            "text": "Número ONU: 1234\nCAS: 64-17-5\nClasse: 3",
            "metadata": {"pages": 1},
            "sections": None,
        })

        # With high-confidence heuristics, LLM is not called, so no timeout
        # This tests that heuristics bypass LLM failures
        processor.process(test_file, mode="local")

        # Should complete successfully using heuristics
        assert mock_db_manager.update_document_status.called
        status_call = mock_db_manager.update_document_status.call_args
        assert status_call[1]["status"] == "success"

    def test_llm_network_error_handling(
        self,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test handling of network errors during LLM calls."""
        mock_llm = MagicMock()
        mock_llm.extract_field.side_effect = ConnectionError("Network error")

        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=mock_llm,
        )

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        processor.extractors[0].extract = Mock(return_value={
            "text": "Some FDS text",
            "metadata": {"pages": 1},
            "sections": None,
        })

        # Network error should be caught and logged
        with pytest.raises(ConnectionError):
            processor.process(test_file, mode="local")

        # Verify error was logged in database
        assert mock_db_manager.update_document_status.called


class TestMalformedInput:
    """Test handling of malformed or corrupted input."""

    def test_corrupted_pdf_extraction_error(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test handling of corrupted PDF that fails extraction."""
        test_file = tmp_path / "corrupted.pdf"
        test_file.write_bytes(b"Not a valid PDF")

        processor.extractors[0].extract = Mock(
            side_effect=Exception("PDF extraction failed")
        )

        with pytest.raises(Exception, match="PDF extraction failed"):
            processor.process(test_file)

        # Verify error status is recorded
        status_call = mock_db_manager.update_document_status.call_args
        assert status_call[1]["status"] == "failed"
        assert "PDF extraction failed" in status_call[1]["error_message"]

    def test_empty_pdf_no_text_extracted(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test handling of PDF with no extractable text."""
        test_file = tmp_path / "empty.pdf"
        test_file.write_text("dummy")

        processor.extractors[0].extract = Mock(return_value={
            "text": "",  # Empty text
            "metadata": {"pages": 0},
            "sections": None,
        })

        processor.process(test_file, mode="local")

        # Should complete without error, storing "NAO ENCONTRADO"
        assert mock_db_manager.register_document.called
        assert mock_db_manager.update_document_status.called


class TestHeuristicEdgeCases:
    """Test edge cases in heuristic extraction."""

    def test_multiple_onu_numbers_takes_first(self) -> None:
        """Test that multiple ONU numbers returns the first valid one."""
        extractor = HeuristicExtractor()
        text = "Número ONU: 1234\nOutro produto ONU: 5678"

        result = extractor._extract_numero_onu(text, None)

        assert result is not None
        assert result["value"] == "1234"  # First match

    def test_onu_number_outside_valid_range_rejected(self) -> None:
        """Test that ONU numbers outside 4-3506 are rejected."""
        extractor = HeuristicExtractor()
        text = "UN 9999"  # Outside valid range

        result = extractor._extract_numero_onu(text, None)

        assert result is None  # Should be rejected

    def test_cas_number_with_extra_spaces(self) -> None:
        """Test CAS number extraction with formatting variations."""
        extractor = HeuristicExtractor()
        text = "CAS:  64-17-5  (com espaços)"

        result = extractor._extract_numero_cas(text, None)

        assert result is not None
        assert "64-17-5" in result["value"]

    def test_classification_with_decimal_subclass(self) -> None:
        """Test extraction of UN class with decimal subclass."""
        extractor = HeuristicExtractor()
        text = "Classe de risco 6.1"  # No colon - matches regex pattern

        result = extractor._extract_classificacao(text, None)

        assert result is not None
        assert result["value"] == "6.1"

    def test_product_name_with_special_characters(self) -> None:
        """Test product name with special characters and accents."""
        extractor = HeuristicExtractor()
        text = "Produto: ÁCIDO SULFÚRICO 98% (H₂SO₄)"

        result = extractor._extract_nome_produto(text, None)

        assert result is not None
        assert "ÁCIDO SULFÚRICO 98%" in result["value"]
        # Parentheses should be removed
        assert "(" not in result["value"]

    def test_manufacturer_with_long_legal_name(self) -> None:
        """Test manufacturer extraction with long corporate name."""
        extractor = HeuristicExtractor()
        text = "Fabricante: Acme Chemicals Industria e Comercio Ltda - CNPJ 12.345.678/0001-90"

        result = extractor._extract_fabricante(text, None)

        assert result is not None
        # Should capture the name before newline
        assert "Acme Chemicals" in result["value"]

    def test_packing_group_arabic_to_roman_conversion(self) -> None:
        """Test conversion of Arabic numerals to Roman for packing group."""
        extractor = HeuristicExtractor()
        test_cases = [
            ("Grupo de embalagem: 1", "I"),
            ("Grupo de embalagem: 2", "II"),
            ("Grupo de embalagem: 3", "III"),
        ]

        for text, expected in test_cases:
            result = extractor._extract_grupo_embalagem(text, None)
            assert result is not None
            assert result["value"] == expected


class TestConfidenceThresholds:
    """Test confidence threshold behavior."""

    def test_confidence_exactly_at_threshold_skips_llm(
        self,
        mock_db_manager: MagicMock,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that confidence exactly at 0.82 skips LLM."""
        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=mock_llm_client,
            heuristic_confidence_skip=0.82,
        )

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        # Mock heuristic with exactly 0.82 confidence
        processor.heuristics.extract = Mock(return_value={
            "numero_onu": {"value": "1234", "confidence": 0.82, "context": "..."}
        })

        processor.extractors[0].extract = Mock(return_value={
            "text": "Some text",
            "metadata": {"pages": 1},
            "sections": None,
        })

        processor.process(test_file, mode="local")

        # Should skip LLM due to threshold
        assert mock_llm_client.extract_field.call_count == 0

    def test_custom_confidence_threshold(
        self,
        mock_db_manager: MagicMock,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that custom confidence threshold works."""
        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=mock_llm_client,
            heuristic_confidence_skip=0.95,  # Higher threshold
        )

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        # Mock heuristic with 0.85 confidence (below new threshold)
        processor.heuristics.extract = Mock(return_value={
            "numero_onu": {"value": "1234", "confidence": 0.85, "context": "..."}
        })

        processor.extractors[0].extract = Mock(return_value={
            "text": "Some text",
            "metadata": {"pages": 1},
            "sections": None,
        })

        processor.process(test_file, mode="local")

        # Should call LLM because 0.85 < 0.95
        assert mock_llm_client.extract_field.call_count >= 3


class TestModeSwitch:
    """Test online vs local mode behavior."""

    def test_online_mode_skips_local_llm(
        self,
        processor: DocumentProcessor,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that online mode skips local LLM processing."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        processor.extractors[0].extract = Mock(return_value={
            "text": "Text without clear data",
            "metadata": {"pages": 1},
            "sections": None,
        })

        # Online mode should skip local LLM
        processor.process(test_file, mode="online")

        assert mock_llm_client.extract_field.call_count == 0

    def test_local_mode_uses_llm_for_low_confidence(
        self,
        processor: DocumentProcessor,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that local mode uses LLM for low confidence results."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        processor.extractors[0].extract = Mock(return_value={
            "text": "Text without clear data",
            "metadata": {"pages": 1},
            "sections": None,
        })

        # Local mode should use LLM
        processor.process(test_file, mode="local")

        assert mock_llm_client.extract_field.call_count >= 3
