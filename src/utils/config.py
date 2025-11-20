"""Global configuration helpers.

This module centralizes configuration and filesystem locations. It now prefers
storing application data under a user-writable directory (e.g. %APPDATA% on
Windows) when the application is installed or running as a frozen EXE.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    # Provide accurate type information to the type checker.
    from dotenv import load_dotenv as _load_dotenv  # type: ignore
else:
    try:
        from dotenv import load_dotenv as _load_dotenv
    except ImportError:  # noqa: F401 - fallback when dependency missing
        def _load_dotenv(*_args: object, **_kwargs: object) -> bool:
            """Fallback no-op when python-dotenv is not installed."""
            return False

# Ensure environment variables from .env are available early.
# Load .env first, then .env.local to allow local overrides (e.g., API keys)
_load_dotenv()
# Allow .env.local to override values from .env for developer-specific settings
_load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env.local",
    override=True,
)

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent.parent

def _default_data_root() -> Path:
    """Choose a user-writable data directory.

    Priority:
    1) FDS_DATA_DIR env var, if set
    2) On Windows: %APPDATA%/FDS Reader
       Else: ~/.local/share/fds_reader
    3) Fallback to repo-local ./data (useful during development)
    """
    # 1) explicit override
    override = os.getenv("FDS_DATA_DIR")
    if override:
        return Path(override)

    # Detect frozen builds or site-packages install
    is_frozen = bool(getattr(sys, "frozen", False))
    base_str = str(BASE_DIR).lower()
    in_site_packages = any(
        name in base_str for name in ("site-packages", "dist-packages")
    )
    base_writable = os.access(BASE_DIR, os.W_OK)

    # 2) prefer user data dir when frozen/installed or base is not writable
    if is_frozen or in_site_packages or not base_writable:
        if os.name == "nt":
            appdata = os.getenv("APPDATA")
            if appdata:
                return Path(appdata) / "FDS Reader"
            # Fallback for Windows without APPDATA
            return Path.home() / "AppData" / "Roaming" / "FDS Reader"
        # POSIX fallback
        return Path.home() / ".local" / "share" / "fds_reader"

    # 3) dev default
    return BASE_DIR / "data"

DATA_DIR: Final[Path] = _default_data_root()
LOGS_DIR: Final[Path] = DATA_DIR / "logs"
DUCKDB_FILE: Final[Path] = Path(
    os.getenv("DUCKDB_PATH", DATA_DIR / "duckdb" / "extractions.db")
)
SQLITE_FILE: Final[Path] = Path(
    os.getenv("SQLITE_PATH", DATA_DIR / "config" / "templates.db")
)
LOG_FILE: Final[Path] = Path(os.getenv("LOG_FILE", LOGS_DIR / "app.log"))
LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO")

def _ensure_directories() -> None:
    """Create expected directories if they do not exist."""
    for directory in {
        DATA_DIR,
        DATA_DIR / "duckdb",
        DATA_DIR / "config",
        LOGS_DIR,
    }:
        directory.mkdir(parents=True, exist_ok=True)

_ensure_directories()

LM_STUDIO_CONFIG: Final[dict[str, object]] = {
    # Defaults point to Ollama's OpenAI-compatible endpoint/model.
    "base_url": os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:11434/v1"),
    "model": os.getenv("LM_STUDIO_MODEL", "llama3.1:8b"),
    "timeout": int(os.getenv("LM_STUDIO_TIMEOUT", "60")),
    "max_tokens": int(os.getenv("LM_STUDIO_MAX_TOKENS", "2000")),
    "temperature": float(os.getenv("LM_STUDIO_TEMPERATURE", "0.1")),
}

# Gemini (Google Generative Language API) configuration
# To enable online search via Gemini, set GOOGLE_API_KEY in your environment
# Optional overrides:
#   GEMINI_MODEL (default: gemini-2.0-flash)
#   GEMINI_BASE_URL (default: https://generativelanguage.googleapis.com)
GEMINI_CONFIG: Final[dict[str, object]] = {
    "api_key": os.getenv("GOOGLE_API_KEY", ""),
    "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    "base_url": os.getenv(
        "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"
    ),
    "timeout": int(os.getenv("GEMINI_TIMEOUT", "60")),
}

# Grok (xAI API) configuration
# To enable online search via Grok, set GROK_API_KEY in your environment
# Optional overrides:
#   GROK_MODEL (default: grok-beta)
#   GROK_BASE_URL (default: https://api.x.ai/v1)
GROK_CONFIG: Final[dict[str, object]] = {
    "api_key": os.getenv("GROK_API_KEY", ""),
    "model": os.getenv("GROK_MODEL", "grok-beta"),
    "base_url": os.getenv("GROK_BASE_URL", "https://api.x.ai/v1"),
    "timeout": int(os.getenv("GROK_TIMEOUT", "60")),
}

# SearXNG + Crawl4AI configuration (open-source alternative - no API key required!)
# No API key required; uses public SearXNG instances by default
# Configuration:
#   SEARXNG_INSTANCES: Comma-separated list of SearXNG URLs
#   SEARXNG_RATE_LIMIT: Requests per second (default: 2.0)
#   SEARXNG_BURST_LIMIT: Max burst tokens (default: 5.0)
#   SEARXNG_MIN_DELAY: Minimum seconds between requests (default: 1.0)
#   SEARXNG_MAX_RETRIES: Max retry attempts (default: 3)
#   SEARXNG_BACKOFF: Initial backoff in seconds (default: 2.0)
#   SEARXNG_TIMEOUT: Request timeout in seconds (default: 30)
#   SEARXNG_LANGUAGE: Search language (default: en; examples: pt-BR, es, fr)
#   SEARXNG_CACHE: Enable persistent cache (default: 1)
#   SEARXNG_CACHE_TTL: Cache TTL in seconds (default: 7 days)
#   SEARXNG_CRAWL: Enable Crawl4AI for content extraction (default: 0)
SEARXNG_CONFIG: Final[dict[str, object]] = {
    "instances": os.getenv(
        "SEARXNG_INSTANCES",
        "https://searx.be,https://search.bus-hit.me,https://searx.tiekoetter.com",
    ),
    "rate_limit": float(os.getenv("SEARXNG_RATE_LIMIT", "2.0")),
    "burst_limit": float(os.getenv("SEARXNG_BURST_LIMIT", "5.0")),
    "min_delay": float(os.getenv("SEARXNG_MIN_DELAY", "1.0")),
    "max_retries": int(os.getenv("SEARXNG_MAX_RETRIES", "3")),
    "backoff": float(os.getenv("SEARXNG_BACKOFF", "2.0")),
    "timeout": int(os.getenv("SEARXNG_TIMEOUT", "30")),
    "cache_enabled": os.getenv("SEARXNG_CACHE", "1") in {"1", "true", "True"},
    "cache_ttl": int(os.getenv("SEARXNG_CACHE_TTL", str(7 * 24 * 3600))),
    "crawl_enabled": os.getenv("SEARXNG_CRAWL", "0") in {"1", "true", "True"},
}

# Provider for online search. Options: "searxng", "grok", "gemini", "lmstudio".
# Default: SearXNG (no API key needed - free and open source!)
ONLINE_SEARCH_PROVIDER: Final[str] = os.getenv(
    "ONLINE_SEARCH_PROVIDER",
    "searxng",  # SearXNG as default (no API key needed)
)

MAX_WORKERS: Final[int] = int(os.getenv("MAX_WORKERS", "2"))
CHUNK_SIZE: Final[int] = int(os.getenv("CHUNK_SIZE", "4000"))
MAX_FILE_SIZE_MB: Final[int] = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

# ----------------------- Retrieval / Enrichment ----------------------- #
# Centralized tunables for multi-pass enrichment & retrieval logic. All may be
# overridden via environment variables. These defaults are conservative so they
# do not introduce heavy network / token usage until explicitly increased.

# Maximum number of iterative enrichment passes (heuristics/local, web, refine)
ONLINE_SEARCH_MAX_PASSES: Final[int] = int(
    os.getenv("ONLINE_SEARCH_MAX_PASSES", "2")
)

# Top-K chunks to retrieve from the local VectorStore per field query
RETRIEVAL_TOP_K: Final[int] = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# Confidence thresholds guiding pass transitions
#  - LOW: below this triggers web retrieval
#  - MID: below this after web retrieval triggers refinement
CONFIDENCE_THRESHOLD_LOW: Final[float] = float(
    os.getenv("CONFIDENCE_THRESHOLD_LOW", "0.6")
)
CONFIDENCE_THRESHOLD_MID: Final[float] = float(
    os.getenv("CONFIDENCE_THRESHOLD_MID", "0.75")
)

# Targeted refinement rounds (vector + LLM) after initial passes
REFINEMENT_MAX_ROUNDS: Final[int] = int(
    os.getenv("REFINEMENT_MAX_ROUNDS", "2")
)

# Crawling / page fetch limits
MAX_CRAWL_PAGES_PER_FIELD: Final[int] = int(
    os.getenv("MAX_CRAWL_PAGES_PER_FIELD", "2")
)
CRAWL_TEXT_MAX_CHARS: Final[int] = int(
    os.getenv("CRAWL_TEXT_MAX_CHARS", "5000")
)

# ────────────── Crawl4AI IP Ban Prevention Safeguards ──────────────
# These settings respect robots.txt, add delays, rotate user-agents, and
# prevent aggressive crawling that could trigger IP bans.
#
# Configuration:
#   CRAWL4AI_ENABLED: Enable Crawl4AI for page extraction (default: 0)
#   CRAWL4AI_MIN_DELAY: Minimum seconds between crawl requests (default: 2.0)
#   CRAWL4AI_MAX_CONCURRENT: Max concurrent crawl tasks (default: 1)
#   CRAWL4AI_TIMEOUT: Request timeout in seconds (default: 30)
#   CRAWL4AI_BROWSER_TYPE: Browser type - chromium/firefox (default: chromium)
#   CRAWL4AI_RESPECT_ROBOTS: Respect robots.txt (default: 1 - YES)
#   CRAWL4AI_USER_AGENT_ROTATION: Rotate user agents (default: 1 - YES)
#   CRAWL4AI_PROXY: Optional proxy URL for requests
#
CRAWL4AI_ENABLED: Final[bool] = os.getenv("CRAWL4AI_ENABLED", "0") in {
    "1",
    "true",
    "True",
}
CRAWL4AI_MIN_DELAY: Final[float] = float(
    os.getenv("CRAWL4AI_MIN_DELAY", "2.0")
)  # Higher than SearXNG to be respectful
CRAWL4AI_MAX_CONCURRENT: Final[int] = int(
    os.getenv("CRAWL4AI_MAX_CONCURRENT", "1")
)  # Sequential by default to avoid hammering
CRAWL4AI_TIMEOUT: Final[int] = int(os.getenv("CRAWL4AI_TIMEOUT", "30"))
CRAWL4AI_BROWSER_TYPE: Final[str] = os.getenv(
    "CRAWL4AI_BROWSER_TYPE", "chromium"
)
CRAWL4AI_RESPECT_ROBOTS: Final[bool] = os.getenv(
    "CRAWL4AI_RESPECT_ROBOTS", "1"
) in {"1", "true", "True"}
CRAWL4AI_USER_AGENT_ROTATION: Final[bool] = os.getenv(
    "CRAWL4AI_USER_AGENT_ROTATION", "1"
) in {"1", "true", "True"}
CRAWL4AI_PROXY: Final[str | None] = os.getenv("CRAWL4AI_PROXY", None)

# Maximum retries for external search/page fetch operations
ONLINE_SEARCH_MAX_RETRIES: Final[int] = int(
    os.getenv("ONLINE_SEARCH_MAX_RETRIES", "3")
)

# Base delay (seconds) for exponential backoff with jitter on external calls
ONLINE_SEARCH_BACKOFF_BASE: Final[float] = float(
    os.getenv("ONLINE_SEARCH_BACKOFF_BASE", "0.5")
)

# Field-level retry attempts (per missing field) wrapping the lower-level
# provider retries. This allows re-running the entire query variant set when
# all variants return weak/no snippets. Separates transport/API retries from
# semantic retry logic.
FIELD_SEARCH_MAX_ATTEMPTS: Final[int] = int(
    os.getenv("FIELD_SEARCH_MAX_ATTEMPTS", "3")
)

# Base backoff for field-level attempts (multiplied exponentially and with
# jitter). If unset defaults to ONLINE_SEARCH_BACKOFF_BASE to keep behavior
# consistent. Use env FIELD_SEARCH_BACKOFF_BASE to override independently.
FIELD_SEARCH_BACKOFF_BASE: Final[float] = float(
    os.getenv(
        "FIELD_SEARCH_BACKOFF_BASE",
        os.getenv("ONLINE_SEARCH_BACKOFF_BASE", "0.5"),
    )
)

# Timeout (seconds) for individual HTTP fetches of search result pages
WEB_FETCH_TIMEOUT_SECONDS: Final[int] = int(
    os.getenv("WEB_FETCH_TIMEOUT_SECONDS", "20")
)

# Enable / disable strict source validation (HEAD check). When disabled the
# pipeline accepts source URLs returned by the LLM without verification.
STRICT_SOURCE_VALIDATION: Final[bool] = os.getenv(
    "STRICT_SOURCE_VALIDATION", "1"
) in {"1", "true", "True"}

# Directory for caching web pages / search results (overridable)
WEB_CACHE_DIR: Final[Path] = Path(
    os.getenv("WEB_CACHE_DIR", DATA_DIR / "web_cache")
)
WEB_CACHE_DIR.mkdir(parents=True, exist_ok=True)

TESSERACT_PATH: Final[str] = os.getenv("TESSERACT_PATH", "tesseract")

SUPPORTED_FORMATS: Final[dict[str, str]] = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".html": "HTML",
    ".htm": "HTML",
}

FDS_SECTIONS: Final[dict[int, str]] = {
    1: "Identificacao",
    2: "Identificacao de perigos",
    3: "Composicao e informacoes sobre os ingredientes",
    4: "Medidas de primeiros-socorros",
    5: "Medidas de combate a incendio",
    6: "Medidas de controle para derramamento ou vazamento",
    7: "Manuseio e armazenamento",
    8: "Controle de exposicao e protecao individual",
    9: "Propriedades fisicas e quimicas",
    10: "Estabilidade e reatividade",
    11: "Informacoes toxicologicas",
    12: "Informacoes ecologicas",
    13: "Consideracoes sobre destinacao final",
    14: "Informacoes sobre transporte",
    15: "Informacoes sobre regulamentacoes",
    16: "Outras informacoes",
}
