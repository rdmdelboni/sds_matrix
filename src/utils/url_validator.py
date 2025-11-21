"""URL validation utilities for source citation checking."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from ..utils.config import STRICT_SOURCE_VALIDATION, WEB_FETCH_TIMEOUT_SECONDS
from ..utils.logger import logger

def is_valid_url_format(url: str) -> bool:
    """Check if a string has valid URL format.
    
    Args:
        url: URL string to validate
        
    Returns:
        True if URL has valid format, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    # Basic URL pattern check
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    
    if not url_pattern.match(url):
        return False
    
    # Parse URL to check components
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:  # noqa: BLE001
        return False

def is_reachable_url(url: str, timeout: float | None = None) -> bool:
    """Check if a URL is reachable via HEAD request.
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds (defaults to WEB_FETCH_TIMEOUT_SECONDS)
        
    Returns:
        True if URL returns successful status code, False otherwise
    """
    if not is_valid_url_format(url):
        return False
    
    if timeout is None:
        timeout = WEB_FETCH_TIMEOUT_SECONDS
    
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.head(url)
            # Accept 2xx and 3xx status codes
            return 200 <= response.status_code < 400
    except Exception as exc:  # noqa: BLE001
        logger.debug("URL reachability check failed for %s: %s", url, exc)
        return False

def validate_source_urls(
    source_urls: list[str] | None, strict: bool | None = None
) -> tuple[bool, str]:
    """Validate source URLs according to configured strictness.
    
    Args:
        source_urls: list of source URLs to validate
        strict: Whether to enforce strict validation (defaults to STRICT_SOURCE_VALIDATION)
        
    Returns:
        tuple of (is_valid, error_message)
    """
    if strict is None:
        strict = STRICT_SOURCE_VALIDATION
    
    # If not strict mode, just check format
    if not strict:
        if not source_urls:
            return True, ""
        
        # Check format only
        invalid_urls = [url for url in source_urls if not is_valid_url_format(url)]
        if invalid_urls:
            return False, f"URLs com formato invalido: {', '.join(invalid_urls[:3])}"
        return True, ""
    
    # Strict mode: require at least one URL and verify reachability
    if not source_urls or len(source_urls) == 0:
        return False, "Fonte obrigatoria: nenhuma URL fornecida"
    
    # Check format
    invalid_urls = [url for url in source_urls if not is_valid_url_format(url)]
    if invalid_urls:
        return False, f"URLs com formato invalido: {', '.join(invalid_urls[:3])}"
    
    # Check reachability of at least one URL
    reachable_urls = [url for url in source_urls if is_reachable_url(url)]
    if not reachable_urls:
        return (
            False,
            f"Nenhuma URL alcancavel entre: {', '.join(source_urls[:3])}",
        )
    
    logger.debug(
        "Source validation passed: %d/%d URLs reachable",
        len(reachable_urls),
        len(source_urls),
    )
    return True, ""
