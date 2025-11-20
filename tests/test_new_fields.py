"""Tests for new extraction fields (product name, manufacturer, packing group)."""

from __future__ import annotations

import pytest

from src.core.heuristics import HeuristicExtractor
from src.core.validator import Fabricante, GrupoEmbalagem, NomeProduto

@pytest.fixture
def extractor() -> HeuristicExtractor:
    """Create a fresh HeuristicExtractor instance for testing."""
    return HeuristicExtractor()

class TestNomeProduto:
    """Test suite for product name extraction."""

    def test_extract_product_name_standard(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of standard product name format."""
        text = "Produto: ETANOL 95% - ÁLCOOL ETÍLICO"
        result = extractor._extract_nome_produto(text, None)
        
        assert result is not None
        assert "ETANOL" in result["value"]
        assert result["confidence"] == 0.75

    def test_extract_from_section_1(self, extractor: HeuristicExtractor) -> None:
        """Test extraction from Section 1."""
        sections = {
            1: "Seção 1 - Identificação\nNome do Produto: ÁCIDO SULFÚRICO 98%"
        }
        result = extractor._extract_nome_produto("", sections)
        
        assert result is not None
        assert "ÁCIDO SULFÚRICO" in result["value"]

    def test_clean_parentheses(self, extractor: HeuristicExtractor) -> None:
        """Test that parentheses are removed from product name."""
        text = "Produto: METANOL (Álcool Metílico)"
        result = extractor._extract_nome_produto(text, None)
        
        assert result is not None
        assert "(" not in result["value"]

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no product name is found."""
        text = "Este texto não contém nome de produto."
        result = extractor._extract_nome_produto(text, None)
        
        assert result is None

class TestFabricante:
    """Test suite for manufacturer extraction."""

    def test_extract_manufacturer(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of manufacturer name."""
        text = "Fabricante: Acme Chemicals Ltda"
        result = extractor._extract_fabricante(text, None)

        assert result is not None
        assert "Acme Chemicals" in result["value"]
        assert result["confidence"] == 0.8  # "Fabricante" keyword triggers higher confidence

    def test_extract_supplier(self, extractor: HeuristicExtractor) -> None:
        """Test extraction using 'fornecedor' keyword."""
        text = "Fornecedor: Chemical Corp Brasil"
        result = extractor._extract_fabricante(text, None)
        
        assert result is not None
        assert "Chemical Corp" in result["value"]

    def test_extract_from_section_1(self, extractor: HeuristicExtractor) -> None:
        """Test extraction from Section 1."""
        sections = {
            1: "Identificação da Empresa\nEmpresa: XYZ Industrial S.A."
        }
        result = extractor._extract_fabricante("", sections)
        
        assert result is not None
        assert "XYZ Industrial" in result["value"]

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no manufacturer is found."""
        text = "Texto sem informação de fabricante."
        result = extractor._extract_fabricante(text, None)
        
        assert result is None

class TestGrupoEmbalagem:
    """Test suite for packing group extraction."""

    def test_extract_packing_group_roman(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of packing group in Roman numerals."""
        text = "Grupo de embalagem: II"
        result = extractor._extract_grupo_embalagem(text, None)
        
        assert result is not None
        assert result["value"] == "II"
        assert result["confidence"] == 0.80

    def test_extract_packing_group_arabic(self, extractor: HeuristicExtractor) -> None:
        """Test conversion from Arabic to Roman numerals."""
        text = "Grupo de embalagem: 2"
        result = extractor._extract_grupo_embalagem(text, None)
        
        assert result is not None
        assert result["value"] == "II"  # Converted to Roman

    def test_all_packing_groups(self, extractor: HeuristicExtractor) -> None:
        """Test all valid packing groups."""
        test_cases = [
            ("Grupo de embalagem I", "I"),
            ("Grupo de embalagem: II", "II"),
            ("Grupo de embalagem III", "III"),
        ]
        
        for text, expected in test_cases:
            result = extractor._extract_grupo_embalagem(text, None)
            assert result is not None
            assert result["value"] == expected

    def test_extract_from_section_14(self, extractor: HeuristicExtractor) -> None:
        """Test extraction from Section 14 (Transport Information)."""
        sections = {
            14: "Informações sobre Transporte\nGrupo de embalagem: I"
        }
        result = extractor._extract_grupo_embalagem("", sections)
        
        assert result is not None
        assert result["value"] == "I"

    def test_no_match(self, extractor: HeuristicExtractor) -> None:
        """Test when no packing group is found."""
        text = "Documento sem grupo de embalagem."
        result = extractor._extract_grupo_embalagem(text, None)
        
        assert result is None

class TestNomeProdutoValidator:
    """Test suite for product name validation."""

    def test_valid_product_name(self) -> None:
        """Test validation of valid product names."""
        result = NomeProduto(value="ETANOL 95%", confidence=0.9)
        assert result.value == "ETANOL 95%"

    def test_special_values(self) -> None:
        """Test that special values are allowed."""
        result = NomeProduto(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"

    def test_too_short(self) -> None:
        """Test validation rejects too-short names."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="muito curto"):
            NomeProduto(value="AB", confidence=0.9)

    def test_too_long(self) -> None:
        """Test validation rejects too-long names."""
        from pydantic import ValidationError
        long_name = "A" * 201
        with pytest.raises(ValidationError, match="muito longo"):
            NomeProduto(value=long_name, confidence=0.9)

class TestFabricanteValidator:
    """Test suite for manufacturer validation."""

    def test_valid_manufacturer(self) -> None:
        """Test validation of valid manufacturer names."""
        result = Fabricante(value="Acme Chemicals Ltd", confidence=0.8)
        assert result.value == "Acme Chemicals Ltd"

    def test_special_values(self) -> None:
        """Test that special values are allowed."""
        result = Fabricante(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"

    def test_too_short(self) -> None:
        """Test validation rejects too-short names."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="muito curto"):
            Fabricante(value="AB", confidence=0.9)

class TestGrupoEmbalagemValidator:
    """Test suite for packing group validation."""

    def test_valid_packing_groups(self) -> None:
        """Test all valid packing groups."""
        for group in ["I", "II", "III"]:
            result = GrupoEmbalagem(value=group, confidence=0.9)
            assert result.value == group

    def test_case_insensitive(self) -> None:
        """Test that validation is case-insensitive."""
        result = GrupoEmbalagem(value="ii", confidence=0.9)
        assert result.value == "II"

    def test_special_values(self) -> None:
        """Test that special values are allowed."""
        result = GrupoEmbalagem(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"

    def test_invalid_group(self) -> None:
        """Test validation rejects invalid groups."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="I, II ou III"):
            GrupoEmbalagem(value="IV", confidence=0.9)

class TestFullExtractionWithNewFields:
    """Integration tests for extraction with all fields including new ones."""

    def test_extract_all_fields_including_new(self, extractor: HeuristicExtractor) -> None:
        """Test extraction of all fields from complete FDS text."""
        text = """
        FICHA DE DADOS DE SEGURANÇA
        
        1. Identificação do Produto e da Empresa
        Produto: ETANOL 95% - ÁLCOOL ETÍLICO
        Fabricante: Acme Chemicals Ltda
        
        3. Composição e Informações sobre os Ingredientes
        CAS: 64-17-5
        Concentração: 95%
        
        14. Informações sobre Transporte
        Número ONU: 1170
        Classe de risco 3
        Grupo de embalagem: II
        """
        
        results = extractor.extract(text=text, sections=None)
        
        # Original fields
        assert "numero_onu" in results
        assert results["numero_onu"]["value"] == "1170"
        
        assert "numero_cas" in results
        assert results["numero_cas"]["value"] == "64-17-5"
        
        assert "classificacao_onu" in results
        assert results["classificacao_onu"]["value"] == "3"
        
        # New fields
        assert "nome_produto" in results
        assert "ETANOL" in results["nome_produto"]["value"]
        
        assert "fabricante" in results
        assert "Acme" in results["fabricante"]["value"]
        
        assert "grupo_embalagem" in results
        assert results["grupo_embalagem"]["value"] == "II"
