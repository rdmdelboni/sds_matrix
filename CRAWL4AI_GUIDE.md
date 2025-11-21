# Crawl4AI Integration Guide - IP Ban Prevention

**Status**: ✅ **Crawl4AI installed and configured with IP ban prevention safeguards**

---

## Why Crawl4AI?

Crawl4AI extracts **richer content** from web pages compared to search engine snippets:

| Source | Content | Quality | Speed |
|--------|---------|---------|-------|
| SearXNG Snippets | Short excerpt (~200-500 chars) | Lower precision | Fast ⚡ |
| Crawl4AI Pages | Full page text (~5000 chars) | Higher precision | Slower |

### When to Use Crawl4AI

✅ **Enable Crawl4AI when**:
- Search snippets are insufficient (confidence < 400)
- You need detailed product information (specifications, ingredients, etc.)
- You're extracting from data-rich websites

❌ **Avoid Crawl4AI for**:
- High-volume bulk processing (would slow down significantly)
- Restricted crawling environments
- Sites that explicitly forbid automated access

---

## IP Ban Prevention: Safety Features

### 🛡️ Built-In Safeguards

All these protections are **enabled by default**:

| Feature | Default | Purpose |
|---------|---------|---------|
| **robots.txt Respect** | ✅ ON | Never crawl restricted paths |
| **User-Agent Rotation** | ✅ ON | Appear as different browsers |
| **Request Delays** | ✅ 2.0s | Respectful spacing between requests |
| **Sequential Crawling** | ✅ ON | Never hammer servers with parallel requests |
| **Timeouts** | 30s | Auto-kill hung requests |
| **Error Handling** | Graceful | Retry-safe failure modes |

### 📊 Rate Limiting Strategy

```
SearXNG Search:  1.0s minimum between requests  (fast)
                 ↓
Crawl4AI:        2.0s minimum between requests  (respectful)
```

The system is **sequential by default** (`MAX_CONCURRENT=1`), meaning:
- Only one page crawled at a time
- No risk of overwhelming target servers
- Natural, human-like access patterns

---

## Configuration

### Enable Crawl4AI

```bash
export CRAWL4AI_ENABLED=1
```

### Optional: Fine-Tune Safety Settings

```bash
# Minimum delay between crawl requests (default: 2.0s)
export CRAWL4AI_MIN_DELAY=2.0

# Max concurrent crawls (default: 1 - sequential)
export CRAWL4AI_MAX_CONCURRENT=1

# Browser type: chromium or firefox (default: chromium)
export CRAWL4AI_BROWSER_TYPE=chromium

# Respect robots.txt (default: 1 - YES, recommended)
export CRAWL4AI_RESPECT_ROBOTS=1

# Rotate user agents (default: 1 - YES, recommended)
export CRAWL4AI_USER_AGENT_ROTATION=1

# Optional proxy for requests (default: none)
# export CRAWL4AI_PROXY=http://proxy.example.com:8080

# Request timeout (default: 30s)
export CRAWL4AI_TIMEOUT=30
```

### Safe Defaults (Already Set)

```bash
CRAWL4AI_ENABLED=0                  # Disabled by default
CRAWL4AI_MIN_DELAY=2.0              # 2 second gap (respectful)
CRAWL4AI_MAX_CONCURRENT=1           # Sequential only
CRAWL4AI_RESPECT_ROBOTS=1           # Always respect robots.txt
CRAWL4AI_USER_AGENT_ROTATION=1      # Rotate user agents
CRAWL4AI_TIMEOUT=30                 # 30 second timeout
```

---

## Usage

### 1. Start with Crawl4AI Enabled

```bash
# Option A: Enable for this session
export CRAWL4AI_ENABLED=1
./iniciar.sh

# Option B: Edit .env file (if you have one)
echo "CRAWL4AI_ENABLED=1" >> .env
./iniciar.sh
```

### 2. How It Works During Extraction

When extracting a field:

```
1. Try LLM extraction (fast, always first)
   ↓
2. If confidence < 300, try web search (SearXNG)
   ↓
3. If confidence still < 400, and Crawl4AI enabled:
   → Fetch full page content using Crawl4AI
   → Search full text for field value
   → Extract with higher confidence
   ↓
4. Return best result with source tracking
```

### 3. Monitor Extraction

Check logs to see if crawling is being used:

```bash
# Watch logs in real-time
tail -f data/logs/app.log | grep -i crawl

# Look for these messages:
# ✅ "Crawl cache hit for [URL]"           (cached, no crawl)
# ✅ "Crawl4AI extracted [N] chars"        (successful crawl)
# ⚠️ "Crawl4AI failed for [URL]"          (crawl failed, continuing)
# ℹ️ "Crawl4AI not installed"              (gracefully skipped)
```

---

## Safety Best Practices

### ✅ DO

- ✅ **Keep default delays** (2.0s is respectful)
- ✅ **Keep sequential mode** (MAX_CONCURRENT=1)
- ✅ **Respect robots.txt** (enabled by default)
- ✅ **Rotate user agents** (enabled by default)
- ✅ **Limit crawl scope** (MAX_CRAWL_PAGES_PER_FIELD=2)
- ✅ **Use caching** (prevents redundant crawls)
- ✅ **Monitor logs** (watch for failures)

### ❌ DON'T

- ❌ **Never set MAX_CONCURRENT > 2** (too aggressive)
- ❌ **Never set MIN_DELAY < 1.0s** (too fast)
- ❌ **Never disable robots.txt** (disrespectful)
- ❌ **Never crawl the same site repeatedly** (caching prevents this)
- ❌ **Never crawl sites that forbid it** (robots.txt will catch most)
- ❌ **Never use without rate limiting** (dangerous)

---

## Troubleshooting

### Issue: IP Blocked by Website

**Symptoms**:
- Crawl returns empty or error responses
- Site returns 403/429 errors
- Requests timeout frequently

**Solutions**:
```bash
# 1. Increase delay between requests
export CRAWL4AI_MIN_DELAY=5.0  # More respectful

# 2. Disable crawling temporarily
export CRAWL4AI_ENABLED=0

# 3. Use a proxy if available
export CRAWL4AI_PROXY=http://your-proxy:8080

# 4. Disable user-agent rotation (some sites check this)
# export CRAWL4AI_USER_AGENT_ROTATION=0
```

### Issue: Crawl4AI Taking Too Long

**Symptoms**:
- System slower than expected
- Long pauses between field extractions

**Solutions**:
```bash
# 1. Reduce timeout (faster failures)
export CRAWL4AI_TIMEOUT=15  # Default 30s

# 2. Limit crawl pages per field
export MAX_CRAWL_PAGES_PER_FIELD=1  # Default 2

# 3. Disable crawling for fast processing
export CRAWL4AI_ENABLED=0
```

### Issue: Crawl Results Look Strange

**Symptoms**:
- Extracted text is malformed
- Missing important information
- Lots of ads/navigation text

**Solutions**:
```bash
# This is expected sometimes. Try:
# - Check if the website uses JavaScript (Crawl4AI renders it)
# - Look at logs for specific errors
# - Disable if results are worse than search snippets
```

---

## Caching Benefits

The system caches all crawled pages, so:

- 🔄 **First crawl**: Full content extraction (slow)
- ⚡ **Subsequent crawls**: Instant cache hit (fast)
- 💾 **Persistent**: Cached across app restarts
- 🗑️ **Auto-cleanup**: Old caches auto-deleted

### View Cache Status

```bash
# List cached crawls
sqlite3 data/duckdb/extractions.db \
  "SELECT url, LENGTH(content) as chars FROM crawl_cache LIMIT 5;"
```

---

## Monitoring & Metrics

### Check if Crawl4AI is Actually Being Used

```bash
# Count successful crawls
grep "Crawl4AI extracted" data/logs/app.log | wc -l

# Count cache hits
grep "Crawl cache hit" data/logs/app.log | wc -l

# Check extraction confidence improvement
# (High confidence = good crawl results)
```

### Performance Impact

Expected timing (with 2.0s delays):

- **Without Crawl4AI**: ~1-2s per field
- **With Crawl4AI**: ~3-5s per field (2s delay + 1-3s crawl)

For 10 fields: ~10-20 seconds total (manageable)

---

## Advanced Configuration

### Using a Proxy Service

For high-volume crawling or restricted networks:

```bash
# Residential proxy example (Bright Data, Oxylabs, etc.)
export CRAWL4AI_PROXY=http://user:pass@proxy.example.com:8080

# SOCKS proxy
export CRAWL4AI_PROXY=socks5://proxy.example.com:1080
```

### Custom Browser Settings

```bash
# Use Firefox instead of Chromium (sometimes bypasses blocks)
export CRAWL4AI_BROWSER_TYPE=firefox
```

---

## FAQ

**Q: Will I get my IP banned?**  
A: With default settings (2.0s delays, sequential, robots.txt respect), very unlikely. These are exactly the practices professional web scrapers use.

**Q: Can I crawl faster?**  
A: Not recommended. The current settings are already fast enough for most use cases.

**Q: Do I need a proxy?**  
A: No, unless you're crawling the same site heavily (100+ pages). For field extraction, caching + delays are sufficient.

**Q: What if a site blocks me?**  
A: Simply set `CRAWL4AI_ENABLED=0` and use search snippets instead.

**Q: How much does Crawl4AI cost?**  
A: Free! It's open-source. Only costs your time (2-3s delays).

**Q: Can I crawl JavaScript-heavy sites?**  
A: Yes, Crawl4AI uses Chromium under the hood, so it renders JavaScript automatically.

---

## Summary

| Aspect | Status |
|--------|--------|
| Crawl4AI Installed | ✅ |
| IP Ban Prevention | ✅ **Fully enabled** |
| Default Setting | ⊘ Disabled (for speed) |
| To Enable | `export CRAWL4AI_ENABLED=1` |
| Safety Level | ⭐⭐⭐⭐⭐ (very safe) |
| Performance Cost | +2-3s per field (when used) |
| Caching | ✅ Automatic (speeds up repeats) |

---

## Next Steps

1. **Try it with defaults**:
   ```bash
   export CRAWL4AI_ENABLED=1
   ./iniciar.sh
   ```

2. **Monitor logs** to see if crawling improves results

3. **Adjust if needed**:
   - Faster? Reduce `CRAWL4AI_MIN_DELAY` (but don't go below 1.0s)
   - Blocked? Increase delay or use proxy
   - Too slow? Disable or reduce `MAX_CRAWL_PAGES_PER_FIELD`

**Your IP is protected. Enjoy richer extractions!** 🚀

