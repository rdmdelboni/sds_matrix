#!/usr/bin/env bash
# IP Ban Prevention Configuration Helper
# This script helps you configure safe rate limiting settings

set -e

echo "🛡️  SearXNG IP Ban Prevention Configuration"
echo "=========================================="
echo ""

# Check if .env.local exists
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local from example..."
    cp .env.local.example .env.local
    echo "✅ Created .env.local"
fi

echo "Current SearXNG Configuration:"
echo "------------------------------"

# Show current settings
if grep -q "SEARXNG_RATE_LIMIT" .env.local 2>/dev/null; then
    echo "📊 Rate Limit: $(grep SEARXNG_RATE_LIMIT .env.local | grep -v '^#' | cut -d'=' -f2)"
else
    echo "📊 Rate Limit: 2.0 req/sec (default)"
fi

if grep -q "SEARXNG_MIN_DELAY" .env.local 2>/dev/null; then
    echo "⏱️  Min Delay: $(grep SEARXNG_MIN_DELAY .env.local | grep -v '^#' | cut -d'=' -f2)s"
else
    echo "⏱️  Min Delay: 1.0s (default)"
fi

if grep -q "SEARXNG_CACHE" .env.local 2>/dev/null; then
    cache_val=$(grep SEARXNG_CACHE .env.local | grep -v '^#' | cut -d'=' -f2)
    if [ "$cache_val" = "1" ]; then
        echo "💾 Cache: Enabled ✅"
    else
        echo "💾 Cache: Disabled ⚠️"
    fi
else
    echo "💾 Cache: Enabled (default) ✅"
fi

echo ""
echo "Select a preset configuration:"
echo "------------------------------"
echo "1) 🐌 Maximum Safety    (1.0 req/sec, 2.0s delay) - Slowest, safest"
echo "2) ⚖️  Balanced         (2.0 req/sec, 1.0s delay) - DEFAULT"
echo "3) 🚀 Aggressive        (5.0 req/sec, 0.5s delay) - Fastest, riskier"
echo "4) 🛠️  Custom           (Enter your own values)"
echo "5) ℹ️  View guide       (Open IP_BAN_PREVENTION.md)"
echo "6) ❌ Cancel"
echo ""
read -p "Choose option [1-6]: " choice

case $choice in
    1)
        echo ""
        echo "Applying Maximum Safety preset..."
        sed -i.bak '/^SEARXNG_RATE_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_MIN_DELAY=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_BURST_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_CACHE=/d' .env.local 2>/dev/null || true
        echo "" >> .env.local
        echo "# === Maximum Safety Preset ===" >> .env.local
        echo "SEARXNG_RATE_LIMIT=1.0" >> .env.local
        echo "SEARXNG_MIN_DELAY=2.0" >> .env.local
        echo "SEARXNG_BURST_LIMIT=2.0" >> .env.local
        echo "SEARXNG_CACHE=1" >> .env.local
        echo "✅ Applied: ~30 searches/min max"
        ;;
    2)
        echo ""
        echo "Applying Balanced preset (default)..."
        sed -i.bak '/^SEARXNG_RATE_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_MIN_DELAY=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_BURST_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_CACHE=/d' .env.local 2>/dev/null || true
        echo "" >> .env.local
        echo "# === Balanced Preset (Default) ===" >> .env.local
        echo "SEARXNG_RATE_LIMIT=2.0" >> .env.local
        echo "SEARXNG_MIN_DELAY=1.0" >> .env.local
        echo "SEARXNG_BURST_LIMIT=5.0" >> .env.local
        echo "SEARXNG_CACHE=1" >> .env.local
        echo "✅ Applied: ~120 searches/min max"
        ;;
    3)
        echo ""
        echo "⚠️  WARNING: Aggressive preset increases ban risk!"
        read -p "Continue? [y/N]: " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            echo "Applying Aggressive preset..."
            sed -i.bak '/^SEARXNG_RATE_LIMIT=/d' .env.local 2>/dev/null || true
            sed -i.bak '/^SEARXNG_MIN_DELAY=/d' .env.local 2>/dev/null || true
            sed -i.bak '/^SEARXNG_BURST_LIMIT=/d' .env.local 2>/dev/null || true
            sed -i.bak '/^SEARXNG_CACHE=/d' .env.local 2>/dev/null || true
            echo "" >> .env.local
            echo "# === Aggressive Preset (USE WITH CAUTION) ===" >> .env.local
            echo "SEARXNG_RATE_LIMIT=5.0" >> .env.local
            echo "SEARXNG_MIN_DELAY=0.5" >> .env.local
            echo "SEARXNG_BURST_LIMIT=10.0" >> .env.local
            echo "SEARXNG_CACHE=1" >> .env.local
            echo "✅ Applied: ~300 searches/min max"
            echo "⚠️  Monitor logs for 429/403 errors!"
        else
            echo "Cancelled."
            exit 0
        fi
        ;;
    4)
        echo ""
        echo "Custom Configuration"
        echo "-------------------"
        read -p "Rate limit (req/sec) [2.0]: " rate
        rate=${rate:-2.0}
        read -p "Min delay (seconds) [1.0]: " delay
        delay=${delay:-1.0}
        read -p "Burst capacity [5.0]: " burst
        burst=${burst:-5.0}
        
        sed -i.bak '/^SEARXNG_RATE_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_MIN_DELAY=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_BURST_LIMIT=/d' .env.local 2>/dev/null || true
        sed -i.bak '/^SEARXNG_CACHE=/d' .env.local 2>/dev/null || true
        echo "" >> .env.local
        echo "# === Custom Configuration ===" >> .env.local
        echo "SEARXNG_RATE_LIMIT=$rate" >> .env.local
        echo "SEARXNG_MIN_DELAY=$delay" >> .env.local
        echo "SEARXNG_BURST_LIMIT=$burst" >> .env.local
        echo "SEARXNG_CACHE=1" >> .env.local
        echo "✅ Applied custom settings"
        ;;
    5)
        echo ""
        if [ -f IP_BAN_PREVENTION.md ]; then
            # Try to open with default markdown viewer
            if command -v xdg-open &> /dev/null; then
                xdg-open IP_BAN_PREVENTION.md
            elif command -v open &> /dev/null; then
                open IP_BAN_PREVENTION.md
            else
                echo "📖 Opening guide..."
                cat IP_BAN_PREVENTION.md | less
            fi
        else
            echo "❌ IP_BAN_PREVENTION.md not found"
        fi
        exit 0
        ;;
    6)
        echo "Cancelled."
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "🎯 Configuration Summary"
echo "----------------------"
grep "SEARXNG_RATE_LIMIT\|SEARXNG_MIN_DELAY\|SEARXNG_BURST_LIMIT\|SEARXNG_CACHE" .env.local | grep -v "^#"

echo ""
echo "📚 Next Steps:"
echo "  1. Restart your application to apply changes"
echo "  2. Monitor logs: tail -f data/logs/app.log"
echo "  3. Check for rate limit warnings"
echo "  4. Read IP_BAN_PREVENTION.md for more details"
echo ""
echo "✨ Configuration complete!"
