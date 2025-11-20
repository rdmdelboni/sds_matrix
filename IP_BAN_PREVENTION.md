# 🛡️ IP Ban Prevention Guide for SearXNG

## Overview

This guide explains how to avoid IP bans when using SearXNG for automated searches. The system has **multiple layers of protection** built-in, but you can adjust them based on your needs.

---

## 🔒 Current Protection Layers

### 1. **Local SearXNG Instance** (Primary Defense)
✅ **You're already using this!**
- Your SearXNG runs locally on `http://localhost:8080`
- Search engines see requests from **SearXNG**, not directly from you
- SearXNG already has built-in rate limiting and bot protection

### 2. **Token Bucket Rate Limiting**
✅ **Currently active: 2.0 requests/second**
- Prevents burst traffic that looks like a bot
- Smooths out request patterns
- Configurable burst capacity (default: 5 requests)

### 3. **Minimum Delay Between Requests**
✅ **Currently: 1 second minimum between each search**
- Additional safeguard on top of rate limiting
- Ensures human-like pacing

### 4. **Exponential Backoff**
✅ **Automatically retries with increasing delays**
- Detects 429 (Too Many Requests) errors
- Backs off exponentially: 2s → 4s → 8s
- Random jitter prevents thundering herd

### 5. **User-Agent Rotation**
✅ **Cycles through realistic browser user-agents**
- Mimics different browsers (Firefox, Chrome, Safari, Edge)
- Makes requests look more natural

### 6. **Persistent Caching**
✅ **DuckDB cache prevents duplicate searches**
- Cache TTL: 7 days (default)
- Dramatically reduces actual API calls
- Stores both search results and crawled content

### 7. **Multiple Instance Support**
✅ **Fallback to public instances if local fails**
- Distributes load across multiple SearXNG servers
- Health checks rotate to healthy instances

---

## ⚙️ Configuration Options

### Environment Variables

Add these to your `.env` or `.env.local` file:

```bash
# === Core Settings ===
ONLINE_SEARCH_PROVIDER=searxng
SEARXNG_INSTANCES=http://localhost:8080

# === Rate Limiting (IP Ban Prevention) ===
# Requests per second (lower = safer, higher = faster)
SEARXNG_RATE_LIMIT=2.0          # Default: 2.0 req/sec
SEARXNG_BURST_LIMIT=5.0         # Burst capacity (tokens)
SEARXNG_MIN_DELAY=1.0           # Min seconds between requests

# === Retry & Backoff ===
SEARXNG_MAX_RETRIES=3           # Max retries on failure
SEARXNG_BACKOFF=2.0             # Initial backoff delay (seconds)

# === Caching (Reduces Requests) ===
SEARXNG_CACHE=1                 # 1=enabled, 0=disabled
SEARXNG_CACHE_TTL=604800        # Cache TTL in seconds (7 days)

# === Other ===
SEARXNG_TIMEOUT=30              # Request timeout (seconds)
SEARXNG_LANGUAGE=en             # Search language
```

### Recommended Settings by Use Case

#### 🐌 Maximum Safety (Avoid Bans at All Costs)
```bash
SEARXNG_RATE_LIMIT=1.0          # 1 search per second
SEARXNG_BURST_LIMIT=2.0         # Low burst
SEARXNG_MIN_DELAY=2.0           # 2 seconds between searches
SEARXNG_MAX_RETRIES=5           # More patient retries
SEARXNG_BACKOFF=5.0             # Longer backoff
SEARXNG_CACHE=1                 # Must be enabled
```

**Result:** ~60 searches/minute max, very low ban risk

#### ⚖️ Balanced (Current Default)
```bash
SEARXNG_RATE_LIMIT=2.0          # 2 searches per second
SEARXNG_BURST_LIMIT=5.0         # Moderate burst
SEARXNG_MIN_DELAY=1.0           # 1 second minimum
SEARXNG_MAX_RETRIES=3           # Standard retries
SEARXNG_BACKOFF=2.0             # Normal backoff
SEARXNG_CACHE=1                 # Enabled
```

**Result:** ~120 searches/minute, good balance

#### 🚀 Aggressive (Higher Risk)
```bash
SEARXNG_RATE_LIMIT=5.0          # 5 searches per second
SEARXNG_BURST_LIMIT=10.0        # High burst
SEARXNG_MIN_DELAY=0.5           # 500ms minimum
SEARXNG_MAX_RETRIES=2           # Quick retries
SEARXNG_BACKOFF=1.0             # Short backoff
SEARXNG_CACHE=1                 # Still recommended
```

**Result:** ~300 searches/minute, **higher ban risk**

---

## 🔧 SearXNG Container Configuration

### Enable More Search Engines

Your SearXNG has **rate limiting disabled** (`limiter: false`), which is good for local use. However, you can enable more search engines to distribute load:

**Edit `searxng/settings.yml`:**

```yaml
# Line ~188: Enable more engines for redundancy
engines:
  - name: duckduckgo
    engine: duckduckgo
    shortcut: ddg
    disabled: false  # ✅ Keep enabled

  - name: google
    engine: google
    shortcut: go
    disabled: false  # ✅ Enable if you want Google results

  - name: bing
    engine: bing
    shortcut: bi
    disabled: false  # ✅ Enable Bing as backup

  - name: qwant
    qwant_categ: web
    engine: qwant
    shortcut: qw
    categories: [general, web]
    disabled: false  # ✅ Privacy-focused alternative

  - name: brave
    engine: brave
    shortcut: br
    disabled: false  # ✅ Good for avoiding Google/Bing
```

**After editing, restart:**
```bash
docker compose restart searxng
```

### Add Request Delays in SearXNG

Add this to `searxng/settings.yml` under the `outgoing:` section:

```yaml
outgoing:
  request_timeout: 5.0          # Increase timeout
  pool_connections: 50          # Reduce concurrent connections (was 100)
  pool_maxsize: 10              # Reduce max pool size (was 20)
  
  # Add delays between engine requests (NEW)
  # This makes SearXNG itself more polite to search engines
  max_request_timeout: 10.0
```

**Restart after changes:**
```bash
docker compose restart searxng
```

---

## 📊 Monitoring for Bans

### Signs You're Getting Rate Limited

1. **429 Status Codes**
   - "Too Many Requests" errors in logs
   - Exponential backoff automatically activates

2. **403 Forbidden**
   - Some search engines block you
   - Check `docker compose logs searxng`

3. **Empty Results**
   - Search returns no results when it should
   - May indicate soft blocking

4. **CAPTCHA Challenges**
   - SearXNG logs will show "CAPTCHA detected"
   - Suspend that engine temporarily

### Check Logs

**Application logs:**
```bash
# Watch for rate limiting messages
tail -f data/logs/app.log | grep -i "rate"

# Check for errors
grep -i "429\|403\|rate\|limit" data/logs/app.log
```

**SearXNG container logs:**
```bash
# Real-time monitoring
docker compose logs -f searxng

# Check for errors
docker compose logs searxng | grep -i "error\|warn\|captcha"
```

---

## 🛠️ Advanced Techniques

### 1. Use Tor for SearXNG (Maximum Privacy)

**Edit `searxng/settings.yml`:**
```yaml
outgoing:
  proxies:
    all://:
      - socks5://127.0.0.1:9050  # Tor SOCKS proxy
  using_tor_proxy: true
```

**Start Tor:**
```bash
# Install Tor
sudo apt-get install tor  # Debian/Ubuntu
brew install tor          # macOS

# Start Tor
sudo systemctl start tor
```

**Restart SearXNG:**
```bash
docker compose restart searxng
```

### 2. Multiple SearXNG Instances

Run multiple SearXNG containers with different configurations:

**docker-compose.yml:**
```yaml
services:
  searxng1:
    image: searxng/searxng:latest
    ports:
      - "8080:8888"
    volumes:
      - ./searxng:/etc/searxng:rw
      
  searxng2:
    image: searxng/searxng:latest
    ports:
      - "8081:8888"
    volumes:
      - ./searxng2:/etc/searxng:rw
      
  searxng3:
    image: searxng/searxng:latest
    ports:
      - "8082:8888"
    volumes:
      - ./searxng3:/etc/searxng:rw
```

**Configure in `.env`:**
```bash
SEARXNG_INSTANCES=http://localhost:8080,http://localhost:8081,http://localhost:8082
```

### 3. Random Delays (More Human-Like)

The code already has **jitter** built-in, but you can increase randomness:

**Edit `.env`:**
```bash
# Base delay + random jitter
SEARXNG_MIN_DELAY=1.0     # Minimum 1 second
SEARXNG_MAX_JITTER=2.0    # Add random 0-2 seconds (TODO: implement)
```

### 4. Respect robots.txt

SearXNG already respects `robots.txt`, but ensure your crawling does too:

**Check Crawl4AI settings:**
- The Crawl4AI integration respects `robots.txt` by default
- Uses realistic delays between page crawls
- Rotates user agents

---

## 🚨 What to Do If You Get Banned

### 1. **Stop Immediately**
```bash
# Stop all searches
pkill -f "python main.py"

# Let things cool down
sleep 3600  # Wait 1 hour
```

### 2. **Check Which Engine Banned You**
```bash
# Check SearXNG logs
docker compose logs searxng | grep -i "403\|429\|captcha\|blocked"
```

### 3. **Disable Problematic Engines**

**Edit `searxng/settings.yml`:**
```yaml
engines:
  - name: google
    engine: google
    disabled: true  # ❌ Disable temporarily
```

### 4. **Increase Delays**
```bash
# In .env
SEARXNG_RATE_LIMIT=0.5    # Slow down to 1 search every 2 seconds
SEARXNG_MIN_DELAY=3.0     # Minimum 3 seconds between requests
```

### 5. **Use Tor or VPN**
- Route SearXNG through Tor (see above)
- Use a VPN on your host machine
- Rotate IP addresses if possible

### 6. **Clear SearXNG Instance State**
```bash
# If using public instances, switch to local only
echo "SEARXNG_INSTANCES=http://localhost:8080" > .env.local

# Restart
docker compose restart searxng
```

### 7. **Wait It Out**
- Most bans are temporary (1 hour to 24 hours)
- Don't retry aggressively
- Let the cache do its job

---

## 📈 Performance vs Safety Trade-offs

| Setting | Safety | Speed | Use Case |
|---------|--------|-------|----------|
| `RATE_LIMIT=0.5` | 🛡️🛡️🛡️🛡️🛡️ | 🐌 | Production, high-value data |
| `RATE_LIMIT=1.0` | 🛡️🛡️🛡️🛡️ | 🐌🐌 | Recommended minimum |
| `RATE_LIMIT=2.0` | 🛡️🛡️🛡️ | 🚀🚀 | **Current default** |
| `RATE_LIMIT=5.0` | 🛡️🛡️ | 🚀🚀🚀🚀 | Testing, dev environment |
| `RATE_LIMIT=10.0` | 🛡️ | 🚀🚀🚀🚀🚀 | High risk, use with care |

---

## 🎯 Best Practices Checklist

✅ **Always use local SearXNG** (not public instances)
✅ **Enable caching** (`SEARXNG_CACHE=1`)
✅ **Keep rate limit ≤ 2.0 req/sec** for production
✅ **Monitor logs** for 429/403 errors
✅ **Use minimum 1 second delay** between requests
✅ **Enable multiple search engines** in SearXNG
✅ **Test with small batches** before bulk operations
✅ **Respect exponential backoff** (don't override retries)
✅ **Consider Tor/VPN** for sensitive use cases
✅ **Document your usage patterns** to identify issues

---

## 🔍 Testing Your Configuration

### Quick Test Script

```bash
# Test current rate limiting
python -c "
import time
from src.core.searxng_client import SearXNGClient
import os

os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'

client = SearXNGClient()
queries = ['test 1', 'test 2', 'test 3', 'test 4', 'test 5']

print('Testing rate limiting...')
start = time.time()

for query in queries:
    before = time.time()
    client._wait_for_rate_limit()  # Internal method
    after = time.time()
    delay = after - before
    print(f'Query {query}: waited {delay:.2f}s')

total = time.time() - start
print(f'\nTotal time: {total:.2f}s')
print(f'Average: {total/len(queries):.2f}s per query')
print(f'Rate: {len(queries)/total:.2f} req/sec')
"
```

### Load Test (Use Carefully!)

```bash
# Run only in dev/test environment!
python test_searxng_online_search.py
```

---

## 📚 Additional Resources

- **SearXNG Documentation**: https://docs.searxng.org/
- **Rate Limiting Best Practices**: https://cloud.google.com/architecture/rate-limiting-strategies-techniques
- **Crawl4AI GitHub**: https://github.com/unclecode/crawl4ai
- **Tor Project**: https://www.torproject.org/

---

## 🆘 Need Help?

If you're still getting banned:

1. **Check your logs**: `data/logs/app.log`
2. **Check SearXNG logs**: `docker compose logs searxng`
3. **Reduce rate limit**: Start with `SEARXNG_RATE_LIMIT=0.5`
4. **Enable only DuckDuckGo**: Disable Google/Bing in `settings.yml`
5. **Use Tor**: Route through Tor for maximum anonymity
6. **Contact search engine**: Some have API programs for researchers

---

**✨ Remember: The best way to avoid bans is to not look like a bot. Slow, steady, and cached requests are your friends!**
