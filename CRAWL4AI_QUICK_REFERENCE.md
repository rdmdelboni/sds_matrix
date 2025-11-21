# Crawl4AI Quick Reference Card

## Enable Crawl4AI (Safe Default)

```bash
# One-time setup
pip install crawl4ai
crawl4ai-setup

# Enable in your application
export CRAWL4AI_ENABLED=1

# Start your app
./iniciar.sh
```

---

## Configuration Presets

### 🟢 SAFE (Recommended for Most Users)
```bash
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=1.0
export MAX_CRAWL_PAGES_PER_FIELD=2
export CRAWL_TEXT_MAX_CHARS=5000
```
**Best for**: General use, low IP ban risk, good accuracy

### 🟡 CONSERVATIVE (Paranoid Mode)
```bash
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=2.0
export MAX_CRAWL_PAGES_PER_FIELD=1
export CRAWL_TEXT_MAX_CHARS=3000
export CRAWL4AI_TIMEOUT=45
```
**Best for**: High-risk sites, shared/residential IPs, first time

### 🔴 AGGRESSIVE (Fast But Risky)
```bash
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=0.5
export MAX_CRAWL_PAGES_PER_FIELD=3
export CRAWL_TEXT_MAX_CHARS=8000
export CRAWL4AI_TIMEOUT=20
```
**Best for**: Datacenter IP, unrestricted sites, need speed

---

## Troubleshooting

### ✅ Working (Look for These in Logs)
```
INFO: Crawl4AI extraction successful
INFO: crawl cache hit
INFO: Rate limit enforced (1.0s minimum)
```

### ⚠️ Rate Limit Hit (429 Error)
```
WARNING: 429 Too Many Requests - backing off...

FIX: Increase delay
export SEARXNG_MIN_DELAY=2.0  # was 1.0
```

### 🚫 IP Banned (403 Error)
```
ERROR: 403 Forbidden - possible IP ban

FIX: 
1. Disable Crawl4AI: export CRAWL4AI_ENABLED=0
2. Wait 24 hours
3. Re-enable conservatively: export SEARXNG_MIN_DELAY=3.0
```

### ⏱️ Timeout (Slow Sites)
```
ERROR: Request timeout

FIX: Increase timeout
export CRAWL4AI_TIMEOUT=45  # was 30
```

---

## Common Tasks

### Check if Crawl4AI is Working
```bash
grep "CRAWL4AI" data/logs/app.log | tail -10
```

### See Rate Limiting in Action
```bash
grep "Rate limit" data/logs/app.log | head -5
```

### Count Successful Crawls
```bash
grep -c "extraction successful" data/logs/app.log
```

### View Latest Errors
```bash
tail -100 data/logs/app.log | grep -E "ERROR|WARNING"
```

---

## All Configuration Options

```bash
# Enable/Disable
export CRAWL4AI_ENABLED=1                    # 0 or 1

# Browser Settings
export CRAWL4AI_BROWSER_TYPE=chromium        # chromium or firefox
export CRAWL4AI_TIMEOUT=30                   # seconds

# User Agent
export CRAWL4AI_USER_AGENT_ROTATION=1        # 0 or 1 (rotate user agents)

# Rate Limiting
export SEARXNG_MIN_DELAY=1.0                 # minimum seconds between requests
export SEARXNG_RATE_LIMIT=2.0                # requests per second

# Crawling Scope
export MAX_CRAWL_PAGES_PER_FIELD=2           # max pages to crawl per field
export CRAWL_TEXT_MAX_CHARS=5000             # max text to extract

# Caching
export SEARXNG_CRAWL_CACHE=1                 # 0 or 1 (enable cache)
export SEARXNG_CRAWL_CACHE_TTL=86400         # cache duration in seconds
```

---

## Decision Tree: When to Crawl

```
Extraction Confidence < 400?
  ├─ NO  → Use search snippet result ✓
  └─ YES → Can crawl page?
     ├─ NO (CRAWL4AI_ENABLED=0)     → Return low-confidence result
     └─ YES (CRAWL4AI_ENABLED=1)    → Crawl full page
        ├─ Crawl succeeds          → Extract with full text ✓
        └─ Crawl fails (429/403)   → Fall back to snippet
```

---

## Results Improvement Examples

### Example 1: Product Manufacturer
```
❌ WITHOUT Crawl4AI:
   Snippet: "Safety equipment... reliable..."
   Result: NOT FOUND (confidence: 120)

✅ WITH Crawl4AI:
   Full Page: "Manufactured by Tyco International..."
   Result: TYCO INTERNATIONAL (confidence: 850)
```

### Example 2: Hazard Classification
```
❌ WITHOUT Crawl4AI:
   Snippet: "Contains hazardous materials"
   Result: INCOMPLETE

✅ WITH Crawl4AI:
   Full Page: "Class 8 Corrosive | UN2922"
   Result: CLASS 8, CORROSIVE (confidence: 920)
```

### Example 3: Technical Specs
```
❌ WITHOUT Crawl4AI:
   Snippet: "Industrial equipment"
   Result: MISSING SPECS

✅ WITH Crawl4AI:
   Full Page: "Capacity: 10kg, Pressure: 150PSI, Duration: 15s"
   Result: COMPLETE SPECS (confidence: 880)
```

---

## Performance Numbers

| Operation | Time | Notes |
|-----------|------|-------|
| Search only | 0.5s | Fast, limited accuracy |
| Crawl page | 3-5s | Slower, better accuracy |
| From cache | 0.1s | Fastest (if recently crawled) |
| Rate limit wait | 1-2s | Enforced between requests |

---

## Best Practices Checklist

- ✅ Start with SAFE configuration
- ✅ Monitor logs daily for errors
- ✅ Wait 24h before increasing rate
- ✅ Only increase rate if no 429/403 errors
- ✅ Never disable rate limiting
- ✅ Use user-agent rotation (default: ON)
- ✅ Respect robots.txt (automatic)
- ✅ Cache crawl results (automatic)
- ✅ Check IP status if blocked

---

## Emergency: IP Got Banned

**Immediate Action**:
```bash
# Disable Crawl4AI
export CRAWL4AI_ENABLED=0

# Restart app
./iniciar.sh
```

**Wait**: 24-48 hours for IP to reset

**Recovery**:
```bash
# Conservative restart
export CRAWL4AI_ENABLED=1
export SEARXNG_MIN_DELAY=3.0        # Very slow
export MAX_CRAWL_PAGES_PER_FIELD=1  # Minimal crawl
./iniciar.sh

# Monitor for errors
tail -f data/logs/app.log
```

---

## Support Resources

- 📖 **Full Guide**: `CRAWL4AI_SETUP_GUIDE.md`
- 📖 **IP Ban Prevention**: `IP_BAN_PREVENTION.md`
- 📊 **Architecture**: `COMPLETION_SUMMARY.md`
- 🐛 **Logs**: `data/logs/app.log`
- ⚙️ **Config**: `src/utils/config.py`

---

## Key Takeaway

✅ **Crawl4AI is safe by default**
- Rate limiting enforced
- User-agent rotation enabled  
- Cache prevents re-crawling
- Respects robots.txt
- Only crawls when needed

🚀 **Just enable it and let the system handle IP protection**

```bash
export CRAWL4AI_ENABLED=1
./iniciar.sh
```

