# 🤖 Copilot/Codex Context Guide

**Quick reference for AI assistants working on this project.**

## 📋 Project Overview

**FDS-2-Matrix** - Extract chemical product data from PDF Safety Data Sheets (SDS)

- **Language:** Python 3.13+
- **GUI:** Tkinter (ttk)
- **Database:** DuckDB (local SQLite-like)
- **LLM:** phi3:mini (via Ollama/LM Studio)
- **Online Search:** Tavily/Grok/Gemini APIs

## 🎯 Current State (Session: 2025-11-18)

### Features Implemented ✅
1. Multi-threaded PDF processing (16 workers)
2. Local LLM extraction (phi3:mini)
3. Online search providers (Tavily, Grok, Gemini, LM Studio)
4. Integrated progress bar in GUI
5. Secure API key management (.env.local)
6. DuckDB with thread-safe locking
7. Results export (CSV, Excel)

### Recent Changes
- **Latest Commit:** `65ebc7b` - Add session summary
- **Previous:** `a3c7603` - Tavily integration
- **Before:** Progress bar integration, API key management, thread safety

## 📂 Critical Files

### Core Logic
```
src/
├── core/
│   ├── llm_client.py           # 4 clients: LMStudio, Tavily, Grok, Gemini
│   ├── document_processor.py   # PDF extraction pipeline
│   ├── chunk_strategy.py       # Text chunking logic
│   └── queue_manager.py        # Async job queue (16 workers)
├── database/
│   └── duckdb_manager.py       # THREAD-SAFE: Uses threading.Lock()
├── gui/
│   └── main_app.py             # Tkinter app, provider selection
└── utils/
    ├── config.py               # ENV loading + provider detection
    └── logger.py               # Structured logging
```

### Configuration
```
.env                    # Shared (committed): Provider choice, LM Studio settings
.env.local             # Private (git-ignored): API keys
.env.local.example     # Template for users
```

### Documentation
```
SESSION_SUMMARY.md     # ← Read this first (418 lines)
TAVILY_SETUP.md        # Tavily-specific setup (331 lines)
GEMINI_SETUP.md        # Gemini setup (original)
INTEGRATED_PROGRESS_BAR.md
```

## 🔑 Key Concepts

### 1. Provider System
```python
# Automatic detection in config.py
ONLINE_SEARCH_PROVIDER = detect_provider():
    # Try in order:
    if TAVILY_API_KEY: return "tavily"
    elif GROK_API_KEY: return "grok"
    elif GOOGLE_API_KEY: return "gemini"
    else: return "lmstudio"
```

### 2. Thread Safety
```python
# In DuckDBManager.__init__()
self._lock = threading.Lock()

# All DB operations wrapped:
with self._lock:
    self.connection.execute(...)  # SAFE for 16 parallel workers
```

### 3. Client Interface
```python
class AnyClient:
    def test_connection(self) -> bool:
        """Check if API configured"""

    def search_online_for_missing_fields(
        product_name: str | None,
        cas_number: str | None,
        un_number: str | None,
        missing_fields: list[str]
    ) -> Dict[str, Dict[str, object]]:
        # Returns: {"field": {"value": "...", "confidence": 0.0-1.0, "context": "..."}}
```

### 4. Processing Flow
```
User selects PDFs
    ↓
start_processing()
    ├─ Show progress bar
    └─ Enqueue files (ProcessingQueue)
        ↓
        16 workers (parallel):
        ├─ Extract text from PDF
        ├─ Local LLM extraction (phi3:mini)
        ├─ If missing fields → Online search (Tavily/Grok/etc)
        ├─ Merge results + confidence scores
        └─ Store in DuckDB (THREAD-SAFE)
            ↓
        Status updates → UI progress bar
            ↓
Hide progress bar
    ↓
Show results in "Resultados" tab
```

## 🔧 Common Tasks

### Add New Online Search Provider
```python
# 1. Create client class in src/core/llm_client.py
class MyClient:
    def __init__(self):
        self.api_key = str(MY_CONFIG.get("api_key", ""))

    def test_connection(self) -> bool:
        return bool(self.api_key)

    def search_online_for_missing_fields(...):
        # Implement search logic
        return results

# 2. Add config in src/utils/config.py
MY_CONFIG = {
    "api_key": os.getenv("MY_API_KEY", ""),
    ...
}

# 3. Update ONLINE_SEARCH_PROVIDER priority
ONLINE_SEARCH_PROVIDER = os.getenv(
    "ONLINE_SEARCH_PROVIDER",
    "my_provider" if os.getenv("MY_API_KEY") else ...
)

# 4. Update Application in src/gui/main_app.py
elif provider == "my_provider":
    self.online_search_client = MyClient()

# 5. Update status check
elif provider_name == "my_provider":
    status += " | MyProvider ready"
```

### Change Processing Configuration
```python
# In .env:
MAX_WORKERS=16              # Parallel workers
CHUNK_SIZE=2000             # Text chunk size
LM_STUDIO_MODEL=phi3:mini   # LLM model
LM_STUDIO_TEMPERATURE=0.0   # Extraction precision
```

### Debug Issues
```bash
# Check configuration
python -c "from src.utils.config import *; print(f'Provider: {ONLINE_SEARCH_PROVIDER}')"

# Run tests
python test_tavily_integration.py

# Check logs
tail -f data/logs/app.log

# Verify database
python -c "from src.database.duckdb_manager import DuckDBManager; db = DuckDBManager(); print(db.db.execute('SELECT COUNT(*) FROM documents').fetchall())"
```

### Add New Field to Extract
1. Add to `ADDITIONAL_FIELDS` in `src/core/document_processor.py`
2. Update field_translations in TavilyClient (for online search)
3. Add to database schema in DuckDBManager
4. Update UI in ResultsTab

## 🚨 Important Notes

### ⚠️ Thread Safety CRITICAL
- **NEVER** access DuckDB outside `with self._lock:` block
- All database operations in `duckdb_manager.py` are protected
- 16 workers depend on this

### ⚠️ API Keys CRITICAL
- Never commit `.env` or `.env.local`
- Always use `.env.local` for user's keys
- .gitignore already has protection

### ⚠️ GUI Thread Safety
- All UI updates must happen on main thread
- Use `queue.Queue` for worker → UI communication
- Progress bar updates use `self.after()` for main thread

## 🧪 Running Tests

```bash
# Tavily integration tests
source .venv/bin/activate
python test_tavily_integration.py

# Expected output:
# ✅ Imports
# ✅ Configuration
# ✅ Client Instantiation
# ✅ Tavily Connection
# ✅ Provider Selection
# ✅ Application Initialization
```

## 📊 Code Statistics

```
Total: ~7,000 lines of code

Core processing:
├── llm_client.py: 560 lines (4 clients)
├── document_processor.py: ~500 lines
├── queue_manager.py: ~200 lines
├── duckdb_manager.py: ~300 lines

GUI:
├── main_app.py: ~1,500 lines (3 tabs)
├── Styles: ~100 lines

Config/Utils:
├── config.py: ~145 lines
├── logger.py: ~50 lines
├── file_utils.py: ~100 lines
```

## 🔗 Key Dependencies

```
Python: 3.13+
├── tkinter           # GUI (built-in)
├── duckdb            # Database
├── openai (SDK)      # LM Studio client
├── httpx             # HTTP requests (Tavily, Grok, Gemini)
├── python-dotenv     # .env loading
└── pytesseract       # OCR for scanned PDFs

External Services:
├── Ollama/LM Studio  # Local LLM (phi3:mini)
├── Tavily API        # Online search (recommended)
├── Grok API          # Alternative search
└── Gemini API        # Alternative search
```

## 💾 Database Schema

```sql
documents (id, file_path, status, created_at, updated_at)
extractions (id, document_id, field_name, value, confidence, source, created_at)
field_details (id, document_id, field_name, value, confidence, context, created_at)
```

## 🎨 UI Structure

```
Application (Tkinter)
├── Notebook (3 tabs)
│   ├── ⚙️ Configuração (SetupTab)
│   │   ├── Folder selector
│   │   ├── LLM Status bar
│   │   ├── Progress bar (integrated)
│   │   └── File list
│   ├── ⚡ Processamento (ProcessingTab)
│   │   ├── Processing status grid
│   │   ├── Field details
│   │   └── Real-time updates
│   └── 📊 Resultados (ResultsTab)
│       ├── Results table
│       ├── Filters
│       └── Export buttons
└── Status bar (bottom)
    └── Current status + version
```

## 🚀 Quick Start Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
./iniciar.sh

# Test
python test_tavily_integration.py

# Configure
cp .env.local.example .env.local
nano .env.local  # Add API key
```

## 📌 Git Commits This Session

```
65ebc7b Add comprehensive session summary for reference
a3c7603 Add Tavily AI search integration for online field lookup
f9adfc9 Add progress bar demonstration script
2d8909f Fix progress bar visibility and layout issues
b34a12e Move progress bar from external dialog to integrated interface
4ff5fab Add secure API key configuration with .env.local support
```

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| "Bus error (core dumped)" | Update DuckDBManager with threading.Lock() (already fixed) |
| Progress bar not showing | Ensure SetupTab.show_progress() called before processing |
| API key not loading | Check .env.local exists and readable (not git-ignored) |
| "Provider not found" | Set ONLINE_SEARCH_PROVIDER in .env |
| 16 workers timeout | Increase LM_STUDIO_TIMEOUT in .env |
| DuckDB locked | Restart app (only one instance can write) |

## 📞 Quick Reference

**Files to modify when:**
- Adding feature → `src/core/` or `src/gui/`
- Changing config → `src/utils/config.py` and `.env`
- Adding provider → `src/core/llm_client.py`, `src/gui/main_app.py`
- Bug fix → Fix + add test to `test_*.py`
- Documentation → Update `SESSION_SUMMARY.md` and `.md` files

**Always:**
1. Run tests before committing
2. Update SESSION_SUMMARY.md with major changes
3. Check thread safety with DuckDB
4. Never commit .env or .env.local
5. Use git commit messages with [Claude Code] signature

---

**Last Updated:** 2025-11-18
**For:** Claude Code, GitHub Copilot, other AI assistants
**Status:** Ready for continuation ✅
