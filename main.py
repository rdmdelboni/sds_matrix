"""Entry point for the FDS Extraction desktop application."""

import sys
import traceback
from src.gui.main_app import run_app

def main() -> None:
    """Launch the Tkinter application."""
    try:
        print("🚀 Iniciando FDS Extractor...")
        print("📊 Carregando configurações...")
        run_app()
    except Exception as e:
        print("\n❌ ERRO AO INICIAR A APLICAÇÃO:")
        print(f"   {type(e).__name__}: {e}")
        print("\n📋 Stack trace completo:")
        traceback.print_exc()
        print("\n💡 Possíveis soluções:")
        print("   1. Verifique se o ambiente virtual está ativado: source .venv/bin/activate")
        print("   2. Reinstale as dependências: pip install -r requirements.txt")
        print("   3. Verifique se o Ollama está rodando: ollama list")
        print("   4. Execute o teste: python teste_rapido.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
