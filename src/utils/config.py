"""Global configuration helpers.

This module centralizes configuration and filesystem locations. It now prefers
storing application data under a user-writable directory (e.g. %APPDATA% on
Windows) when the application is installed or running as a frozen EXE.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, Final
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # noqa: F401 - fallback when dependency missing
    def load_dotenv(*_args, **_kwargs) -> bool:  # type: ignore[override]
        """Fallback no-op when python-dotenv is not installed."""
        return False


# Ensure environment variables from .env are available early.
# Load .env first, then .env.local to allow local overrides (e.g., API keys)
load_dotenv()
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env.local")

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
    in_site_packages = any(name in str(BASE_DIR).lower() for name in ("site-packages", "dist-packages"))
    base_writable = os.access(BASE_DIR, os.W_OK)

    # 2) prefer user data dir when frozen or installed (non-dev), or when base is not writable
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
DUCKDB_FILE: Final[Path] = Path(os.getenv("DUCKDB_PATH", DATA_DIR / "duckdb" / "extractions.db"))
SQLITE_FILE: Final[Path] = Path(os.getenv("SQLITE_PATH", DATA_DIR / "config" / "templates.db"))
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


LM_STUDIO_CONFIG: Final[Dict[str, object]] = {
    # Defaults point to Ollama's OpenAI-compatible endpoint/model; override for LM Studio if desired.
    "base_url": os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:11434/v1"),
    "model": os.getenv("LM_STUDIO_MODEL", "llama3.1:8b"),
    "timeout": int(os.getenv("LM_STUDIO_TIMEOUT", "60")),
    "max_tokens": int(os.getenv("LM_STUDIO_MAX_TOKENS", "2000")),
    "temperature": float(os.getenv("LM_STUDIO_TEMPERATURE", "0.1")),
}

# Gemini (Google Generative Language API) configuration
# To enable online search via Gemini, set GOOGLE_API_KEY in your environment (or .env)
# Optional overrides:
#   GEMINI_MODEL (default: gemini-2.0-flash)
#   GEMINI_BASE_URL (default: https://generativelanguage.googleapis.com)
GEMINI_CONFIG: Final[Dict[str, object]] = {
    "api_key": os.getenv("GOOGLE_API_KEY", ""),
    "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
    "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
    "timeout": int(os.getenv("GEMINI_TIMEOUT", "60")),
}

# Provider for online search. Options: "gemini", "lmstudio".
ONLINE_SEARCH_PROVIDER: Final[str] = os.getenv("ONLINE_SEARCH_PROVIDER", "gemini" if os.getenv("GOOGLE_API_KEY") else "lmstudio")

MAX_WORKERS: Final[int] = int(os.getenv("MAX_WORKERS", "2"))
CHUNK_SIZE: Final[int] = int(os.getenv("CHUNK_SIZE", "4000"))
MAX_FILE_SIZE_MB: Final[int] = int(os.getenv("MAX_FILE_SIZE_MB", "10"))

TESSERACT_PATH: Final[str] = os.getenv("TESSERACT_PATH", "tesseract")

SUPPORTED_FORMATS: Final[Dict[str, str]] = {
    ".pdf": "PDF",
    ".docx": "Word",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".html": "HTML",
    ".htm": "HTML",
}

FDS_SECTIONS: Final[Dict[int, str]] = {
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
