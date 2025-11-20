# 🔄 Online Search Reprocessing - Fixed!

## Problem

When adding already-processed documents to the queue for reprocessing:
- ❌ Online search was **not running** for documents with existing data
- ❌ Missing fields were **not being filled** even in "online" mode
- ❌ The system kept old field values instead of searching online

## Root Cause

The `DocumentProcessor` was reusing existing document IDs without clearing old extraction data. When the online search step ran, it would see fields with existing values/confidence and skip searching for them.

## ✅ Solution Implemented

### 1. **Clear Old Extractions Before Reprocessing**

Modified `src/core/document_processor.py`:

```python
def process(self, file_path: Path, *, mode: str = "online") -> None:
    # ... document registration ...
    
    # NEW: Clear old field extractions to allow fresh processing
    logger.info("Clearing previous extractions for document %s", document_id)
    self.db.clear_document_extractions(document_id)
    
    # Now reprocess from scratch...
```

### 2. **Added Database Method to Clear Extractions**

Added to `src/database/duckdb_manager.py`:

```python
def clear_document_extractions(self, document_id: int) -> None:
    """Delete all field extractions for a document to allow fresh processing."""
    logger.info("Clearing extractions for document %s", document_id)
    with self._lock:
        self.conn.execute(
            "DELETE FROM extractions WHERE document_id = ?",
            [document_id],
        )
```

## How It Works Now

### Processing Flow (Mode = "online")

```
1. Select file to process
   ↓
2. Register document (gets existing ID if already processed)
   ↓
3. ✨ **CLEAR old field extractions** ✨
   ↓
4. Extract text from document
   ↓
5. Run heuristics + LLM for all fields
   ↓
6. ✨ **Run online search for missing/low-confidence fields** ✨
   ↓
7. Store all results in database
```

### Reprocessing from Results Tab

```
1. Right-click processed document
   ↓
2. Select "Reprocessar seleção (online)"
   ↓
3. System calls processor.reprocess_online(doc_id)
   ↓
4. Online search runs immediately on existing data
   ↓
5. Updates fields with better results
```

## 🎯 What Gets Searched Online?

The online search step identifies missing fields by checking:

✅ **Will search for:**
- Fields with `confidence < 0.7`
- Fields with `value = "NAO ENCONTRADO"`
- Fields with `validation_status = "invalid"`
- Field `incompatibilidades` (always searched as extra field)

❌ **Will skip:**
- Fields with `confidence >= 0.7`
- Fields already marked as "valid"
- When mode is "local"
- When no online search client configured

## 📝 Usage Examples

### Example 1: Reprocess Single Document

```python
from src.core.document_processor import DocumentProcessor
from src.core.searxng_client import SearXNGClient
from src.database.duckdb_manager import DuckDBManager
from pathlib import Path

db = DuckDBManager()
searxng = SearXNGClient()
processor = DocumentProcessor(db_manager=db, online_search_client=searxng)

# Reprocess with online search
file_path = Path("data/documents/example.pdf")
processor.process(file_path, mode="online")
```

### Example 2: Reprocess from GUI

1. **Open Results Tab**
2. **Find document** with missing fields
3. **Right-click** → "Reprocessar seleção (online)"
4. **Wait** for online search to complete
5. **Refresh** to see updated fields

### Example 3: Queue Multiple Documents

1. **Open Setup Tab**
2. **Select files** (including previously processed)
3. **Set mode** to "online" for each file
4. **Click** "Iniciar Processamento"
5. System will:
   - Clear old data
   - Reprocess completely
   - Run online search for missing fields

## 🧪 Testing

Run the test script to verify the fix:

```bash
# Activate virtual environment
source venv/bin/activate

# Ensure SearXNG is running
./setup_searxng.sh

# Run test
python test_reprocess_online.py
```

**Expected output:**
```
Testing Document Reprocessing with Online Search
✅ SearXNG connected: http://localhost:8080
📄 Document: example.pdf
📊 Current field status:
   ⚠️  numero_onu: NAO ENCONTRADO (conf: 0.00)
   ⚠️  classificacao_onu: NAO ENCONTRADO (conf: 0.00)
🔄 Reprocessing document with online search...
✅ Reprocessing completed!
📊 Updated field status:
   ⬆️  numero_onu: 1170 (conf: 0.00 → 0.75)
   ⬆️  classificacao_onu: 3 (conf: 0.00 → 0.75)
✅ SUCCESS: 2 field(s) improved via online search!
```

## ⚠️ Important Notes

### 1. **SearXNG Must Be Running**

Before reprocessing with online mode:

```bash
# Check if running
docker ps | grep searxng

# If not running, start it
./setup_searxng.sh
```

### 2. **Virtual Environment Required**

Always activate venv before running:

```bash
source venv/bin/activate
```

### 3. **Rate Limiting Active**

Online search respects rate limits:
- ✅ Max 2 requests/second (default)
- ✅ Cache hits don't count toward limit
- ✅ Processing may take longer with many missing fields

### 4. **Cache Reduces Search Load**

Most reprocessing will hit cache:
- ✅ Same product+field = cached result
- ✅ 30-day TTL (default)
- ✅ Faster processing
- ✅ Fewer API calls

## 📊 Monitoring

### Check Processing Logs

```bash
# View real-time logs
tail -f data/logs/app.log | grep -E "Clearing|online search|SearXNG"

# Expected log messages:
# INFO - Clearing previous extractions for document 123
# INFO - Searching online for 3 missing fields: ['numero_onu', 'classificacao_onu', 'grupo_embalagem']
# INFO - SearXNG search: Ethanol CAS 64-17-5 UN number safety data sheet
# INFO - Updated numero_onu from online search: 1170 (confidence: 0.75)
```

### Check Database

```python
from src.database.duckdb_manager import DuckDBManager

db = DuckDBManager()

# Get document ID
doc_id = db.get_document_id(Path("data/documents/example.pdf"))

# Check field details
details = db.get_field_details(doc_id)
for field, data in details.items():
    print(f"{field}: {data['value']} (conf: {data['confidence']:.2f})")
```

## 🎉 Benefits of the Fix

✅ **Always Fresh Data**: Old extractions cleared before reprocessing  
✅ **Online Search Works**: Missing fields get searched even on reprocessing  
✅ **Queue Mode Respected**: "online" mode triggers web search  
✅ **Reprocess Button Works**: Right-click reprocess fills missing fields  
✅ **Cache Still Active**: Duplicate searches still use cache  

## 🔗 Related Documentation

- **IP Ban Prevention**: `IP_BAN_PREVENTION.md`
- **SearXNG Setup**: `SEARXNG_COMPLETE_GUIDE.md`
- **SearXNG Status**: `SEARXNG_WORKING.md`
- **Quick Reference**: `IP_BAN_QUICK_REFERENCE.md`

---

**The online search now works correctly for all documents, whether new or reprocessed! 🚀**
