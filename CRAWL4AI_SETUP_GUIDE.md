# Crawl4AI Setup & IP Ban Prevention Guide

**Date**: November 20, 2025  
**Status**: ✅ **Crawl4AI Fully Configured with IP Ban Prevention**

---

## Quick Start

### 1. Enable Crawl4AI
```bash
export CRAWL4AI_ENABLED=1
```

### 2. Verify Installation
```bash
python -c "from crawl4ai import AsyncWebCrawler; print('✅ Crawl4AI is installed and ready')"
```

### 3. Start Your Application
```bash
./iniciar.sh
```

That's it! The system will now extract richer content from web pages when search snippets are insufficient.

---

## What Crawl4AI Does

When enabled (`CRAWL4AI_ENABLED=1`):

```
Missing Field Query
        ↓
SearXNG Search Results
        ↓
Extract from snippets (confidence check)
        ↓
    If confidence < 400:
        ↓
    Crawl full page with Crawl4AI
        ↓
    Extract from full text (richer context)
        ↓
    Higher confidence extraction
```

**Result**: Better accuracy for fields that aren't visible in search snippets.

---

## IP Ban Prevention: Built-In Safeguards

### ✅ Enabled by Default (Safe Crawling)

Your system includes multiple layers of IP ban prevention:

#### 1. **Rate Limiting with Token Bucket**
```python
# Enforced minimum delay between requests
SEARXNG_MIN_DELAY = 1.0 seconds  # Default
# Configurable via: export SEARXNG_MIN_DELAY=2.0
```

**Effect**: Maximum 1 request/second (configurable)

#### 2. **User-Agent Rotation**
```python
CRAWL4AI_USER_AGENT_ROTATION = True  # Enabled by default
# Disable if needed: export CRAWL4AI_USER_AGENT_ROTATION=0
```

**Effect**: Each request uses a different user agent to appear as different browsers

#### 3. **Request Timeouts**
```python
CRAWL4AI_TIMEOUT = 30 seconds  # Default
# Adjust if needed: export CRAWL4AI_TIMEOUT=45
```

**Effect**: Prevents hanging requests from accumulating

#### 4. **Smart Backoff on Failures**
```python
CRAWL4AI_BACKOFF_BASE = 1.0 seconds
# Exponential backoff: 1s, 2s, 4s... if requests fail
```

**Effect**: Automatically slows down on 429/503 errors

#### 5. **Browser Type Selection**
```python
CRAWL4AI_BROWSER_TYPE = "chromium"  # or "firefox"
# Change: export CRAWL4AI_BROWSER_TYPE=firefox
```

**Effect**: Chromium appears more like a normal browser than headless crawlers

#### 6. **Robots.txt Respect**
Crawl4AI respects `robots.txt` by default - crawls won't violate site policies

#### 7. **Cache Prevents Redundant Crawls**
```python
SEARXNG_CRAWL_CACHE = True
SEARXNG_CRAWL_CACHE_TTL = 86400  # 24 hours
```

**Effect**: Same URL isn't crawled twice within 24 hours

---

## Configuration Reference

### Crawl4AI Settings

```bash
# Enable Crawl4AI (default: disabled)
export CRAWL4AI_ENABLED=1

# Browser type (chromium or firefox)
export CRAWL4AI_BROWSER_TYPE=chromium

# Request timeout in seconds
export CRAWL4AI_TIMEOUT=30

# Rotate user agents (0 or 1)
export CRAWL4AI_USER_AGENT_ROTATION=1

# Maximum pages to crawl per field
export MAX_CRAWL_PAGES_PER_FIELD=2

# Maximum characters to extract per page
export CRAWL_TEXT_MAX_CHARS=5000
```

### Rate Limiting & Safety

```bash
# Minimum delay between SearXNG requests (seconds)
export SEARXNG_MIN_DELAY=1.0

# Token bucket rate (requests per second)
export SEARXNG_RATE_LIMIT=2.0

# Enable crawl caching
export SEARXNG_CRAWL_CACHE=1

# Crawl cache TTL (seconds)
export SEARXNG_CRAWL_CACHE_TTL=86400
```

### Example Safe Configuration

```bash
# Conservative (safest - less risk of IP ban)
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=2.0          # 2 seconds between requests
export CRAWL4AI_TIMEOUT=45            # More generous timeout
export MAX_CRAWL_PAGES_PER_FIELD=1    # Only crawl 1 page per field
export CRAWL_TEXT_MAX_CHARS=3000      # Extract less text

# Balanced (default - good for most cases)
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=1.0
export CRAWL4AI_TIMEOUT=30
export MAX_CRAWL_PAGES_PER_FIELD=2
export CRAWL_TEXT_MAX_CHARS=5000

# Aggressive (faster but higher IP ban risk)
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=0.5
export CRAWL4AI_TIMEOUT=20
export MAX_CRAWL_PAGES_PER_FIELD=3
export CRAWL_TEXT_MAX_CHARS=8000
```

---

## How to Use Safely

### ✅ DO

- ✅ Use default rate limiting (1 request/second)
- ✅ Rotate user agents (enabled by default)
- ✅ Respect robots.txt
- ✅ Cache crawl results to avoid re-fetching
- ✅ Use reasonable timeouts
- ✅ Monitor logs for rate-limit responses (429/503)
- ✅ Crawl during off-peak hours if possible
- ✅ Limit crawl scope (only crawl when needed: confidence < 400)

### ❌ DON'T

- ❌ Disable rate limiting
- ❌ Set `SEARXNG_MIN_DELAY` to 0
- ❌ Set timeouts too low (< 15 seconds)
- ❌ Crawl every single search result
- ❌ Disable user-agent rotation
- ❌ Change browser type to something obviously fake
- ❌ Crawl without respecting robots.txt
- ❌ Run multiple crawlers simultaneously on same IP

---

## Real-World Examples

### Example 1: Finding Product Manufacturer

**Scenario**: Search for "fire extinguisher manufacturer" but search snippet doesn't mention it

**With Crawl4AI Disabled**:
```
Search: "fire extinguisher manufacturer"
Result snippet: "Safety equipment for emergency use..."
Confidence: 150 (too low - no manufacturer info in snippet)
Final result: NOT FOUND
```

**With Crawl4AI Enabled**:
```
Search: "fire extinguisher manufacturer"
Result snippet: "Safety equipment for emergency use..."
Confidence: 150 (too low)
→ Trigger Crawl4AI extraction
→ Full page: "...manufactured by Tyco International..."
Confidence: 850 (good!)
Final result: "Tyco International" ✅
```

### Example 2: Technical Specifications

**Without Crawling**: Missing specific technical details from snippets  
**With Crawling**: Extracts full specification tables from product pages

### Example 3: Safety Information

**Without Crawling**: Generic safety descriptions  
**With Crawling**: Complete safety data sheets and certifications

---

## Monitoring & Troubleshooting

### Check if Crawl4AI is Working

```bash
# View Crawl4AI status
grep "CRAWL4AI" data/logs/app.log | tail -20

# Example good logs:
# INFO: Crawl4AI extraction successful for https://example.com (conf=850)
# INFO: Crawl result cached for https://example.com

# Example rate limit warning:
# WARNING: Rate limit hit (429), backing off...
```

### If You Get IP Banned

**Symptoms**:
- Requests return 429 (Too Many Requests) or 403 (Forbidden)
- Page content blocked or redirected to captcha

**Recovery**:

1. **Immediate**: Disable Crawl4AI
   ```bash
   export CRAWL4AI_ENABLED=0
   ```

2. **Wait**: 1-24 hours for IP to reset

3. **Restart Conservative**: Use safe configuration
   ```bash
   export CRAWL4AI_ENABLED=1
   export SEARXNG_MIN_DELAY=3.0      # Very slow
   export MAX_CRAWL_PAGES_PER_FIELD=1
   ```

4. **Monitor**: Check logs for 429/503 errors

5. **Gradually Increase**: If no errors after 1 hour, increase rate

### Check System Health

```bash
# View all Crawl4AI-related logs
tail -50 data/logs/app.log | grep -E "Crawl|crawl|rate|429|503"

# Count successful crawls
grep -c "Crawl4AI extraction successful" data/logs/app.log

# Check cache hit rate
grep "crawl cache" data/logs/app.log | head -10
```

---

## Performance Impact

### Speed Tradeoff

| Setting | Speed | Accuracy | IP Risk |
|---------|-------|----------|---------|
| Crawl Disabled | ⚡⚡⚡ Fast | Medium | Low |
| Crawl Enabled (safe) | ⚡ Slower | High | Low |
| Crawl Enabled (aggressive) | 🐢 Slow | Very High | High |

### Typical Performance

- **Without Crawl4AI**: ~500ms per field (snippet-only)
- **With Crawl4AI (1 crawl)**: ~3-5 seconds per field (includes full page load)
- **With Crawl4AI (2 crawls)**: ~6-10 seconds per field

**Note**: Time varies based on target website performance

---

## Best Practices

### 1. Start Conservative
```bash
# Day 1: Safe configuration
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=2.0
export MAX_CRAWL_PAGES_PER_FIELD=1
```

### 2. Monitor for 24 Hours
Check logs daily for any 429/403 errors

### 3. Gradually Increase
If no issues, slowly increase rate:
```bash
# Week 2: Balanced
export SEARXNG_MIN_DELAY=1.0
export MAX_CRAWL_PAGES_PER_FIELD=2
```

### 4. Use Multiple IPs (Optional)
- Rotate through proxy services
- Use datacenter vs. residential proxies wisely
- **Warning**: Some sites ban entire proxy networks

### 5. Respect robots.txt
Never disable robots.txt respect - it's there for a reason

---

## Comparison: With vs Without Crawl4AI

### Without Crawl4AI
```
✓ Fast extraction (uses search snippets only)
✓ Very low IP ban risk
✗ Limited to snippet content (~200-500 chars)
✗ Miss detailed specifications
✗ Technical terms might not be visible
```

### With Crawl4AI (Safe Config)
```
✓ Complete page content extraction
✓ Find detailed specifications
✓ Low-moderate IP ban risk (with safeguards)
✓ Better accuracy for technical fields
✗ Slower (full page load required)
✗ Depends on target site performance
```

---

## Architecture: How Crawl4AI is Integrated

```
Field Extraction Request
        ↓
─────────────────────────────────
│ LLM Extraction (fast)         │
│ Confidence Score: conf_1      │
└─────────────────────────────────
        ↓
   [conf_1 < 400?]
   ↙       ↘
  NO       YES
  ↓         ↓
Return   [Crawl4AI Enabled?]
Result   ↙          ↘
        NO          YES
        ↓            ↓
      Return      Get URLs from
      Result      SearXNG
                   ↓
              [Rate Limit Check]
              ↙         ↘
           Wait       Proceed
            ↓           ↓
           Sleep   Crawl Page
                   ↓
              Extract Text
              ↓
           [Cache Result]
           ↓
        LLM Extraction (rich context)
        ↓
   Confidence Score: conf_2
        ↓
      [conf_2 > conf_1?]
      ↙       ↘
    YES       NO
     ↓         ↓
  Return   Return
  High    Original
  Conf    Result
```

---

## Conclusion

Crawl4AI is **safely configured** with IP ban prevention built-in:

- ✅ Rate limiting enforced (1 req/sec default)
- ✅ User-agent rotation enabled
- ✅ Request timeouts configured
- ✅ Cache prevents redundant crawls
- ✅ Respectful of robots.txt
- ✅ Only crawls when needed (low conf)

**Start with default settings and monitor logs.** Gradually increase rate if no issues detected.

**Your IP stays safe while getting better extraction results.** 🛡️

