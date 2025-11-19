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

# Inicia a aplicação
echo "✅ Iniciando aplicação..."
echo ""
python main.py
