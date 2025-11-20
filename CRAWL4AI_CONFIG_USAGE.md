# Crawl4AI Configuration Usage Guide

After recent updates, you have **3 ways** to configure Crawl4AI for automatic startup:

## Option 1: Automatic via `iniciar.sh` (Recommended - No Setup Needed)

Simply run:
```bash
./iniciar.sh
```

✅ **Benefits:**
- Automatically configured on every startup
- Safe defaults (balanced mode)
- IP protection enabled
- No manual steps needed
- Visual confirmation on startup

```
✅ Crawl4AI configured in BALANCED mode
   • CRAWL4AI_ENABLED: 1
   • CRAWL4AI_MIN_DELAY: 1.0s
   • MAX_CRAWL_PAGES_PER_FIELD: 2
   • FIELD_SEARCH_MAX_ATTEMPTS: 3
   • IP Ban Protection: ACTIVE
```

---

## Option 2: Source `.env.crawl4ai` File (Flexible Profile Selection)

If you want to use a different IP protection profile:

```bash
# Load configuration, then start app
source .env.crawl4ai
python main.py
```

**Available profiles in `.env.crawl4ai`:**

```bash
# Conservative (slowest, safest)
# Delay: 3.0s between requests
# Pages per field: 1
# Max attempts: 2

# Balanced (recommended, default)
# Delay: 1.0s between requests
# Pages per field: 2
# Max attempts: 3

# Aggressive (fastest, higher risk)
# Delay: 0.5s between requests
# Pages per field: 3
# Max attempts: 5
```

**To use different profile:**
1. Edit `.env.crawl4ai`
2. Uncomment your chosen profile (comment out others)
3. Save
4. Run: `source .env.crawl4ai && python main.py`

---

## Option 3: Use Python Module (Programmatic Configuration)

Call from your code for dynamic configuration:

```python
from config_crawl4ai import load_crawl4ai_config, print_config

# Configure before starting your app
load_crawl4ai_config(mode="balanced")  # or "conservative", "aggressive", "custom"

# Verify configuration
print_config()

# Now start your app
# ... your app logic ...
```

**Available modes:**
```python
load_crawl4ai_config(mode="conservative")  # Safest
load_crawl4ai_config(mode="balanced")      # Recommended
load_crawl4ai_config(mode="aggressive")    # Fastest
load_crawl4ai_config(mode="custom")        # Load from .env.crawl4ai
```

**Programmatic usage in `main.py`:**
```python
#!/usr/bin/env python3
"""FDS Matrix Extractor - Main Entry Point"""

from config_crawl4ai import load_crawl4ai_config, print_config
import sys

# Configure Crawl4AI before anything else
try:
    mode = sys.argv[1] if len(sys.argv) > 1 else "balanced"
    load_crawl4ai_config(mode=mode)
    print_config()
except Exception as e:
    print(f"Warning: Could not load Crawl4AI config: {e}")

# Now import and run your app
from project.app import main

if __name__ == "__main__":
    main()
```

Then run:
```bash
python main.py conservative  # Use conservative mode
python main.py balanced      # Use balanced mode (default)
python main.py aggressive    # Use aggressive mode
python main.py custom        # Use .env.crawl4ai settings
python main.py               # Defaults to balanced
```

---

## Command-Line Tool for Direct Configuration

Test/verify configuration without running app:

```bash
python config_crawl4ai.py conservative
python config_crawl4ai.py balanced
python config_crawl4ai.py aggressive
python config_crawl4ai.py custom
```

Output:
```
✅ Crawl4AI configured in CONSERVATIVE mode
   • CRAWL4AI_ENABLED: 1
   • CRAWL4AI_MIN_DELAY: 3.0s
   • MAX_CRAWL_PAGES_PER_FIELD: 1
   • FIELD_SEARCH_MAX_ATTEMPTS: 2
   • IP Ban Protection: ACTIVE

============================================================
CRAWL4AI CONFIGURATION
============================================================
✅ CRAWL4AI_ENABLED                 = 1
✅ CRAWL4AI_MIN_DELAY               = 3.0
✅ CRAWL4AI_BROWSER_TYPE            = chromium
✅ CRAWL4AI_HEADLESS                = true
✅ CRAWL4AI_CACHE_ENABLED           = true
✅ MAX_CRAWL_PAGES_PER_FIELD        = 1
✅ CRAWL_TEXT_MAX_CHARS             = 5000
✅ FIELD_SEARCH_MAX_ATTEMPTS        = 2
✅ FIELD_SEARCH_BACKOFF_BASE        = 0.5
✅ SEARXNG_MIN_DELAY                = 1.5
✅ SEARXNG_CACHE                    = 1
✅ SEARXNG_CRAWL                    = 1
============================================================
```

---

## Configuration Priority (if multiple methods used)

1. **Highest:** Environment variables already set
2. **Middle:** `.env.crawl4ai` file (Option 2)
3. **Middle:** `config_crawl4ai.py` arguments (Option 3)
4. **Lowest:** `iniciar.sh` defaults (Option 1)

---

## IP Ban Protection: 7 Layers Across All Methods

Regardless of configuration method chosen, all have:

| Layer | Protection |
|-------|-----------|
| 1 | Minimum delay between requests (configurable) |
| 2 | robots.txt compliance (automatic) |
| 3 | User-agent rotation (automatic) |
| 4 | Exponential backoff with jitter on errors |
| 5 | Token bucket rate limiting |
| 6 | DuckDB result caching |
| 7 | Graceful fallback to snippets on ban |

---

## Recommended Setup

For most users, **Option 1 is recommended**:

```bash
./iniciar.sh  # That's it! Everything is configured automatically
```

**For advanced users** who want profile control:

```bash
source .env.crawl4ai  # Choose your profile in this file
python main.py        # Run your app
```

**For developers** integrating into larger projects:

```python
from config_crawl4ai import load_crawl4ai_config
load_crawl4ai_config(mode="balanced")
# Then proceed with your app logic
```

---

## Troubleshooting

### Configuration not applying

Check if environment variables are set:
```bash
python config_crawl4ai.py balanced
echo $CRAWL4AI_ENABLED  # Should show: 1
```

### Want to disable Crawl4AI temporarily

```bash
export CRAWL4AI_ENABLED=0
python main.py
```

### Want to change IP protection aggressiveness

Edit `iniciar.sh` or `.env.crawl4ai`, modify these values:

| Goal | Change |
|------|--------|
| More protection | Increase `CRAWL4AI_MIN_DELAY` |
| Fewer pages crawled | Decrease `MAX_CRAWL_PAGES_PER_FIELD` |
| More retries | Increase `FIELD_SEARCH_MAX_ATTEMPTS` |

---

## Summary Table

| Method | Ease | Flexibility | Automation |
|--------|------|-------------|-----------|
| Option 1: `iniciar.sh` | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Option 2: `.env.crawl4ai` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Option 3: `config_crawl4ai.py` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

For most use cases: **Start with Option 1, upgrade to Option 2/3 as needed.**
