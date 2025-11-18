# 🔍 Tavily AI Search Setup Guide

## Overview

Tavily is an AI research API specifically designed for helping AI agents find reliable information on the internet. Your application now uses Tavily as the **recommended provider** for online search, combined with your local LLM (phi3:mini) for processing the results.

## Why Tavily?

**Advantages:**
- ✅ **Free tier:** 100 searches/month (perfect for testing)
- ✅ **No usage limits** beyond the monthly quota
- ✅ **Science-focused:** Optimized for technical and scientific queries
- ✅ **Open source compatible:** Works well with local LLMs
- ✅ **Better results:** Specifically designed for AI agents searching for reliable information

**Comparison with other providers:**
| Provider | Free Tier | Quota Limit | Recommended |
|----------|-----------|-------------|------------|
| Tavily | 100/month | Yes | ✅ **YES** |
| Grok | Unlimited | No | Alternative |
| Gemini | Limited | Yes | Limited use |
| LM Studio | Unlimited | No | Local only |

## Setup Instructions

### 1. Create Tavily Account

1. Go to [Tavily.com](https://tavily.com)
2. Sign up for a free account
3. Navigate to your API dashboard
4. Copy your API key

### 2. Configure .env.local

```bash
# Copy the example file
cp .env.local.example .env.local

# Edit .env.local and add your Tavily API key
nano .env.local
```

**Add to `.`.env.local`:**
```env
TAVILY_API_KEY=your_tavily_api_key_here

# Optional overrides (use defaults if not needed):
# TAVILY_BASE_URL=https://api.tavily.com
# TAVILY_TIMEOUT=60
```

### 3. Verify Configuration

```bash
source .venv/bin/activate

# Test if Tavily is configured
python -c "
from src.utils.config import TAVILY_CONFIG, ONLINE_SEARCH_PROVIDER
if TAVILY_CONFIG.get('api_key'):
    print('✅ Tavily API Key loaded successfully!')
    print(f'Provider: {ONLINE_SEARCH_PROVIDER}')
else:
    print('❌ Tavily API Key not found - check .env.local')
"
```

### 4. Run Application

```bash
./iniciar.sh
```

The status bar should show: **"LLM local conectado. | Tavily pronto para pesquisa online."**

## How It Works

### Search Flow

```
PDF File
   ↓
Local LLM (phi3:mini)
   ↓ Extracts initial data
Missing fields?
   ↓ YES
Tavily Search
   ↓ Performs web search
Parse Results
   ↓
Merge with extracted data
   ↓
Database Storage
```

### For Each Missing Field

1. **Build Search Query:**
   - Product identifier (name, CAS#, UN#)
   - Field name translation (e.g., "CAS number", "UN classification")
   - Context: "chemical product safety data"

2. **Tavily Search:**
   - Topic: "science" (filters for technical content)
   - Search depth: "advanced" (better results)
   - Max results: 5 (balanced speed/accuracy)

3. **Extract Answer:**
   - Prefer Tavily's generated answer (if available)
   - Fallback to first search result content
   - Mark with confidence score (0.8 for answer, 0.6 for snippet)

4. **Store Result:**
   - Save in database with source attribution
   - Track confidence level
   - Mark as "Tavily online search"

## Features

### Automatic Field Search

The application automatically searches for these fields if missing from PDF:
- **numero_cas** → CAS number
- **numero_onu** → UN number
- **nome_produto** → Product name
- **fabricante** → Manufacturer
- **classificacao_onu** → UN hazard classification
- **grupo_embalagem** → Packing group
- **incompatibilidades** → Chemical incompatibilities

### Confidence Scoring

```
Generated Answer:  confidence = 0.8
Search Result:     confidence = 0.6
Not Found:         confidence = 0.0
```

## Usage Example

### Manual Test

```python
from src.core.llm_client import TavilyClient

client = TavilyClient()

# Test connection
if client.test_connection():
    print("✅ Tavily is configured")

    # Search for missing fields
    results = client.search_online_for_missing_fields(
        product_name="Acetone",
        cas_number="67-64-1",
        missing_fields=["numero_onu", "classificacao_onu"]
    )

    for field, data in results.items():
        print(f"{field}: {data['value']} (confidence: {data['confidence']})")
```

### Automatic Processing

When you process PDFs through the GUI:
1. Select folder with PDFs
2. Click "Adicionar à fila"
3. Watch progress bar
4. Missing fields are automatically filled from Tavily
5. Results appear in "Resultados" tab

## Free Tier Limits

**100 searches per month** translates to:
- ~3 searches per day
- ~15 searches per week
- Enough for reasonable testing and batch processing

**To optimize usage:**
1. Only search for truly missing fields
2. Batch process files (more efficient)
3. Cache results in database
4. Use confidence scores to avoid redundant searches

## Cost Considerations

- **Free tier:** 100 searches/month (completely free)
- **Paid tier:** Per-request billing (if you exceed free tier)
- Monitor usage: Visit [tavily.com/dashboard](https://tavily.com/dashboard)

## Switching Providers

If you want to use a different provider:

```bash
# Edit .env.local and uncomment the provider you want
# Then set ONLINE_SEARCH_PROVIDER in .env

# Option 1: Tavily (recommended)
TAVILY_API_KEY=your_key
ONLINE_SEARCH_PROVIDER=tavily

# Option 2: Grok (unlimited)
# GROK_API_KEY=your_key
# ONLINE_SEARCH_PROVIDER=grok

# Option 3: Gemini
# GOOGLE_API_KEY=your_key
# ONLINE_SEARCH_PROVIDER=gemini

# Option 4: Local LLM only (no external API)
# ONLINE_SEARCH_PROVIDER=lmstudio
```

The application will automatically detect which provider to use based on available API keys.

## Troubleshooting

### "Tavily not configured" message

**Solution:**
```bash
# Verify .env.local exists and has correct key
ls -l .env.local
grep TAVILY_API_KEY .env.local

# Reload environment
source .venv/bin/activate
```

### Search returns no results

**Possible causes:**
- Product name is too vague (try with CAS number)
- Field is not available online
- Tavily API quota exhausted

**Solution:**
- Try more specific identifiers
- Check Tavily dashboard for usage stats
- Wait for monthly quota reset (if exhausted)

### Confidence scores are low

This is normal for web search results. The LLM model in use (phi3:mini) has limitations but:
- Confidence 0.8: High reliability (Tavily's generated answer)
- Confidence 0.6: Moderate reliability (search snippet)
- Confidence 0.0: Not found or error

Always verify critical safety data from official sources!

### Slow search performance

Tavily's "advanced" search is thorough but slower. To speed up:

1. Edit `src/core/llm_client.py` line 454:
```python
"search_depth": "basic",  # Changed from "advanced"
```

2. Also reduce max_results:
```python
"max_results": 3,  # Changed from 5
```

**Trade-off:** Faster but potentially less accurate results.

## Privacy & Security

- ✅ API key stored locally only (.env.local is git-ignored)
- ✅ No data sent to GitHub
- ✅ Tavily searches are encrypted (HTTPS)
- ✅ Results stored in local DuckDB database
- ✅ Never share your API key in public repositories

## API Reference

### TavilyClient Class

```python
class TavilyClient:
    def test_connection(self) -> bool:
        """Verify API key is configured."""

    def search_online_for_missing_fields(
        product_name: Optional[str],
        cas_number: Optional[str],
        un_number: Optional[str],
        missing_fields: list[str]
    ) -> Dict[str, Dict[str, object]]:
        """Search for missing chemical product fields."""
```

**Returns:**
```python
{
    "field_name": {
        "value": "extracted_value",
        "confidence": 0.0-1.0,
        "context": "source_info"
    }
}
```

## Performance Metrics

Based on typical usage:
- **Per search:** ~2-5 seconds
- **100 searches/month:** Comfortable testing pace
- **Fallback:** Falls back to LLM extraction if Tavily fails

## Next Steps

1. ✅ Get Tavily API key from [tavily.com](https://tavily.com)
2. ✅ Add to `.env.local`
3. ✅ Restart application
4. ✅ Verify "Tavily pronto" appears in status bar
5. ✅ Process a PDF with missing fields

## Support

- **Tavily Docs:** https://docs.tavily.com
- **GitHub Issues:** Report bugs or feature requests
- **Community:** Tavily Discord for additional help

---

**Version:** 1.0
**Date:** 18 de Novembro de 2025
**Status:** ✅ Production Ready
**Recommended:** Yes - Best balance of free tier, accuracy, and ease of use
