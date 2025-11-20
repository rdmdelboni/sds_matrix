# 🚨 IP Ban Prevention - Quick Reference

## 🎯 TL;DR - Don't Want to Get Banned?

```bash
# 1. Use this preset (add to .env.local):
SEARXNG_RATE_LIMIT=1.0    # Max 1 search per second
SEARXNG_MIN_DELAY=2.0     # Wait 2 seconds between searches
SEARXNG_CACHE=1           # Cache results to avoid duplicate searches

# 2. Or run the interactive config tool:
./configure_rate_limiting.sh

# 3. Always keep SearXNG running:
docker compose up -d

# 4. Monitor for issues:
tail -f data/logs/app.log | grep -i "rate\|429\|403"
```

---

## 📊 Current Protection Status

✅ **You're already protected!** The system has:

- **Local SearXNG**: Search engines see SearXNG, not you
- **Rate Limiting**: 2.0 requests/second (default)
- **Minimum Delay**: 1 second between requests
- **Smart Caching**: 7-day cache reduces duplicate requests
- **Exponential Backoff**: Auto-retries with delays on errors
- **User-Agent Rotation**: Looks like different browsers

---

## ⚙️ Quick Adjustments

### I Want Maximum Safety (Slow but Safe)

**Add to `.env.local`:**
```bash
SEARXNG_RATE_LIMIT=1.0     # 1 search per second
SEARXNG_MIN_DELAY=2.0      # 2 seconds minimum between searches
SEARXNG_BURST_LIMIT=2.0    # Low burst capacity
```

**Result:** ~30 searches/minute, very low ban risk

### I Want Balanced Performance (Default)

**Already configured!** Or explicitly set:
```bash
SEARXNG_RATE_LIMIT=2.0     # 2 searches per second
SEARXNG_MIN_DELAY=1.0      # 1 second minimum
SEARXNG_BURST_LIMIT=5.0    # Moderate burst
```

**Result:** ~120 searches/minute, good balance

### I Need Speed (Higher Risk)

**⚠️ Use with caution:**
```bash
SEARXNG_RATE_LIMIT=5.0     # 5 searches per second
SEARXNG_MIN_DELAY=0.5      # 500ms minimum
SEARXNG_BURST_LIMIT=10.0   # High burst
```

**Result:** ~300 searches/minute, monitor for bans

---

## 🚨 Signs You're Getting Banned

### Check Your Logs

```bash
# Watch for problems in real-time
tail -f data/logs/app.log | grep -E "429|403|rate|limit"

# Check SearXNG container logs
docker compose logs searxng | grep -E "error|warn|captcha|blocked"
```

### Warning Signs

- **429 Errors**: "Too Many Requests" - slow down immediately
- **403 Errors**: "Forbidden" - you may be blocked
- **Empty Results**: Search returns nothing when it shouldn't
- **CAPTCHA Messages**: In SearXNG logs

---

## 🛠️ Quick Fixes

### If You Get a 429 Error

```bash
# 1. Stop your application
pkill -f "python main.py"

# 2. Slow down (add to .env.local)
echo "SEARXNG_RATE_LIMIT=0.5" >> .env.local
echo "SEARXNG_MIN_DELAY=3.0" >> .env.local

# 3. Wait 10 minutes
sleep 600

# 4. Restart
python main.py
```

### If You Get a 403 Error

```bash
# 1. Check which search engine is blocked
docker compose logs searxng | grep -i "403"

# 2. Disable problematic engines in searxng/settings.yml
# Example: disable Google temporarily
sed -i '/name: google/,/disabled:/s/disabled: false/disabled: true/' searxng/settings.yml

# 3. Restart SearXNG
docker compose restart searxng

# 4. Use slower rate
echo "SEARXNG_RATE_LIMIT=1.0" >> .env.local
```

### If Cache Stops Working

```bash
# Check cache database
ls -lh data/duckdb/searxng_cache.db

# Enable cache if disabled
echo "SEARXNG_CACHE=1" >> .env.local

# Clear old cache if corrupted
rm data/duckdb/searxng_cache.db
# (Will be recreated automatically)
```

---

## 📈 Performance vs Safety

| Setting | Searches/Min | Ban Risk | Use Case |
|---------|--------------|----------|----------|
| `RATE=0.5` | ~30 | 🛡️🛡️🛡️🛡️🛡️ Very Low | Production |
| `RATE=1.0` | ~60 | 🛡️🛡️🛡️🛡️ Low | Recommended |
| `RATE=2.0` | ~120 | 🛡️🛡️🛡️ Medium | **Default** |
| `RATE=5.0` | ~300 | 🛡️🛡️ Higher | Testing only |
| `RATE=10.0` | ~600 | 🛡️ High | Not recommended |

---

## 🔍 Testing Your Settings

### Quick Rate Test

```bash
python -c "
import time, os
from src.core.searxng_client import SearXNGClient

os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'
client = SearXNGClient()

start = time.time()
for i in range(5):
    t0 = time.time()
    client._wait_for_rate_limit()
    delay = time.time() - t0
    print(f'Request {i+1}: waited {delay:.2f}s')

total = time.time() - start
print(f'Total: {total:.2f}s = {5/total:.2f} req/sec')
"
```

### Full Search Test

```bash
python test_searxng_online_search.py
```

---

## 🆘 Emergency Procedures

### Got Banned? Do This:

1. **STOP** - Kill your application immediately
   ```bash
   pkill -f "python main.py"
   ```

2. **WAIT** - Most bans are temporary (1-24 hours)
   ```bash
   # Wait at least 1 hour
   sleep 3600
   ```

3. **SLOW DOWN** - Reduce rate to minimum
   ```bash
   cat >> .env.local << EOF
   SEARXNG_RATE_LIMIT=0.5
   SEARXNG_MIN_DELAY=5.0
   SEARXNG_BURST_LIMIT=1.0
   EOF
   ```

4. **CHECK LOGS** - Find which engine banned you
   ```bash
   docker compose logs searxng | tail -100
   ```

5. **DISABLE ENGINE** - Edit `searxng/settings.yml`
   - Find the problematic engine
   - Set `disabled: true`
   - Restart: `docker compose restart searxng`

6. **RESTART CAUTIOUSLY** - Test with single search first
   ```bash
   python -c "
   from src.core.searxng_client import SearXNGClient
   import os
   os.environ['SEARXNG_INSTANCES'] = 'http://localhost:8080'
   client = SearXNGClient()
   result = client.search_online_for_missing_fields(
       product_name='water',
       cas_number='7732-18-5',
       missing_fields=['numero_onu']
   )
   print('Test successful!' if result else 'Still blocked')
   "
   ```

---

## 🎓 Best Practices

### ✅ DO

- ✅ Use local SearXNG (not public instances)
- ✅ Enable caching (`SEARXNG_CACHE=1`)
- ✅ Keep rate ≤ 2.0 req/sec for production
- ✅ Monitor logs regularly
- ✅ Test with small batches first
- ✅ Respect exponential backoff
- ✅ Use realistic delays (≥1 second)

### ❌ DON'T

- ❌ Disable all safety features at once
- ❌ Ignore 429/403 errors
- ❌ Run large batches untested
- ❌ Set rate > 10 req/sec
- ❌ Disable caching
- ❌ Override exponential backoff
- ❌ Run multiple instances without coordination

---

## 📚 More Information

- **Full Guide**: `IP_BAN_PREVENTION.md` (comprehensive details)
- **Configure Tool**: `./configure_rate_limiting.sh` (interactive)
- **Test Script**: `test_searxng_online_search.py` (validate setup)
- **SearXNG Logs**: `docker compose logs searxng`
- **App Logs**: `tail -f data/logs/app.log`

---

## 🔧 Interactive Config Tool

```bash
# Run the configuration wizard
./configure_rate_limiting.sh

# It will:
# 1. Show current settings
# 2. Let you choose a preset (Safe/Balanced/Aggressive)
# 3. Update .env.local automatically
# 4. Show you what changed
```

---

## 💡 Pro Tips

1. **Start Conservative**: Begin with slow rate, increase gradually
2. **Monitor First Hour**: Watch logs closely when testing new settings
3. **Use Cache Aggressively**: Cache TTL of 7 days prevents duplicate requests
4. **Test Search Engines**: Some engines are more permissive than others
5. **Consider Tor**: For maximum privacy, route SearXNG through Tor
6. **Schedule Wisely**: Avoid peak hours if doing bulk searches
7. **Batch Intelligently**: Process in small batches with breaks

---

## 🎯 One-Liner Recommendations

```bash
# Copy this line, paste into your .env.local, and you're safe:
echo -e "SEARXNG_RATE_LIMIT=1.0\nSEARXNG_MIN_DELAY=2.0\nSEARXNG_CACHE=1" >> .env.local
```

**That's it!** You now have strong IP ban protection. 🛡️

---

**Questions?** Check `IP_BAN_PREVENTION.md` for detailed explanations.
