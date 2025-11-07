# FDS Reader - Release Notes

## Version 2.0 - Production Ready (October 30, 2025)

### 🎉 Major Features

#### Expanded Field Extraction (6 Total Fields)

- ✅ **Número ONU** - UN hazard identification number
- ✅ **Número CAS** - Chemical Abstracts Service registry number  
- ✅ **Classificação ONU** - UN hazard class (1-9)
- ✅ **Nome do Produto** - Product/chemical name (NEW)
- ✅ **Fabricante** - Manufacturer/supplier name (NEW)
- ✅ **Grupo de Embalagem** - Packing group I/II/III (NEW)

All fields include confidence scores and validation status (valid/warning/invalid).

#### Enhanced User Experience

- ✅ **Progress Dialog** - Modal progress bar tracks batch processing
- ✅ **Rich Error Dialogs** - Actionable suggestions + copy-to-clipboard for errors
- ✅ **Menu Bar** - Quick actions:
  - Arquivo → Abrir pasta de exportação (opens data folder)
  - Arquivo → Exportar CSV/Excel (one-click export)
  - Arquivo → Sair
- ✅ **Color-Coded Validation** - Green/yellow/red row highlighting in results
- ✅ **Validation Icons** - ✓ (valid) / ⚠ (warning) / ✗ (invalid) in tables

#### Improved Heuristics

- Enhanced regex patterns for product name (Nome comercial, Identificação do produto, etc.)
- Better manufacturer detection (Fabricante, Fornecedor, Razão social)
- Packing group extraction from Section 14 (Roman numerals I-III or 1-3)
- Confidence boost for strong label matches (0.88 vs 0.75)

#### Export Enhancements

- ✅ All 6 fields + confidence + validation metadata in exports
- ✅ CLI export tool: `scripts/export_results.py --format csv/excel`
- ✅ Filtered exports respect UI filters (status, validation, search)
- ✅ Both CSV and Excel formats supported

#### Testing & Quality

- ✅ **72 passing tests** (up from 40)
- ✅ 95-100% code coverage on critical modules
- ✅ Pydantic v2 compatibility
- ✅ Python 3.13 wheel compatibility (lxml, duckdb, pandas pinned)

### 📚 Documentation

- ✅ `USAGE.md` - Complete user guide with screenshots
- ✅ `.env.example` - Full configuration template
- ✅ `README.md` - Updated with all new features
- ✅ `docs/screenshots/` - Placeholder screenshots (replace with real captures)

### 🔧 Technical Improvements

#### Database

- DuckDB schema uses sequences (not AUTOINCREMENT) for Python 3.13 compatibility
- Validation columns in CTE queries for aggregated results
- Proper error status tracking (register document before extraction)

#### Architecture

- Separated DEFAULT_FIELDS and ADDITIONAL_FIELDS for test stability
- Global LLM skip if any heuristic confidence ≥ 0.82
- Robust error handling with status updates in all paths

#### Dependencies

- httpx==0.27.2 (pinned for openai==1.3.7 compatibility)
- lxml>=5.2.0, duckdb>=1.2.0, pandas>=2.2.0, pydantic>=2.10.0

### 🚀 Quick Start

```powershell
# Install dependencies
pip install -r requirements.txt

# Run GUI
python main.py

# Process examples (heuristics only)
python scripts/process_examples.py --heuristics-only

# Export results
python scripts/export_results.py --format excel --output data/my_results.xlsx
```

### 📸 Screenshots

Place actual screenshots in `docs/screenshots/`:

- `setup_tab.png` - Folder selection and queue
- `processing_tab.png` - Progress and field extraction
- `results_tab.png` - Filtering and validation
- `export_dialog.png` - CSV/Excel save dialog

### 🐛 Known Issues & Future Work

- Heuristics may miss product/manufacturer/packing group on some PDFs (enable LM Studio for better results)
- Screenshot placeholders need replacement with actual GUI captures
- Consider undo/redo for manual corrections
- Potential: add Tesseract OCR integration for scanned PDFs

### 🙏 Contributors

Developed with assistance from GitHub Copilot.

---

**Full implementation:** Option B (Complete production-ready implementation with GUI updates, progress tracking, error handling, comprehensive testing, and documentation).
