#!/bin/bash
# Setup script for SearXNG with JSON output enabled

echo "🔍 Setting up SearXNG..."

# Start SearXNG to generate default config
echo "📦 Starting SearXNG container..."
docker compose up -d

# Wait for initialization
echo "⏳ Waiting for SearXNG to initialize (10 seconds)..."
sleep 10

# Stop container
echo "⏸️  Stopping container to configure..."
docker compose down

# Check if settings.yml exists
if [ ! -f "searxng/settings.yml" ]; then
    echo "❌ Error: settings.yml not created. Trying manual setup..."
    mkdir -p searxng
    
    # Download default settings
    echo "📥 Downloading default SearXNG configuration..."
    curl -o searxng/settings.yml https://raw.githubusercontent.com/searxng/searxng/master/searx/settings.yml
fi

# Enable JSON format
echo "🔧 Enabling JSON output format..."
if grep -q "formats:" searxng/settings.yml; then
    # Add json if not already there
    if ! grep -q "json" searxng/settings.yml; then
        sed -i '/formats:/a\    - json' searxng/settings.yml
        echo "✅ JSON format enabled"
    else
        echo "✅ JSON format already enabled"
    fi
else
    echo "⚠️  Warning: Could not find 'formats:' section in settings.yml"
    echo "   Please manually add '- json' to the search.formats section"
fi

# Generate secret key if needed
if grep -q "ultrasecretkey" searxng/settings.yml; then
    echo "🔐 Generating secret key..."
    SECRET=$(openssl rand -hex 32)
    sed -i "s/ultrasecretkey/${SECRET}/" searxng/settings.yml
    echo "✅ Secret key generated"
fi

# Start SearXNG
echo "🚀 Starting SearXNG..."
docker compose up -d

echo ""
echo "✅ SearXNG setup complete!"
echo ""
echo "🌐 Access SearXNG at: http://localhost:8080"
echo "🧪 Test JSON API: http://localhost:8080/search?q=test&format=json"
echo ""
echo "To stop SearXNG: docker compose down"
echo "To view logs: docker compose logs -f searxng"
