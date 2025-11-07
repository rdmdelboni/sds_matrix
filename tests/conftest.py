"""Configuration for pytest test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def examples_dir(project_root: Path) -> Path:
    """Return the examples directory with sample PDFs."""
    return project_root / "examples"


@pytest.fixture(scope="session")
def test_data_dir(project_root: Path) -> Path:
    """Return the test data directory."""
    test_dir = project_root / "tests" / "test_data"
    test_dir.mkdir(exist_ok=True)
    return test_dir


@pytest.fixture
def sample_fds_text() -> str:
    """Return a sample FDS text for testing."""
    return """
    FICHA DE DADOS DE SEGURANÇA
    
    1. IDENTIFICAÇÃO DO PRODUTO E DA EMPRESA
    Nome do produto: ETANOL 95%
    Fabricante: Acme Chemicals Ltd.
    
    3. COMPOSIÇÃO E INFORMAÇÕES SOBRE OS INGREDIENTES
    Substância: Etanol
    Número CAS: 64-17-5
    Concentração: 95% p/p
    
    14. INFORMAÇÕES SOBRE TRANSPORTE
    Número ONU: 1170
    Nome apropriado para embarque: ETANOL (ÁLCOOL ETÍLICO)
    Classe de risco: 3
    Grupo de embalagem: II
    Risco subsidiário: Não aplicável
    """


@pytest.fixture
def sample_fds_sections() -> dict[int, str]:
    """Return a sample FDS divided into sections."""
    return {
        1: "Produto: ÁCIDO SULFÚRICO 98%\nFabricante: Chemical Corp.",
        3: "Componente principal: Ácido Sulfúrico\nCAS: 7664-93-9\nConcentração: 98%",
        14: "Transporte:\nNúmero ONU: 1830\nClasse: 8\nGrupo de embalagem: I",
    }
