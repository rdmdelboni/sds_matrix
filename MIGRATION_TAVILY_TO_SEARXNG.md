# Migration Guide: Tavily → SearXNG + Crawl4AI

## 🎯 Summary

**Tavily API support has been removed** in favor of an open-source solution: **SearXNG + Crawl4AI**.

### Why the Change?

| Aspect | Tavily (Old) | SearXNG + Crawl4AI (New) |
|--------|--------------|--------------------------|
| **Cost** | $0.01/search, 1000 free/month | **100% Free, unlimited** |
| **Privacy** | Data sent to third party | **All local/self-hosted** |
| **API Key** | Required | **None required** |
| **Setup** | Easy (just add key) | Requires Docker |
| **Speed** | Very fast | Good (depends on engines) |

## 🚀 Quick Migration (3 Steps)

### Step 1: Install Crawl4AI

```bash
pip install -r requirements.txt  # Already updated
crawl4ai-setup  # Install browser dependencies
```

### Step 2: Start SearXNG

```bash
./setup_searxng.sh  # Automated setup script
```

**OR manually:**

```bash
docker compose up -d
```

### Step 3: Remove Old Configuration

Remove these from your `.env` or `.env.local`:

```bash
# ❌ Remove these lines:
TAVILY_API_KEY=...
TAVILY_BASE_URL=...
ONLINE_SEARCH_PROVIDER=tavily
```

**That's it!** The system now uses SearXNG by default (no configuration needed).

## 📋 Detailed Changes

### Removed Files/Config
- ❌ `TavilyClient` class (from `src/core/llm_client.py`)
- ❌ `TAVILY_CONFIG` (from `src/utils/config.py`)
- ❌ All `TAVILY_*` environment variables
- ❌ Test files: `test_tavily_*.py`

### Added Files
- ✅ `docker-compose.yml` - SearXNG Docker setup
- ✅ `setup_searxng.sh` - Automated setup script
- ✅ `SEARXNG_COMPLETE_GUIDE.md` - Full documentation
- ✅ `src/core/searxng_client.py` - Already existed, now default

### Updated Files
- ✅ `requirements.txt` - Added `crawl4ai`
- ✅ `src/utils/config.py` - Default provider = `searxng`
- ✅ `src/gui/main_app.py` - Removed Tavily import
- ✅ `.env.local.example` - Updated instructions
- ✅ `README.md` - Updated documentation

## 🔧 Configuration Options

### Default (No Config Needed)

SearXNG is already configured and ready to use. Just run:

```bash
./setup_searxng.sh
```

### Optional Configuration

If you want to customize, add to `.env.local`:

```bash
# Optional SearXNG settings
SEARXNG_INSTANCES=http://localhost:8080  # Your local instance
SEARXNG_RATE_LIMIT=2.0                   # Requests per second
SEARXNG_MIN_DELAY=1.0                    # Seconds between requests
SEARXNG_CRAWL=1                          # Enable full page crawling
SEARXNG_LANGUAGE=pt-BR                   # Portuguese Brazil
```

## 🆘 Alternatives (If You Need Commercial API)

If you prefer using commercial APIs instead of SearXNG:

### Option 1: Google Gemini

```bash
# .env.local
ONLINE_SEARCH_PROVIDER=gemini
GOOGLE_API_KEY=your_key_here
```

### Option 2: xAI Grok

```bash
# .env.local
ONLINE_SEARCH_PROVIDER=grok
GROK_API_KEY=your_key_here
```

## ❓ FAQ

### Q: Can I still use my Tavily API key?

**A:** No, Tavily support has been completely removed. Please migrate to SearXNG (free) or Gemini/Grok (paid alternatives).

### Q: Is SearXNG as good as Tavily?

**A:** SearXNG provides similar functionality but:
- ✅ **Pros**: Free, private, unlimited, open-source
- ❌ **Cons**: Requires Docker, slightly slower, needs rate limiting

### Q: I don't want to use Docker. What are my options?

**A:** Use one of these alternatives:
1. **Gemini** (Google) - Free tier with limits
2. **Grok** (xAI) - Paid, no rate limits
3. **Public SearXNG instances** (set `SEARXNG_INSTANCES` to public URLs)

### Q: Will my existing data be affected?

**A:** No. All your extracted data in DuckDB remains unchanged. Only the online search method has changed.

### Q: How do I test if SearXNG is working?

```bash
# Test SearXNG endpoint
curl "http://localhost:8080/search?q=test&format=json"

# Test Crawl4AI
python -c "from crawl4ai import AsyncWebCrawler; print('✅ OK')"
```

## 📚 Additional Resources

- **Full Guide**: `SEARXNG_COMPLETE_GUIDE.md`
- **SearXNG Docs**: https://docs.searxng.org/
- **Crawl4AI Docs**: https://crawl4ai.com/docs
- **Docker Install**: https://docs.docker.com/get-docker/

## 🆘 Troubleshooting

### SearXNG won't start

```bash
# Check Docker is running
docker ps

# View logs
docker compose logs -f searxng

# Restart
docker compose restart searxng
```

### JSON format not enabled

```bash
# Re-run setup script
./setup_searxng.sh

# Or manually check settings
grep -A 3 "formats:" searxng/settings.yml
# Should show:
#   formats:
#     - html
#     - json
```

### Crawl4AI errors

```bash
# Reinstall browser deps
crawl4ai-setup

# Or reinstall package
pip uninstall crawl4ai
pip install crawl4ai
```

## 💬 Need Help?

- Check the full guide: `SEARXNG_COMPLETE_GUIDE.md`
- Open an issue on GitHub
- Review example configurations in `.env.local.example`

---

**Migration completed?** ✅ You're now running a fully open-source, privacy-respecting search solution!
