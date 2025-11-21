#!/usr/bin/env python3
"""
Script para preview das melhorias na interface gráfica.
Execute este arquivo para visualizar a nova interface do FDS Extractor.
"""

import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    print("=" * 60)
    print("🎨 FDS EXTRACTOR - PREVIEW DA INTERFACE MELHORADA")
    print("=" * 60)
    print()
    print("✨ Melhorias Implementadas:")
    print("  • Sistema de cores moderno e profissional")
    print("  • Botões estilizados com ícones Unicode")
    print("  • Layout em cards para melhor organização")
    print("  • Tabelas modernizadas com cores de validação")
    print("  • Abas com ícones e estilo aprimorado")
    print("  • Barra de status na parte inferior")
    print("  • Diálogos de progresso e erro redesenhados")
    print("  • Tipografia aprimorada (Segoe UI)")
    print("  • Hierarquia visual clara")
    print("  • Responsividade e melhor usabilidade")
    print()
    print("📖 Para mais detalhes, consulte: MELHORIAS_INTERFACE.md")
    print()
    print("🚀 Iniciando aplicação...")
    print("=" * 60)
    print()

    try:
        from src.gui.main_app import run_app
        run_app()
    except Exception as e:
        print(f"❌ Erro ao iniciar a aplicação: {e}")
        print()
        print("💡 Certifique-se de que todas as dependências estão instaladas:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
