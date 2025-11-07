# Testes do FDS Reader MVP

Esta pasta contém a suíte de testes automatizados do projeto.

## Estrutura

```
tests/
├── __init__.py              # Inicialização do pacote de testes
├── conftest.py              # Fixtures compartilhadas (pytest)
├── test_heuristics.py       # Testes das heurísticas de extração
├── test_validator.py        # Testes dos validadores Pydantic
└── test_document_processor.py  # Testes de integração do processamento
```

## Executando os testes

### Instalar dependências de teste

```bash
pip install pytest pytest-cov pytest-mock
```

Ou instalar todas as dependências:

```bash
pip install -r requirements.txt
```

### Executar todos os testes

```bash
pytest
```

### Executar com relatório de cobertura

```bash
pytest --cov=src --cov-report=html
```

O relatório HTML será gerado em `htmlcov/index.html`.

### Executar testes específicos

```bash
# Executar apenas testes de heurísticas
pytest tests/test_heuristics.py

# Executar apenas testes de validação
pytest tests/test_validator.py

# Executar apenas uma classe de testes
pytest tests/test_heuristics.py::TestNumeroONU

# Executar apenas um teste específico
pytest tests/test_heuristics.py::TestNumeroONU::test_extract_standard_format
```

### Executar com verbosidade aumentada

```bash
pytest -v
```

### Executar testes em modo watch (requer pytest-watch)

```bash
pip install pytest-watch
ptw
```

## Cobertura de testes

Os testes cobrem:

- ✅ **Heurísticas**: Extração de Número ONU, CAS e Classificação ONU
- ✅ **Validadores**: Validação de formatos e ranges usando Pydantic
- ✅ **Processamento**: Fluxo completo de processamento de documentos
- ✅ **Integração**: Interação entre componentes (mocked)

### Cobertura atual esperada

- `src/core/heuristics.py`: ~95%
- `src/core/validator.py`: ~95%
- `src/core/document_processor.py`: ~80%

## Adicionando novos testes

### Padrão de nomenclatura

- Arquivos: `test_<module>.py`
- Classes: `Test<Feature>`
- Métodos: `test_<comportamento_esperado>`

### Exemplo de teste

```python
def test_extract_numero_onu(extractor: HeuristicExtractor) -> None:
    """Test extraction of ONU number from FDS text."""
    text = "Número ONU: 1234"
    result = extractor._extract_numero_onu(text, None)
    
    assert result is not None
    assert result["value"] == "1234"
    assert result["confidence"] == 0.85
```

### Fixtures compartilhadas

Defina fixtures reutilizáveis em `conftest.py`:

```python
@pytest.fixture
def sample_fds_text() -> str:
    """Return sample FDS text for testing."""
    return "..."
```

## Integração Contínua (CI)

Para configurar CI/CD, adicione ao seu pipeline:

```yaml
# GitHub Actions exemplo
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=src --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Troubleshooting

### Erro: "Import pytest could not be resolved"

Instale pytest:
```bash
pip install pytest
```

### Erro: "No module named src"

Execute pytest da raiz do projeto:
```bash
cd d:\BI\fds_reader
pytest
```

### Testes lentos

Use marcadores para pular testes lentos:
```bash
pytest -m "not slow"
```
