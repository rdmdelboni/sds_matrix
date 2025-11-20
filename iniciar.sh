#!/bin/bash
# Script de inicialização do FDS Extractor com ambiente virtual

echo "🚀 Iniciando FDS Extractor..."
echo ""

# Ativa o ambiente virtual
if [ -d ".venv" ]; then
    echo "✅ Ativando ambiente virtual (.venv)..."
    source .venv/bin/activate
elif [ -d "venv" ]; then
    echo "✅ Ativando ambiente virtual (venv)..."
    source venv/bin/activate
else
    echo "❌ Ambiente virtual não encontrado!"
    echo "   Crie um com: python -m venv .venv"
    exit 1
fi

# Configura variáveis de ambiente para Crawl4AI
echo "🔧 Configurando Crawl4AI com proteção contra IP bans..."
export CRAWL4AI_ENABLED=1
export CRAWL4AI_MIN_DELAY=1.0              # 1 segundo entre requisições (seguro)
export MAX_CRAWL_PAGES_PER_FIELD=2         # Máximo 2 páginas por campo
export CRAWL_TEXT_MAX_CHARS=5000           # Máximo 5KB por página
export CRAWL4AI_BROWSER_TYPE=chromium      # Tipo de browser
export CRAWL4AI_HEADLESS=true              # Modo headless
export CRAWL4AI_CACHE_ENABLED=true         # Cache habilitado

# Configurações de Field-Level Retry & Backoff (Todo 10)
export FIELD_SEARCH_MAX_ATTEMPTS=3         # 3 tentativas de busca
export FIELD_SEARCH_BACKOFF_BASE=0.5       # Base de backoff exponencial

# Configurações de Web Search (SearXNG)
export SEARXNG_MIN_DELAY=1.0               # 1 segundo entre buscas
export SEARXNG_CACHE=1                     # Cache de resultados
export SEARXNG_CRAWL=1                     # Usar Crawl4AI

echo "✅ Variáveis de ambiente configuradas:"
echo "   • CRAWL4AI_ENABLED: $CRAWL4AI_ENABLED"
echo "   • CRAWL4AI_MIN_DELAY: $CRAWL4AI_MIN_DELAY segundos"
echo "   • MAX_CRAWL_PAGES_PER_FIELD: $MAX_CRAWL_PAGES_PER_FIELD"
echo "   • Proteção contra IP bans: ATIVA"
echo ""

# Inicia a aplicação
echo "✅ Iniciando aplicação..."
echo ""
python main.py
