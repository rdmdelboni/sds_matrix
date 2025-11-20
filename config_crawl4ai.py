"""
Configuration loader for automatic Crawl4AI setup
Place this in your project root or import from main.py
"""

import os
from pathlib import Path


def load_crawl4ai_config(mode: str = "balanced") -> None:
    """
    Automatically configure Crawl4AI environment variables.
    
    Args:
        mode: Configuration profile to use
              - "conservative": Safe, slower (IP protection priority)
              - "balanced": Default, recommended (good balance)
              - "aggressive": Fast, higher risk (use with caution)
              - "custom": Use values from .env.crawl4ai file
    
    Examples:
        # In your main.py or startup script:
        from config_crawl4ai import load_crawl4ai_config
        load_crawl4ai_config(mode="balanced")
    """
    
    configs = {
        "conservative": {
            "CRAWL4AI_ENABLED": "1",
            "CRAWL4AI_MIN_DELAY": "3.0",
            "MAX_CRAWL_PAGES_PER_FIELD": "1",
            "CRAWL_TEXT_MAX_CHARS": "5000",
            "FIELD_SEARCH_MAX_ATTEMPTS": "2",
            "FIELD_SEARCH_BACKOFF_BASE": "0.5",
            "SEARXNG_MIN_DELAY": "1.5",
        },
        "balanced": {
            "CRAWL4AI_ENABLED": "1",
            "CRAWL4AI_MIN_DELAY": "1.0",
            "MAX_CRAWL_PAGES_PER_FIELD": "2",
            "CRAWL_TEXT_MAX_CHARS": "5000",
            "FIELD_SEARCH_MAX_ATTEMPTS": "3",
            "FIELD_SEARCH_BACKOFF_BASE": "0.5",
            "SEARXNG_MIN_DELAY": "1.0",
        },
        "aggressive": {
            "CRAWL4AI_ENABLED": "1",
            "CRAWL4AI_MIN_DELAY": "0.5",
            "MAX_CRAWL_PAGES_PER_FIELD": "3",
            "CRAWL_TEXT_MAX_CHARS": "10000",
            "FIELD_SEARCH_MAX_ATTEMPTS": "5",
            "FIELD_SEARCH_BACKOFF_BASE": "0.3",
            "SEARXNG_MIN_DELAY": "0.5",
        },
    }
    
    # Common settings for all modes
    common_settings = {
        "CRAWL4AI_BROWSER_TYPE": "chromium",
        "CRAWL4AI_HEADLESS": "true",
        "CRAWL4AI_CACHE_ENABLED": "true",
        "SEARXNG_CACHE": "1",
        "SEARXNG_CRAWL": "1",
    }
    
    # Select configuration
    if mode.lower() == "custom":
        # Load from .env.crawl4ai file
        env_file = Path(".env.crawl4ai")
        if env_file.exists():
            _load_env_file(env_file)
            print(f"✅ Crawl4AI config loaded from {env_file}")
            return
        else:
            print("⚠️  .env.crawl4ai not found, using balanced mode")
            mode = "balanced"
    
    selected_config = configs.get(mode.lower(), configs["balanced"])
    
    # Apply all settings
    settings = {**common_settings, **selected_config}
    for key, value in settings.items():
        os.environ[key] = value
    
    print(f"✅ Crawl4AI configured in {mode.upper()} mode")
    print(f"   • CRAWL4AI_ENABLED: {os.environ.get('CRAWL4AI_ENABLED')}")
    print(f"   • CRAWL4AI_MIN_DELAY: {os.environ.get('CRAWL4AI_MIN_DELAY')}s")
    max_crawl = os.environ.get('MAX_CRAWL_PAGES_PER_FIELD')
    print(f"   • MAX_CRAWL_PAGES_PER_FIELD: {max_crawl}")
    max_attempts = os.environ.get('FIELD_SEARCH_MAX_ATTEMPTS')
    print(f"   • FIELD_SEARCH_MAX_ATTEMPTS: {max_attempts}")
    print("   • IP Ban Protection: ACTIVE")


def _load_env_file(env_file: Path) -> None:
    """Load environment variables from .env file."""
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Parse KEY=value
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                os.environ[key] = value


def get_config() -> dict:
    """
    Get current Crawl4AI configuration as dictionary.
    
    Returns:
        Dictionary with all Crawl4AI-related environment variables
    """
    keys = [
        "CRAWL4AI_ENABLED",
        "CRAWL4AI_MIN_DELAY",
        "CRAWL4AI_BROWSER_TYPE",
        "CRAWL4AI_HEADLESS",
        "CRAWL4AI_CACHE_ENABLED",
        "MAX_CRAWL_PAGES_PER_FIELD",
        "CRAWL_TEXT_MAX_CHARS",
        "FIELD_SEARCH_MAX_ATTEMPTS",
        "FIELD_SEARCH_BACKOFF_BASE",
        "SEARXNG_MIN_DELAY",
        "SEARXNG_CACHE",
        "SEARXNG_CRAWL",
    ]
    return {key: os.environ.get(key, "NOT SET") for key in keys}


def print_config() -> None:
    """Pretty print current Crawl4AI configuration."""
    config = get_config()
    print("\n" + "=" * 60)
    print("CRAWL4AI CONFIGURATION")
    print("=" * 60)
    for key, value in config.items():
        status = "✅" if value != "NOT SET" else "⚠️ "
        print(f"{status} {key:<35} = {value}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Example usage
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "balanced"
    load_crawl4ai_config(mode=mode)
    print_config()
