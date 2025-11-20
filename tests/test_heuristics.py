"""Tests for heuristic extraction logic."""

from __future__ import annotations

import pytest

from src.core.heuristics import HeuristicExtractor

@pytest.fixture
def extractor() -> HeuristicExtractor:
    """Create a fresh HeuristicExtractor instance for testing."""
    return HeuristicExtractor()

class TestNumeroONU:
    """Test suite for ONU number extraction."""

    def test_extract_standard_format(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of standard UN#### format."""
        text = "O produto é classificado como UN1234 segundo normas."
        result = extractor._extract_numero_onu(text, None)
        
        assert result is not None
        assert result["value"] == "1234"
        assert result["confidence"] == 0.95
        assert "UN1234" in result["context"]

    def test_extract_onu_format(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of ONU:#### format."""
        text = "Número ONU: 2789 - Ácido acético glacial"
        result = extractor._extract_numero_onu(text, None)
        
        assert result is not None
        assert result["value"] == "2789"
        assert result["confidence"] == 0.95

    def test_extract_bare_number(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of bare 4-digit numbers."""
        text = "Transporte: 1203 conforme ADR"
        result = extractor._extract_numero_onu(text, None)
        
        assert result is not None
        assert result["value"] == "1203"

    def test_reject_out_of_range(self, extractor: HeuristicExtractor) -> None:
        """Test rejection of numbers outside valid ONU range."""
        text = "O código interno é 9999"
        result = extractor._extract_numero_onu(text, None)
        
        assert result is None

    def test_reject_too_small(self, extractor: HeuristicExtractor) -> None:
        """Test rejection of numbers below valid range."""
        text = "Código 0003 não é válido"
        result = extractor._extract_numero_onu(text, None)
        
        assert result is None

    def test_extract_from_sections(self, extractor: HeuristicExtractor) -> None:
        """Test extraction when sections are provided."""
        sections = {
            14: "Seção 14 - Transporte\nNúmero ONU: 1993\nClasse: 3"
        }
        result = extractor._extract_numero_onu("", sections)
        
        assert result is not None
        assert result["value"] == "1993"

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no ONU number is present."""
        text = "Este documento não contém número ONU válido."
        result = extractor._extract_numero_onu(text, None)
        
        assert result is None

class TestNumeroCAS:
    """Test suite for CAS number extraction."""

    def test_extract_standard_cas(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of standard CAS format."""
        text = "CAS: 64-19-7 (Ácido acético)"
        result = extractor._extract_numero_cas(text, None)
        
        assert result is not None
        assert result["value"] == "64-19-7"
        assert result["confidence"] == 0.8

    def test_extract_long_cas(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of longer CAS numbers."""
        text = "Número CAS 1234567-89-0"
        result = extractor._extract_numero_cas(text, None)
        
        assert result is not None
        assert result["value"] == "1234567-89-0"

    def test_extract_from_sections(self, extractor: HeuristicExtractor) -> None:
        """Test CAS extraction from structured sections."""
        sections = {
            3: "Seção 3 - Composição\nSubstância: Etanol\nCAS: 64-17-5\nConcentração: 95%"
        }
        result = extractor._extract_numero_cas("", sections)
        
        assert result is not None
        assert result["value"] == "64-17-5"

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no CAS number is present."""
        text = "Produto sem identificação CAS disponível."
        result = extractor._extract_numero_cas(text, None)
        
        assert result is None

class TestClassificacaoONU:
    """Test suite for UN classification extraction."""

    def test_extract_simple_class(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of simple class numbers."""
        text = "Classe de risco 3 - Líquidos inflamáveis"
        result = extractor._extract_classificacao(text, None)
        
        assert result is not None
        assert result["value"] == "3"
        assert result["confidence"] == 0.78

    def test_extract_subclass(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of subclasses."""
        text = "Classe 2.3 - Gases tóxicos"
        result = extractor._extract_classificacao(text, None)
        
        assert result is not None
        assert result["value"] == "2.3"

    def test_extract_case_insensitive(self, extractor: HeuristicExtractor) -> None:
        """Test case-insensitive extraction."""
        text = "CLASSE DE RISCO 6.1"
        result = extractor._extract_classificacao(text, None)
        
        assert result is not None
        assert result["value"] == "6.1"

    def test_extract_from_sections(self, extractor: HeuristicExtractor) -> None:
        """Test extraction from structured sections."""
        sections = {
            14: "Informações sobre transporte\nClasse 4.1 - Sólidos inflamáveis"
        }
        result = extractor._extract_classificacao("", sections)
        
        assert result is not None
        assert result["value"] == "4.1"

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no classification is found."""
        text = "Produto não classificado para transporte."
        result = extractor._extract_classificacao(text, None)
        
        assert result is None

class TestFullExtraction:
    """Integration tests for complete extraction flow."""

    def test_extract_all_fields(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of all fields from complete FDS text."""
        text = """
        FICHA DE DADOS DE SEGURANÇA
        
        1. Identificação
        Produto: Etanol 95%
        
        3. Composição
        CAS: 64-17-5
        Concentração: 95%
        
        14. Informações sobre transporte
        Número ONU: 1170
        Classe de risco 3
        Grupo de embalagem: II
        """
        
        results = extractor.extract(text=text, sections=None)
        
        assert "numero_onu" in results
        assert results["numero_onu"]["value"] == "1170"
        
        assert "numero_cas" in results
        assert results["numero_cas"]["value"] == "64-17-5"
        
        assert "classificacao_onu" in results
        assert results["classificacao_onu"]["value"] == "3"

    def test_extract_with_sections(self, extractor: HeuristicExtractor) -> None:
        """Test extraction with pre-parsed sections."""
        sections = {
            3: "Composição: Metanol, CAS 67-56-1",
            14: "Transporte: UN 1230, Classe 3"
        }
        
        results = extractor.extract(text="", sections=sections)
        
        assert len(results) == 3
        assert results["numero_onu"]["value"] == "1230"
        assert results["numero_cas"]["value"] == "67-56-1"
        assert results["classificacao_onu"]["value"] == "3"

    def test_partial_extraction(self, extractor: HeuristicExtractor) -> None:
        """Test extraction when only some fields are present."""
        text = "Produto com CAS: 7732-18-5 mas sem ONU"
        
        results = extractor.extract(text=text, sections=None)
        
        assert "numero_cas" in results
        assert results["numero_cas"]["value"] == "7732-18-5"
        assert "numero_onu" not in results
        assert "classificacao_onu" not in results

    def test_empty_text(self, extractor: HeuristicExtractor) -> None:
        """Test extraction from empty text."""
        results = extractor.extract(text="", sections=None)
        
        assert results == {}
