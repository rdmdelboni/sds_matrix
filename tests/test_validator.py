"""Tests for field validation logic."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.validator import (
    ClassificacaoONU,
    NumeroCAS,
    NumeroONU,
    validate_field,
)


class TestNumeroONUValidator:
    """Test suite for ONU number validation."""

    def test_valid_onu_number(self) -> None:
        """Test validation of valid ONU numbers."""
        result = NumeroONU(value="1234", confidence=0.95)
        assert result.value == "1234"

    def test_valid_with_un_prefix(self) -> None:
        """Test validation strips UN prefix."""
        result = NumeroONU(value="UN1234", confidence=0.9)
        assert result.value == "1234"

    def test_valid_edge_cases(self) -> None:
        """Test validation at range boundaries."""
        # Minimum valid
        result = NumeroONU(value="0004", confidence=0.9)
        assert result.value == "0004"
        
        # Maximum valid
        result = NumeroONU(value="3506", confidence=0.9)
        assert result.value == "3506"

    def test_special_values(self) -> None:
        """Test that special values are allowed."""
        result = NumeroONU(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"
        
        result = NumeroONU(value="ERRO", confidence=0.0)
        assert result.value == "ERRO"

    def test_invalid_format(self) -> None:
        """Test validation rejects invalid formats."""
        with pytest.raises(ValidationError, match="4 digitos"):
            NumeroONU(value="123", confidence=0.9)
        
        with pytest.raises(ValidationError, match="4 digitos"):
            NumeroONU(value="12345", confidence=0.9)

    def test_invalid_range(self) -> None:
        """Test validation rejects out-of-range numbers."""
        with pytest.raises(ValidationError, match="intervalo valido"):
            NumeroONU(value="0003", confidence=0.9)
        
        with pytest.raises(ValidationError, match="intervalo valido"):
            NumeroONU(value="9999", confidence=0.9)

    def test_confidence_bounds(self) -> None:
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValidationError):
            NumeroONU(value="1234", confidence=-0.1)
        
        with pytest.raises(ValidationError):
            NumeroONU(value="1234", confidence=1.1)


class TestNumeroCASValidator:
    """Test suite for CAS number validation."""

    def test_valid_cas_formats(self) -> None:
        """Test various valid CAS formats."""
        # Standard 5-2-1 format
        result = NumeroCAS(value="64-19-7", confidence=0.9)
        assert result.value == "64-19-7"
        
        # Longer format
        result = NumeroCAS(value="1234567-89-0", confidence=0.9)
        assert result.value == "1234567-89-0"
        
        # Shorter format
        result = NumeroCAS(value="50-00-0", confidence=0.9)
        assert result.value == "50-00-0"

    def test_special_values(self) -> None:
        """Test that special values are allowed."""
        result = NumeroCAS(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"

    def test_invalid_format(self) -> None:
        """Test validation rejects invalid formats."""
        with pytest.raises(ValidationError, match="formato"):
            NumeroCAS(value="64197", confidence=0.9)
        
        with pytest.raises(ValidationError, match="formato"):
            NumeroCAS(value="64-1-7", confidence=0.9)
        
        with pytest.raises(ValidationError, match="formato"):
            NumeroCAS(value="64-19-77", confidence=0.9)


class TestClassificacaoONUValidator:
    """Test suite for UN classification validation."""

    def test_valid_classes(self) -> None:
        """Test all valid UN classes."""
        valid_classes = [
            "1", "1.1", "1.2", "1.3", "1.4", "1.5", "1.6",
            "2.1", "2.2", "2.3",
            "3",
            "4.1", "4.2", "4.3",
            "5.1", "5.2",
            "6.1", "6.2",
            "7", "8", "9"
        ]
        
        for class_value in valid_classes:
            result = ClassificacaoONU(value=class_value, confidence=0.9)
            assert result.value == class_value

    def test_extraction_from_text(self) -> None:
        """Test that numeric part is extracted from text."""
        result = ClassificacaoONU(value="Classe 3", confidence=0.85)
        assert result.value == "3"
        
        result = ClassificacaoONU(value="2.3 - Gases tóxicos", confidence=0.85)
        assert result.value == "2.3"

    def test_special_values(self) -> None:
        """Test special values are allowed."""
        result = ClassificacaoONU(value="NAO ENCONTRADO", confidence=0.0)
        assert result.value == "NAO ENCONTRADO"

    def test_invalid_class(self) -> None:
        """Test validation rejects invalid classes."""
        # Test text without any numeric part
        with pytest.raises(ValidationError, match="invalida"):
            ClassificacaoONU(value="ABC", confidence=0.9)
        
        # Test classe 0 which is invalid
        with pytest.raises(ValidationError, match="invalida"):
            ClassificacaoONU(value="Classe 0", confidence=0.9)


class TestValidateField:
    """Test suite for validate_field helper function."""

    def test_valid_field_high_confidence(self) -> None:
        """Test validation with high confidence."""
        payload = {"value": "1234", "confidence": 0.95}
        status, message = validate_field("numero_onu", payload)
        
        assert status == "valid"
        assert message is None

    def test_valid_field_medium_confidence(self) -> None:
        """Test validation with medium confidence."""
        payload = {"value": "1234", "confidence": 0.85}
        status, message = validate_field("numero_onu", payload)
        
        assert status == "warning"
        assert message is None

    def test_invalid_field_low_confidence(self) -> None:
        """Test validation with low confidence."""
        payload = {"value": "1234", "confidence": 0.5}
        status, message = validate_field("numero_onu", payload)
        
        assert status == "invalid"
        assert "limiar" in message.lower()

    def test_invalid_field_bad_format(self) -> None:
        """Test validation with invalid format."""
        payload = {"value": "123", "confidence": 0.95}
        status, message = validate_field("numero_onu", payload)
        
        assert status == "invalid"
        assert message is not None

    def test_unknown_field(self) -> None:
        """Test validation of unknown field types."""
        payload = {"value": "test", "confidence": 0.95}
        status, message = validate_field("unknown_field", payload)
        
        assert status == "not_validated"
        assert message is None

    def test_all_field_types(self) -> None:
        """Test validation works for all field types."""
        test_cases = [
            ("numero_onu", {"value": "1234", "confidence": 0.95}),
            ("numero_cas", {"value": "64-19-7", "confidence": 0.95}),
            ("classificacao_onu", {"value": "3", "confidence": 0.95}),
        ]
        
        for field_name, payload in test_cases:
            status, message = validate_field(field_name, payload)
            assert status == "valid"
            assert message is None
