# Todo 5: Source Citation & Validation - Implementation Summary

## Overview
Implemented comprehensive source citation and validation system to reduce LLM hallucination by requiring explicit source URLs and optionally validating their reachability.

## Changes Made

### 1. URL Validation Utility (`src/utils/url_validator.py`) - NEW FILE
Created a dedicated module for URL validation with three main functions:

- **`is_valid_url_format(url: str) -> bool`**: Validates URL format using regex pattern
- **`is_reachable_url(url: str, timeout: float | None) -> bool`**: Checks URL reachability via HEAD request
- **`validate_source_urls(source_urls: list[str] | None, strict: bool | None) -> tuple[bool, str]`**:
  - Non-strict mode: Only validates URL format
  - Strict mode: Requires at least one URL and verifies reachability
  - Returns tuple of (is_valid, error_message)

### 2. LLM Client Updates (`src/core/llm_client.py`)

#### System Prompt Enhancement
Updated `DEFAULT_SYSTEM_PROMPT` to require JSON response with `source_urls` field:
```python
DEFAULT_SYSTEM_PROMPT = (
    "Voce e um assistente especialista em Fichas de Dados de Seguranca."
    " Responda em JSON: {value, confidence (0-1.0), context, source_urls: [list of URLs]}."
    " SEMPRE inclua source_urls com URLs das fontes consultadas."
    " Se nao tiver fontes, use lista vazia []."
    " Nao invente dados."
)
```

#### Source URL Validation in `extract_field()`
Added validation logic after JSON parsing:
- Defaults `source_urls` to empty list if missing
- Validates source URLs when `STRICT_SOURCE_VALIDATION` is enabled
- If validation fails:
  - Downgrades confidence to max 0.6 (50% penalty)
  - Appends warning to context field
  - Logs validation failure

### 3. Validator Schema Updates (`src/core/validator.py`)

#### ExtractionResult Model
Added `source_urls` field to base validation schema:
```python
class ExtractionResult(BaseModel):
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: str = ""
    source_urls: list[str] = Field(default_factory=list)
```

All field-specific validators inherit this field automatically.

### 4. Database Schema Extension (`src/database/duckdb_manager.py`)

#### Extractions Table
Added `source_urls TEXT` column to store serialized JSON array:
```sql
CREATE TABLE IF NOT EXISTS extractions (
    id BIGINT PRIMARY KEY DEFAULT nextval('extractions_seq'),
    document_id INTEGER NOT NULL,
    field_name VARCHAR NOT NULL,
    value TEXT,
    confidence DOUBLE,
    context TEXT,
    source_urls TEXT,  -- NEW COLUMN
    validation_status VARCHAR,
    validation_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### store_extraction() Method
Updated signature to accept optional `source_urls` parameter:
```python
def store_extraction(
    self,
    document_id: int,
    field_name: str,
    value: str,
    confidence: float,
    context: str,
    validation_status: str,
    validation_message: str | None,
    source_urls: list[str] | None = None,  -- NEW PARAMETER
) -> None:
```

Serializes source_urls as JSON string before storage.

### 5. Document Processor Updates (`src/core/document_processor.py`)

Updated all 4 `store_extraction()` call sites to extract and pass `source_urls`:

1. **`_run_field_extractions()`**: Extracts source_urls from LLM response
2. **`_search_online_for_missing_fields()`**: Extracts source_urls from online search results
3. **`_try_onu_lookup()`**: Passes empty list (offline lookup has no web sources)
4. **`refine_fields()`**: Extracts source_urls from refinement response

All sites include type safety check:
```python
source_urls = result.get("source_urls", [])
if not isinstance(source_urls, list):
    source_urls = []
```

### 6. Field Retrieval Updates (`src/core/field_retrieval.py`)

Updated `retrieve_missing_fields()` to pass source URL from retrieval result:
```python
source_urls=[rr.source] if rr.source else []
```

Converts single source URL to list format for database storage.

## Configuration

### Strict Validation Mode
Controlled by environment variable (already existed in config):
```python
STRICT_SOURCE_VALIDATION: Final[bool] = os.getenv(
    "STRICT_SOURCE_VALIDATION", "1"
).lower() in ("1", "true", "yes")
```

- **Enabled (default)**: Requires at least one reachable URL, downgrades confidence if missing
- **Disabled**: Only validates URL format, allows empty source_urls

### Related Timeouts
```python
WEB_FETCH_TIMEOUT_SECONDS: Final[float] = 10.0
```

Used for URL reachability checks (HEAD requests).

## Benefits

1. **Hallucination Reduction**: LLM required to cite sources or face confidence penalty
2. **Provenance Tracking**: All extractions now have traceable source URLs
3. **Audit Trail**: Source URLs stored in database for future verification
4. **Quality Signal**: Low source quality correlates with confidence penalty
5. **Gradual Enforcement**: Configurable strict mode allows phased rollout

## Example Workflow

### With Valid Sources
1. LLM extracts field value from document/web
2. Returns JSON: `{"value": "3", "confidence": 0.9, "source_urls": ["https://pubchem.ncbi.nlm.nih.gov/..."]}`
3. URL format validated ✓
4. URL reachability checked ✓ (if strict mode)
5. Extraction stored with full confidence (0.9)

### With Invalid/Missing Sources
1. LLM returns: `{"value": "3", "confidence": 0.9, "source_urls": []}`
2. Strict validation fails (no URLs)
3. Confidence downgraded: 0.9 → 0.45 (50% penalty, max 0.6)
4. Context appended: "[AVISO: Fonte obrigatoria: nenhuma URL fornecida]"
5. Extraction stored with reduced confidence
6. Likely to be re-queried in refinement pass (confidence < 0.7)

## Testing Recommendations

1. **Format Validation**: Test with malformed URLs
2. **Reachability**: Test with unreachable URLs (404, timeout)
3. **Empty Lists**: Verify behavior with missing source_urls
4. **Confidence Penalty**: Confirm downgrade calculation (min(conf * 0.5, 0.6))
5. **Database Storage**: Verify JSON serialization/deserialization
6. **Strict Mode Toggle**: Test both enabled and disabled states

## Future Enhancements

- [ ] Add source URL quality scoring (domain reputation)
- [ ] Implement URL caching to avoid repeated HEAD requests
- [ ] Add source diversity metric (prefer multiple independent sources)
- [ ] Store HTTP status codes for debugging
- [ ] Add source URL display in UI/export

## Related Todos

- **Todo 4** (completed): Web crawling provides source URLs automatically
- **Todo 7** (pending): Caching layer could cache URL reachability checks
- **Todo 8** (pending): Evaluation metrics could assess source quality

## Status
✅ **COMPLETED** - All components implemented and integrated
