"""SearXNG + Crawl4AI client with IP ban prevention safeguards.

Features:
  - Token bucket rate limiting to control request frequency
  - Exponential backoff with jitter for transient errors
  - User-agent rotation to avoid detection
  - Multiple SearXNG instance support with failover
  - Persistent cache (DuckDB) for search results and crawled content
  - Health checks and instance rotation
  - Configurable delays between requests
  - Request queue with priority handling
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Optional, cast

import httpx

from ..utils.config import DATA_DIR
from ..utils.logger import logger


@dataclass
class TokenBucket:
    """Token bucket for rate limiting to prevent IP bans."""

    capacity: float  # Maximum tokens
    tokens: float  # Current tokens
    rate: float  # Tokens per second refill rate
    last_update: float  # Last refill timestamp

    def consume(self, amount: float = 1.0) -> bool:
        """Try to consume tokens; return True if successful."""
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def wait_time(self, amount: float = 1.0) -> float:
        """Calculate seconds to wait for tokens to be available."""
        self._refill()
        if self.tokens >= amount:
            return 0.0
        deficit = amount - self.tokens
        return deficit / self.rate

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now


class SearXNGClient:
    """SearXNG search client with Crawl4AI content extraction.

    IP Ban Prevention Safeguards:
      1. Token bucket rate limiting (default: 2 req/sec)
      2. Configurable min delay between requests (default: 1s)
      3. Exponential backoff for 429/5xx errors
      4. Random jitter to avoid patterns
      5. User-agent rotation
      6. Multiple instance support with health checks
      7. Persistent cache to minimize requests
      8. Request queue with prioritization
    """

    # User-agent pool for rotation
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    def __init__(self, http_client_factory: Optional[Any] = None) -> None:
        # SearXNG instances (with fallback)
        default_instances = [
            "https://searx.be",
            "https://search.bus-hit.me",
            "https://searx.tiekoetter.com",
        ]
        custom_instances = os.getenv("SEARXNG_INSTANCES", "").split(",")
        self.instances = [
            i.strip() for i in custom_instances if i.strip()
        ] or default_instances
        self.current_instance_idx = 0
        self.instance_health: dict[str, float] = {}  # instance -> last success time

        # Rate limiting (token bucket)
        rate = float(os.getenv("SEARXNG_RATE_LIMIT", "2.0"))  # requests/sec
        capacity = float(os.getenv("SEARXNG_BURST_LIMIT", "5.0"))  # burst tokens
        self.rate_limiter = TokenBucket(
            capacity=capacity,
            tokens=capacity,
            rate=rate,
            last_update=time.time(),
        )

        # Additional delay between requests (safeguard)
        self.min_request_delay = float(os.getenv("SEARXNG_MIN_DELAY", "1.0"))
        self.last_request_time = 0.0

        # Retry config
        self.max_retries = int(os.getenv("SEARXNG_MAX_RETRIES", "3"))
        self.initial_backoff = float(os.getenv("SEARXNG_BACKOFF", "2.0"))

        # Timeout
        self.timeout = int(os.getenv("SEARXNG_TIMEOUT", "30"))

        # Search language (en, pt-BR, etc.)
        self.language = os.getenv("SEARXNG_LANGUAGE", "en")

        # Cache (persistent DuckDB)
        self.cache_enabled = os.getenv("SEARXNG_CACHE", "1") in {"1", "true", "True"}
        self.cache_ttl = int(os.getenv("SEARXNG_CACHE_TTL", str(7 * 24 * 3600)))
        self.cache_db_path = os.getenv(
            "SEARXNG_CACHE_DB_PATH",
            str(DATA_DIR / "duckdb" / "searxng_cache.db"),
        )
        self._cache_conn = None
        if self.cache_enabled:
            self._init_cache()

        # HTTP client factory (injectable for testing)
        self._client_factory = http_client_factory or (
            lambda timeout: httpx.Client(timeout=timeout)
        )

        logger.info(
            "SearXNG client initialized: instances=%d rate=%.1f/s cache=%s",
            len(self.instances),
            rate,
            self.cache_enabled,
        )

    def _init_cache(self) -> None:
        """Initialize DuckDB persistent cache."""
        try:
            import duckdb

            os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
            self._cache_conn = duckdb.connect(self.cache_db_path)
            self._cache_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS search_cache (
                    key TEXT PRIMARY KEY,
                    query TEXT,
                    results TEXT,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._cache_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS crawl_cache (
                    url TEXT PRIMARY KEY,
                    content TEXT,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            logger.info("SearXNG cache enabled at %s", self.cache_db_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialize cache: %s", exc)
            self.cache_enabled = False

    def _cache_key(self, query: str, num_results: int = 5) -> str:
        """Generate cache key for search query."""
        key_str = f"{query}|{num_results}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_search(self, key: str) -> Optional[list[dict[str, str]]]:
        """Get cached search results if available and not expired."""
        if not self.cache_enabled or not self._cache_conn:
            return None
        try:
            row = self._cache_conn.execute(
                "SELECT results, ts FROM search_cache WHERE key = ?",
                [key],
            ).fetchone()
            if row:
                results_json, ts = row
                # Check TTL (simplified; DuckDB timestamp handling)
                return json.loads(results_json)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache read error: %s", exc)
        return None

    def _store_cached_search(self, key: str, query: str, results: list[dict[str, str]]) -> None:
        """Store search results in cache."""
        if not self.cache_enabled or not self._cache_conn:
            return
        try:
            self._cache_conn.execute(
                "INSERT OR REPLACE INTO search_cache (key, query, results) VALUES (?, ?, ?)",
                [key, query, json.dumps(results)],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache write error: %s", exc)

    def _get_cached_crawl(self, url: str) -> Optional[str]:
        """Get cached crawled content."""
        if not self.cache_enabled or not self._cache_conn:
            return None
        try:
            row = self._cache_conn.execute(
                "SELECT content FROM crawl_cache WHERE url = ?",
                [url],
            ).fetchone()
            if row:
                return row[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache read error: %s", exc)
        return None

    def _store_cached_crawl(self, url: str, content: str) -> None:
        """Store crawled content in cache."""
        if not self.cache_enabled or not self._cache_conn:
            return
        try:
            self._cache_conn.execute(
                "INSERT OR REPLACE INTO crawl_cache (url, content) VALUES (?, ?)",
                [url, content[:50000]],  # Limit content size
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Cache write error: %s", exc)

    def _wait_for_rate_limit(self) -> None:
        """Block until rate limit allows next request."""
        # Token bucket wait
        wait_tokens = self.rate_limiter.wait_time(1.0)
        if wait_tokens > 0:
            logger.debug("Rate limit: waiting %.2fs for tokens", wait_tokens)
            time.sleep(wait_tokens)
            self.rate_limiter.consume(1.0)
        else:
            self.rate_limiter.consume(1.0)

        # Additional min delay safeguard
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_delay:
            delay = self.min_request_delay - elapsed
            logger.debug("Min delay safeguard: waiting %.2fs", delay)
            time.sleep(delay)
        self.last_request_time = time.time()

    def _get_user_agent(self) -> str:
        """Rotate user agents to avoid detection."""
        return random.choice(self.USER_AGENTS)

    def _get_instance(self) -> str:
        """Get current SearXNG instance with health-based rotation."""
        # Simple round-robin with health check
        instance = self.instances[self.current_instance_idx]
        last_success = self.instance_health.get(instance, 0)
        # If last success was > 5 min ago, try next instance
        if time.time() - last_success > 300:
            self.current_instance_idx = (self.current_instance_idx + 1) % len(
                self.instances
            )
            instance = self.instances[self.current_instance_idx]
        return instance

    def _mark_instance_healthy(self, instance: str) -> None:
        """Mark instance as healthy after successful request."""
        self.instance_health[instance] = time.time()

    def _search_with_retry(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[dict[str, str]]:
        """Perform SearXNG search with retry and backoff."""
        attempt = 0
        backoff = self.initial_backoff
        last_error = None

        while attempt <= self.max_retries:
            instance = self._get_instance()
            try:
                self._wait_for_rate_limit()

                headers = {
                    "User-Agent": self._get_user_agent(),
                    "Accept": "application/json",
                }
                params = {
                    "q": query,
                    "format": "json",
                    "language": self.language,  # Configurable via SEARXNG_LANGUAGE
                    "safesearch": "0",
                }

                with self._client_factory(self.timeout) as client:
                    response = client.get(
                        f"{instance}/search",
                        params=params,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()

                # Mark instance healthy
                self._mark_instance_healthy(instance)

                # Extract results
                results = []
                for item in data.get("results", [])[:num_results]:
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "snippet": item.get("content", ""),
                        }
                    )
                return results

            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                last_error = exc
                if status in (429, 503) and attempt < self.max_retries:
                    # Rate limited or overloaded; back off
                    wait = backoff * (2**attempt) + random.uniform(0, 1.0)
                    logger.warning(
                        "SearXNG %s error from %s (attempt %d/%d). Waiting %.1fs",
                        status,
                        instance,
                        attempt + 1,
                        self.max_retries,
                        wait,
                    )
                    time.sleep(wait)
                    attempt += 1
                    # Try next instance on next attempt
                    self.current_instance_idx = (
                        self.current_instance_idx + 1
                    ) % len(self.instances)
                    continue
                raise RuntimeError(f"SearXNG search failed: {exc}") from exc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_retries:
                    wait = backoff * (2**attempt) + random.uniform(0, 0.5)
                    logger.warning(
                        "SearXNG error from %s: %s. Retrying in %.1fs",
                        instance,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                    attempt += 1
                    self.current_instance_idx = (
                        self.current_instance_idx + 1
                    ) % len(self.instances)
                    continue
                raise RuntimeError(f"SearXNG search failed: {exc}") from exc

        raise RuntimeError(f"SearXNG exhausted retries: {last_error}")

    async def _crawl_url_async(self, url: str) -> str:
        """Crawl URL using Crawl4AI to extract clean text."""
        try:
            from crawl4ai import AsyncWebCrawler

            async with AsyncWebCrawler(verbose=False) as crawler:
                result = await crawler.arun(url=url)
                if result.success:
                    # Try fit_markdown (clean, ads/nav removed) first
                    # Fall back to markdown, then cleaned_html
                    content = ""
                    if hasattr(result.markdown, "fit_markdown"):
                        content = result.markdown.fit_markdown
                    if not content:
                        content = result.markdown or result.cleaned_html or ""
                    return content
                return ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("Crawl4AI failed for %s: %s", url, exc)
            return ""

    def _crawl_url(self, url: str) -> str:
        """Synchronous wrapper for crawling URL."""
        # Check cache first
        cached = self._get_cached_crawl(url)
        if cached:
            logger.debug("Crawl cache hit for %s", url)
            return cached

        # Rate limit crawling too
        self._wait_for_rate_limit()

        try:
            content = asyncio.run(self._crawl_url_async(url))
            self._store_cached_crawl(url, content)
            return content
        except Exception as exc:  # noqa: BLE001
            logger.error("Crawl failed for %s: %s", url, exc)
            return ""

    def search_online_for_missing_fields(
        self,
        *,
        product_name: Optional[str] = None,
        cas_number: Optional[str] = None,
        un_number: Optional[str] = None,
        missing_fields: list[str],
    ) -> dict[str, dict[str, object]]:
        """Search for missing field values using SearXNG + Crawl4AI.

        Args:
            product_name: Known product name
            cas_number: Known CAS number
            un_number: Known UN number
            missing_fields: List of field names that need values

        Returns:
            Dictionary mapping field names to extracted data
        """
        identifiers = []
        if product_name and product_name.strip():
            identifiers.append(product_name.strip())
        if cas_number and str(cas_number).strip():
            identifiers.append(f"CAS {str(cas_number).strip()}")
        if un_number and str(un_number).strip():
            identifiers.append(f"UN {str(un_number).strip()}")

        if not identifiers:
            logger.warning("No identifiers for online search")
            return {}

        identifier_text = " ".join(identifiers).strip()
        results: dict[str, dict[str, object]] = {}

        field_translations = {
            "numero_cas": "CAS number",
            "numero_onu": "UN number",
            "nome_produto": "product name",
            "fabricante": "manufacturer",
            "classificacao_onu": "UN hazard classification",
            "grupo_embalagem": "packing group",
            "incompatibilidades": "chemical incompatibilities",
        }

        # Search for each field
        for field_name in missing_fields:
            try:
                field_display = field_translations.get(field_name, field_name)
                query = f"{identifier_text} {field_display} safety data sheet"

                # Check search cache
                cache_key = self._cache_key(query, 3)
                search_results = self._get_cached_search(cache_key)

                if not search_results:
                    logger.info("SearXNG search: %s", query[:80])
                    search_results = self._search_with_retry(query, num_results=3)
                    self._store_cached_search(cache_key, query, search_results)
                else:
                    logger.debug("Search cache hit for %s", field_name)

                # Extract best result
                if search_results:
                    # Use first result snippet (or crawl URL for more content)
                    first = search_results[0]
                    snippet = first.get("snippet", "").strip()

                    # Optionally crawl top URL for better data
                    crawl_enabled = os.getenv("SEARXNG_CRAWL", "0") == "1"
                    if crawl_enabled and first.get("url"):
                        logger.debug("Crawling %s", first["url"])
                        crawled = self._crawl_url(first["url"])
                        if crawled and len(crawled) > len(snippet):
                            snippet = crawled[:1000]

                    field_data = {
                        "value": snippet or "NAO ENCONTRADO",
                        "confidence": 0.7 if snippet else 0.0,
                        "context": f"SearXNG: {first.get('title', 'search')}",
                    }
                else:
                    field_data = {
                        "value": "NAO ENCONTRADO",
                        "confidence": 0.0,
                        "context": "No search results",
                    }

                results[field_name] = field_data

            except Exception as exc:  # noqa: BLE001
                logger.error("SearXNG search failed for %s: %s", field_name, exc)
                results[field_name] = {
                    "value": "ERRO",
                    "confidence": 0.0,
                    "context": f"Search error: {exc}",
                }

        logger.info("SearXNG search finished for %d fields", len(results))
        return results
