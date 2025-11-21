# Quick Start: Crawl4AI for Richer Extraction

**Status**: ✅ Crawl4AI installed and ready  
**Safety**: ✅ IP ban prevention fully configured  
**Cost**: Free (open-source)

---

## TL;DR - Just Want to Try It?

```bash
# Enable Crawl4AI for this session
export CRAWL4AI_ENABLED=1

# Start the app
./iniciar.sh

# That's it! Richer page content extraction is now enabled
```

---

## What You're Getting

| Aspect | Before (Snippets) | After (Crawl4AI) |
|--------|-------------------|------------------|
| Content per field | ~200-500 chars | ~5000 chars |
| Extraction accuracy | Good | Better |
| Speed | 1-2s/field | 3-5s/field |
| Risk | None | Very low (IP protected) |

---

## Safety Guarantees

✅ **Always enabled by default**:
- Respects `robots.txt` (never crawls restricted areas)
- Rotates user-agents (looks like different browsers)
- 2-second delays between requests (respectful spacing)
- Sequential crawling (never hammer servers)
- Auto-caching (prevents redundant requests)

✅ **Your IP is protected**:
- Same practices as professional web scrapers
- Unlikely to trigger any bans
- If blocked, simply disable (`export CRAWL4AI_ENABLED=0`)

---

## Usage

### Basic Usage

```bash
export CRAWL4AI_ENABLED=1
./iniciar.sh
```

The system will automatically:
1. Use search snippets first (fast)
2. If confidence too low, try Crawl4AI (thorough)
3. Return best result with source tracking

### Check Results

```bash
# Watch extraction with crawling
tail -f data/logs/app.log | grep -i crawl

# Example log messages:
# ✅ Crawl cache hit for [URL]
# ✅ Crawl4AI extracted 4532 chars from [URL]
# ⚠️  Crawl4AI failed for [URL]: timeout
```

### Disable If Needed

```bash
export CRAWL4AI_ENABLED=0
./iniciar.sh

# Back to fast mode using only search snippets
```

---

## Performance

Expected timings (with default settings):

| Fields | With Crawl4AI | Without |
|--------|---------------|---------|
| 5 fields | ~15-25s | ~5-10s |
| 10 fields | ~30-50s | ~10-20s |
| 50 fields | ~2-4 min | ~1-2 min |

For most use cases, the extra accuracy is worth the 2-3s delay per field.

---

## Configuration Options

**For Advanced Users**:

```bash
# Minimum delay between crawls (default: 2.0s, min: 1.0s)
export CRAWL4AI_MIN_DELAY=2.0

# Max concurrent crawls (default: 1 for safety)
export CRAWL4AI_MAX_CONCURRENT=1

# Timeout per crawl (default: 30s)
export CRAWL4AI_TIMEOUT=30

# Always respect robots.txt (recommended: 1)
export CRAWL4AI_RESPECT_ROBOTS=1

# Rotate user agents (recommended: 1)
export CRAWL4AI_USER_AGENT_ROTATION=1
```

---

## Troubleshooting

### Getting blocked?
```bash
# Increase delay
export CRAWL4AI_MIN_DELAY=5.0
export CRAWL4AI_ENABLED=1
./iniciar.sh
```

### Too slow?
```bash
# Use faster search-only mode
export CRAWL4AI_ENABLED=0
./iniciar.sh
```

### Not working?
```bash
# Check if Crawl4AI is installed
python -c "import crawl4ai; print('✅ Crawl4AI installed')"

# Check config
python -c "from src.utils.config import CRAWL4AI_ENABLED; print(f'Crawl4AI enabled: {CRAWL4AI_ENABLED}')"
```

---

## See Also

- **Full Guide**: `CRAWL4AI_GUIDE.md` (comprehensive configuration, troubleshooting, best practices)
- **IP Ban Prevention**: `IP_BAN_PREVENTION.md` (detailed security practices)
- **Completion Summary**: `COMPLETION_SUMMARY.md` (all 10 features overview)

---

## Summary

|  |  |
|--|--|
| **Install** | ✅ Already done |
| **Enable** | `export CRAWL4AI_ENABLED=1` |
| **IP Safety** | ✅ Fully protected |
| **Performance** | +2-3s per field |
| **Accuracy** | Improved |
| **Result** | Richer extractions from web pages |

**Ready to try it?** Just set `CRAWL4AI_ENABLED=1` and run! 🚀

