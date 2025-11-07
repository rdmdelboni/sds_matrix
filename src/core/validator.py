"""Validation schemas for extracted FDS fields."""

from __future__ import annotations

import re
from typing import ClassVar, Dict, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator


class ExtractionResult(BaseModel):
    """Base schema for a validated extraction."""

    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: str = ""


class NumeroONU(ExtractionResult):
    """Validate ONU number format and range."""

    @field_validator("value")
    @classmethod
    def check_un_number(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        value = value.strip().upper()
        if value.startswith("UN"):
            value = value[2:].strip()
        if not value.isdigit() or len(value) != 4:
            raise ValueError("Numero ONU deve conter 4 digitos.")
        number = int(value)
        if not (4 <= number <= 3506):
            raise ValueError("Numero ONU fora do intervalo valido.")
        return value


class NumeroCAS(ExtractionResult):
    """Validate CAS number formatting."""

    CAS_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^\d{2,7}-\d{2}-\d$")

    @field_validator("value")
    @classmethod
    def check_cas(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        value = value.strip()
        if not cls.CAS_PATTERN.match(value):
            raise ValueError("Numero CAS deve seguir o formato ####-##-#.")
        return value


class ClassificacaoONU(ExtractionResult):
    """Validate ONU class enumeration."""

    VALID_CLASSES: ClassVar[set[str]] = {
        "1",
        "1.1",
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "1.6",
        "2.1",
        "2.2",
        "2.3",
        "3",
        "4.1",
        "4.2",
        "4.3",
        "5.1",
        "5.2",
        "6.1",
        "6.2",
        "7",
        "8",
        "9",
    }

    @field_validator("value")
    @classmethod
    def check_class(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        # Extract numeric part
        match = re.search(r"\d(?:\.\d)?", value)
        if match:
            value = match.group(0)
        value = value.strip()
        if value not in cls.VALID_CLASSES:
            raise ValueError("Classe ONU invalida.")
        return value


class NomeProduto(ExtractionResult):
    """Validate product name."""

    @field_validator("value")
    @classmethod
    def check_product_name(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Nome do produto muito curto.")
        if len(value) > 200:
            raise ValueError("Nome do produto muito longo.")
        return value


class Fabricante(ExtractionResult):
    """Validate manufacturer name."""

    @field_validator("value")
    @classmethod
    def check_manufacturer(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Nome do fabricante muito curto.")
        if len(value) > 200:
            raise ValueError("Nome do fabricante muito longo.")
        return value


class GrupoEmbalagem(ExtractionResult):
    """Validate packing group."""

    VALID_GROUPS: ClassVar[set[str]] = {"I", "II", "III"}

    @field_validator("value")
    @classmethod
    def check_packing_group(cls, value: str) -> str:
        if value in {"NAO ENCONTRADO", "ERRO"}:
            return value
        value = value.strip().upper()
        if value not in cls.VALID_GROUPS:
            raise ValueError("Grupo de embalagem deve ser I, II ou III.")
        return value


VALIDATORS: Dict[str, type[ExtractionResult]] = {
    "numero_onu": NumeroONU,
    "numero_cas": NumeroCAS,
    "classificacao_onu": ClassificacaoONU,
    "nome_produto": NomeProduto,
    "fabricante": Fabricante,
    "grupo_embalagem": GrupoEmbalagem,
}


def validate_field(field_name: str, payload: Dict[str, object]) -> tuple[str, Optional[str]]:
    """Validate a field and return status plus optional message."""
    schema = VALIDATORS.get(field_name)
    if not schema:
        return "not_validated", None

    try:
        schema(**payload)
    except ValidationError as exc:
        return "invalid", str(exc.errors()[0]["msg"])

    if payload.get("confidence", 0) >= 0.9:
        return "valid", None
    if payload.get("confidence", 0) >= 0.7:
        return "warning", None
    return "invalid", "Confianca abaixo do limiar minimo (0.7)."
