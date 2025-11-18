# ⚡ Quick Reference Card

## 🚀 Start Here

```bash
# Activate environment
source .venv/bin/activate

# Run app
./iniciar.sh

# Run tests
python test_tavily_integration.py
```

## 🔧 Configuration

### Get API Key
- **Tavily** (recommended): https://tavily.com
- **Grok**: https://console.x.ai
- **Gemini**: https://aistudio.google.com/app/apikey

### Set API Key
```bash
# Copy template
cp .env.local.example .env.local

# Edit with your key
nano .env.local
```

### Switch Provider
```bash
# Edit .env
ONLINE_SEARCH_PROVIDER=tavily  # or grok, gemini, lmstudio

# Restart app
./iniciar.sh
```

## 📊 Architecture at a Glance

```
PDF → 16 Workers → phi3:mini LLM → Missing fields?
                                      ↓
                              Online Search (Tavily/Grok/Gemini)
                                      ↓
                              DuckDB (thread-safe) → Results Tab
```

## 🎯 Providers

| Provider | Setup | Cost | Speed | Notes |
|----------|-------|------|-------|-------|
| **Tavily** | API key (free) | 100 searches/mo | 2-5s | ✅ Recommended |
| **Grok** | API key (free) | Unlimited | 3-7s | No quota limits |
| **Gemini** | API key (free) | Limited | 1-3s | Quota-limited |
| **LM Studio** | None | Free | 5-10s | Local fallback |

## 📁 Important Files

```
config:
  .env                    (provider setting)
  .env.local             (API keys - NEVER COMMIT)
  src/utils/config.py    (env loading)

clients:
  src/core/llm_client.py (4 client classes)

app:
  src/gui/main_app.py    (UI + provider selection)

database:
  src/database/duckdb_manager.py (THREAD-SAFE with lock)

tests:
  test_tavily_integration.py (6 tests, all passing)
```

## 🔒 Thread Safety

❌ **Wrong:**
```python
self.connection.execute(query)  # NOT SAFE
```

✅ **Correct:**
```python
with self._lock:
    self.connection.execute(query)  # SAFE for 16 workers
```

## 🧪 Run Tests

```bash
# Integration tests
python test_tavily_integration.py

# Expected: 6/6 PASS
```

## 📝 Common Edits

### Change Worker Count
```env
# .env
MAX_WORKERS=16  # or 8, 4, 2
```

### Change LLM Model
```env
# .env
LM_STUDIO_MODEL=phi3:mini  # or llama2, mistral, etc
```

### Change Search Provider
```env
# .env
ONLINE_SEARCH_PROVIDER=tavily  # tavily, grok, gemini, lmstudio
```

### Add New Field to Extract
1. Edit `src/core/document_processor.py`
2. Add to `ADDITIONAL_FIELDS` list
3. Update field translations in TavilyClient
4. Update database schema

## 🚨 Critical Notes

⚠️ **Thread Safety:** DuckDB uses `threading.Lock()` - essential for 16 workers
⚠️ **API Keys:** Never commit `.env` or `.env.local`
⚠️ **GUI Thread:** All UI updates must use `.after()` for main thread
⚠️ **Progress Bar:** Must call `show_progress()` before processing

## 🐛 Debug Commands

```bash
# Check provider
python -c "from src.utils.config import ONLINE_SEARCH_PROVIDER; print(ONLINE_SEARCH_PROVIDER)"

# Check config loaded
python -c "from src.utils.config import TAVILY_CONFIG; print('✅ Tavily API key' if TAVILY_CONFIG.get('api_key') else '❌ No key')"

# Check DB
python -c "from src.database.duckdb_manager import DuckDBManager; db = DuckDBManager(); print(db.db.execute('SELECT COUNT(*) FROM documents').fetchall())"

# View logs
tail -f data/logs/app.log
```

## 📊 Status Bar Messages

```
"LLM local conectado. | Tavily pronto para pesquisa online."  ✅
"LLM local conectado. | Grok pronto para pesquisa online."    ✅
"LLM local nao respondeu."                                     ❌
```

## 🔄 Processing Flow

```
start_processing()
    ↓
show_progress(total)
    ↓
enqueue files × total
    ↓
workers (parallel):
  extract_pdf()
    → llm_extract()
      → online_search() [if missing fields]
        → store_in_db() [THREAD-SAFE]
          → update_progress()
    ↓
all done?
    ↓
hide_progress()
→ show results_tab
```

## 🎨 GUI Layout

```
┌─────────────────────────────────┐
│ ⚙️ Configuração | ⚡ Processamento | 📊 Resultados │
├─────────────────────────────────┤
│ Folder selector                 │
│ LLM Status: "...pronto"         │
│ [████░░░░░] 45%    [⏹️ Cancel]  │  ← Progress bar
│ File list (scrollable)          │
│                                 │
├─────────────────────────────────┤
│ Status: Ready - Connections verified │
└─────────────────────────────────┘
```

## 📌 Recent Commits

```
0be84ca Add Copilot/Codex context guide
65ebc7b Add comprehensive session summary
a3c7603 Add Tavily AI search integration ← Latest major feature
```

## 🔗 Key Classes

```python
# Clients (all support same interface)
LMStudioClient()    → local LLM search
TavilyClient()      → online search
GrokClient()        → online search
GeminiClient()      → online search

# Database
DuckDBManager()     → stores all results (thread-safe)

# Processing
DocumentProcessor   → orchestrates extraction
ProcessingQueue     → manages 16 workers

# GUI
Application         → main window
SetupTab            → folder/progress
ProcessingTab       → status display
ResultsTab          → results table
```

## 💾 Data Model

```python
{
    "field_name": {
        "value": "extracted_value",
        "confidence": 0.0-1.0,  # 0.8=answer, 0.6=snippet, 0.0=not found
        "context": "source info"
    }
}
```

## 🆘 Common Issues

| Problem | Fix |
|---------|-----|
| App won't start | `pip install -r requirements.txt` |
| Progress bar hidden | `app.setup_tab.show_progress(total)` before processing |
| Workers hang | Check `LM_STUDIO_TIMEOUT` in .env |
| No API key error | Add to `.env.local`, not `.env` |
| Database locked | Restart app (only 1 writer allowed) |
| "Provider not found" | Set `ONLINE_SEARCH_PROVIDER=tavily` in .env |

## 📞 Where to Find Things

**"How do I..."**

| Question | File | Line |
|----------|------|------|
| Add a new search provider? | src/core/llm_client.py | 432 (TavilyClient example) |
| Change how progress shows? | src/gui/main_app.py | 1237 |
| Add a field to extract? | src/core/document_processor.py | DEFAULT_FIELDS |
| Fix thread issues? | src/database/duckdb_manager.py | 30 (Lock init) |
| See all config? | src/utils/config.py | 87-138 |
| Understand processing? | src/core/queue_manager.py | - |

---

**Status:** ✅ All systems ready
**Last Updated:** 2025-11-18
**Total Lines:** 7,000+ (production ready)
