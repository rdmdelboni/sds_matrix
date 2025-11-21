# SearXNG + Crawl4AI: Open Source Search Solution

This project now uses **SearXNG** (open-source metasearch engine) + **Crawl4AI** (AI-powered web crawler) as the default online search solution. **No API keys required!**

## 🎯 Why SearXNG + Crawl4AI?

| Feature | Commercial APIs | SearXNG + Crawl4AI |
|---------|----------------|-------------------|
| **Cost** | Pay per request | Free, unlimited |
| **Privacy** | Data sent to third party | All local/self-hosted |
| **Rate Limits** | 100-1000 req/month | Unlimited (self-managed) |
| **Setup** | API key signup | Docker + Python |
| **Dependencies** | External service | Self-contained |
| **Speed** | Very fast | Good (depends on search engines) |

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Crawl4AI and setup
pip install crawl4ai
crawl4ai-setup
```

### 2. Start SearXNG (Docker)

```bash
# Automated setup (recommended)
./setup_searxng.sh

# OR manual setup
docker compose up -d
```

### 3. Verify Setup

```bash
# Test SearXNG
curl "http://localhost:8080/search?q=python&format=json"

# Test Crawl4AI (Python)
python -c "from crawl4ai import AsyncWebCrawler; print('✅ Crawl4AI ready')"
```

### 4. Configure Application

The application is **pre-configured** to use SearXNG by default. No additional configuration needed!

Optionally, set environment variables:

```bash
# .env or .env.local
ONLINE_SEARCH_PROVIDER=searxng  # Already the default

# Optional: Custom SearXNG instances
SEARXNG_INSTANCES=http://localhost:8080,https://searx.be

# Optional: Rate limiting (prevents IP bans)
SEARXNG_RATE_LIMIT=2.0          # Requests per second
SEARXNG_MIN_DELAY=1.0           # Min seconds between requests
SEARXNG_MAX_RETRIES=3           # Max retry attempts

# Optional: Enable crawling for full content extraction
SEARXNG_CRAWL=1                 # 0=snippets only, 1=full crawl
```

## 📋 Configuration Options

### SearXNG Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARXNG_INSTANCES` | Public instances | Comma-separated list of SearXNG URLs |
| `SEARXNG_RATE_LIMIT` | 2.0 | Requests per second (prevents bans) |
| `SEARXNG_BURST_LIMIT` | 5.0 | Maximum burst tokens |
| `SEARXNG_MIN_DELAY` | 1.0 | Minimum seconds between requests |
| `SEARXNG_MAX_RETRIES` | 3 | Max retry attempts on error |
| `SEARXNG_BACKOFF` | 2.0 | Initial backoff delay (seconds) |
| `SEARXNG_TIMEOUT` | 30 | Request timeout (seconds) |
| `SEARXNG_LANGUAGE` | en | Search language (en, pt-BR, es, fr) |
| `SEARXNG_CACHE` | 1 | Enable persistent cache (0/1) |
| `SEARXNG_CACHE_TTL` | 604800 | Cache TTL (seconds, default 7 days) |
| `SEARXNG_CRAWL` | 0 | Enable Crawl4AI content extraction |

### Using Public SearXNG Instances

By default, the system uses these public instances:
- https://searx.be
- https://search.bus-hit.me
- https://searx.tiekoetter.com

**Or run your own local instance** for best performance and privacy:

```bash
docker compose up -d  # Starts at http://localhost:8080
```

## 🛡️ IP Ban Prevention

SearXNG + Crawl4AI includes **7 safeguards** to prevent IP bans:

1. **Token Bucket Rate Limiting**: Controls request frequency (2 req/sec default)
2. **Minimum Delay**: Enforced 1-second gap between requests
3. **Exponential Backoff**: Automatic retry with increasing delays
4. **Random Jitter**: Randomizes timing to avoid detection patterns
5. **User-Agent Rotation**: Cycles through realistic browser headers
6. **Instance Failover**: Automatically switches between SearXNG instances
7. **Persistent Cache**: DuckDB cache reduces redundant requests

### Recommended Settings

```bash
# Conservative (avoids bans, slower)
SEARXNG_RATE_LIMIT=1.0
SEARXNG_MIN_DELAY=2.0

# Balanced (default)
SEARXNG_RATE_LIMIT=2.0
SEARXNG_MIN_DELAY=1.0

# Aggressive (faster, higher ban risk)
SEARXNG_RATE_LIMIT=5.0
SEARXNG_MIN_DELAY=0.5
```

## 📊 How It Works

```
┌─────────────────┐
│  Your Query     │
└────────┬────────┘
         │
         v
┌─────────────────┐       ┌──────────────────┐
│  SearXNG        │──────>│  Search Engines  │
│  (Meta-search)  │<──────│  (Google, Bing)  │
└────────┬────────┘       └──────────────────┘
         │
         │ Returns URLs
         v
┌─────────────────┐       ┌──────────────────┐
│  Crawl4AI       │──────>│  Target Websites │
│  (Web Crawler)  │<──────│  (Extract Clean) │
└────────┬────────┘       └──────────────────┘
         │
         │ Clean Content
         v
┌─────────────────┐
│  Your App       │
└─────────────────┘
```

### Search Flow

1. **Query Construction**: Builds search query with product identifiers
2. **SearXNG Search**: Queries metasearch engine (anonymized)
3. **URL Collection**: Extracts top N result URLs
4. **Optional Crawling**: Crawl4AI fetches full page content
5. **Content Extraction**: Returns clean markdown (no ads/nav)
6. **Caching**: Stores results in DuckDB for reuse

## 🔧 Advanced Usage

### Local SearXNG Instance

For maximum control and performance, run your own instance:

```yaml
# docker-compose.yml (already created)
version: '3.8'

services:
  searxng:
    image: searxng/searxng:latest
    ports:
      - "8080:8080"
    volumes:
      - ./searxng:/etc/searxng:rw
    environment:
      - BASE_URL=http://localhost:8080/
```

### Custom SearXNG Configuration

After first run, edit `searxng/settings.yml`:

```yaml
# Enable JSON format (required!)
search:
  formats:
    - html
    - json  # <-- REQUIRED

# Configure search engines
engines:
  - name: google
    weight: 1.0
    disabled: false
  
  - name: duckduckgo
    weight: 0.8
    disabled: false
```

### Enable Full Content Crawling

Set `SEARXNG_CRAWL=1` to use Crawl4AI for extracting full page content:

```bash
# .env.local
SEARXNG_CRAWL=1  # Enables Crawl4AI (slower but more content)
```

**Trade-offs:**
- ✅ More complete/accurate content
- ✅ Better context for LLM
- ❌ Slower (headless browser)
- ❌ Higher memory usage

## 🆚 Comparison with Other Providers

### vs Tavily (Removed)
- **Cost**: Tavily = $0.01/search, SearXNG = Free
- **Speed**: Tavily faster, SearXNG good enough
- **Privacy**: SearXNG wins (no data sent externally)
- **Setup**: Tavily easier (just API key), SearXNG requires Docker

### vs Gemini/Grok
These are still available as alternatives:

```bash
# Use Gemini instead
ONLINE_SEARCH_PROVIDER=gemini
GOOGLE_API_KEY=your_key_here

# Use Grok instead
ONLINE_SEARCH_PROVIDER=grok
GROK_API_KEY=your_key_here
```

## 🐛 Troubleshooting

### SearXNG Not Starting

```bash
# Check Docker status
docker ps

# View logs
docker compose logs -f searxng

# Restart
docker compose restart searxng
```

### JSON Format Not Available

```bash
# Ensure JSON is enabled in settings
grep -A 3 "formats:" searxng/settings.yml

# Should see:
#   formats:
#     - html
#     - json

# If missing, run setup script again
./setup_searxng.sh
```

### Crawl4AI Errors

```bash
# Reinstall browser dependencies
crawl4ai-setup

# Test manually
python -c "from crawl4ai import AsyncWebCrawler; print('OK')"
```

### Rate Limiting / IP Bans

If you see 429 errors:

```bash
# Slow down requests
SEARXNG_RATE_LIMIT=1.0
SEARXNG_MIN_DELAY=2.0

# Use different engines in searxng/settings.yml
# Enable DuckDuckGo, disable Google temporarily
```

## 📚 Additional Resources

- [SearXNG Documentation](https://docs.searxng.org/)
- [SearXNG Public Instances](https://searx.space/)
- [Crawl4AI Documentation](https://crawl4ai.com/docs)
- [Original Tutorial Video](https://www.youtube.com/watch?v=VdLiU3v_jXg)

## 🎯 Performance Tips

1. **Use Local Instance**: Run SearXNG locally for best speed
2. **Enable Caching**: Keep `SEARXNG_CACHE=1` (enabled by default)
3. **Adjust Rate Limits**: Balance speed vs ban risk
4. **Disable Crawling**: Set `SEARXNG_CRAWL=0` for faster (but less complete) results
5. **Multiple Instances**: Configure fallback instances in `SEARXNG_INSTANCES`

## ✅ Production Checklist

- [ ] SearXNG running (`docker compose up -d`)
- [ ] JSON format enabled (`searxng/settings.yml`)
- [ ] Crawl4AI installed (`pip install crawl4ai`)
- [ ] Browser dependencies setup (`crawl4ai-setup`)
- [ ] Test search endpoint (`curl http://localhost:8080/search?q=test&format=json`)
- [ ] Configure rate limits (recommended: 2.0 req/sec)
- [ ] Enable caching (recommended: SEARXNG_CACHE=1)

## 🤝 Contributing

If you find issues or have improvements:
1. Check existing issues
2. Create detailed bug report with logs
3. Suggest configuration improvements

---

**Note**: Tavily API support has been removed in favor of this open-source solution. If you need commercial-grade search with guaranteed uptime, consider using Gemini or Grok as alternatives.
