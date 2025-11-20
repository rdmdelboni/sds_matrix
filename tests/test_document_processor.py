"""Integration tests for document processing flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock

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

class TestDocumentProcessorFlow:
    """Test the complete document processing flow."""

    def test_high_confidence_heuristics_skip_llm(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that high confidence heuristics skip LLM calls."""
        # Create a mock PDF file
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        # Mock the extractor to return high confidence results
        processor.extractors[0].extract = Mock(return_value={
            "text": "Número ONU: 1234",
            "metadata": {"pages": 1},
            "sections": None,
        })
        
        # Process should skip LLM for high confidence
        processor.process(test_file)
        
        # Verify LLM was NOT called (heuristic confidence >= 0.82)
        assert mock_llm_client.extract_field.call_count == 0
        
        # Verify database operations
        assert mock_db_manager.register_document.called
        assert mock_db_manager.store_extraction.call_count == 3  # 3 fields
        assert mock_db_manager.update_document_status.called

    def test_low_confidence_uses_llm(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        mock_llm_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that low confidence heuristics trigger LLM calls."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        # Mock extractor with text that has low confidence matches
        processor.extractors[0].extract = Mock(return_value={
            "text": "Algum texto sem dados claros",
            "metadata": {"pages": 1},
            "sections": None,
        })

        # Must use mode="local" to enable LLM fallback (mode="online" skips local LLM)
        processor.process(test_file, mode="local")

        # LLM should be called for all fields (3 fields * 1 chunk)
        assert mock_llm_client.extract_field.call_count >= 3

    def test_file_size_validation(self, processor: DocumentProcessor, tmp_path: Path) -> None:
        """Test that oversized files are rejected."""
        # Create a file that exceeds MAX_FILE_SIZE_MB
        large_file = tmp_path / "large.pdf"
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11MB
        
        with pytest.raises(ValueError, match="excede o limite"):
            processor.process(large_file)

    def test_error_handling_and_status_update(
        self,
        processor: DocumentProcessor,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that errors are caught and status is updated."""
        test_file = tmp_path / "error.pdf"
        test_file.write_text("dummy")
        
        # Force an error in extraction
        processor.extractors[0].extract = Mock(side_effect=Exception("Extraction failed"))
        
        with pytest.raises(Exception, match="Extraction failed"):
            processor.process(test_file)
        
        # Verify error was logged in database
        status_call = mock_db_manager.update_document_status.call_args
        assert status_call is not None
        assert status_call[1]["status"] == "failed"
        assert "Extraction failed" in status_call[1]["error_message"]

class TestHeuristicConfidenceThreshold:
    """Test the heuristic confidence skip threshold."""

    def test_default_threshold(self, mock_db_manager: MagicMock) -> None:
        """Test default threshold is 0.82."""
        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=None,
        )
        assert processor.heuristic_confidence_skip == 0.82

    def test_custom_threshold(self, mock_db_manager: MagicMock) -> None:
        """Test custom threshold can be set."""
        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=None,
            heuristic_confidence_skip=0.9,
        )
        assert processor.heuristic_confidence_skip == 0.9

    def test_no_llm_client_uses_heuristics_only(
        self,
        mock_db_manager: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that without LLM client, only heuristics are used."""
        processor = DocumentProcessor(
            db_manager=mock_db_manager,
            llm_client=None,  # No LLM
        )
        
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")
        
        processor.extractors[0].extract = Mock(return_value={
            "text": "Número ONU: 1234",
            "metadata": {"pages": 1},
            "sections": None,
        })
        
        processor.process(test_file)
        
        # Should work without LLM
        assert mock_db_manager.register_document.called
        assert mock_db_manager.store_extraction.called
