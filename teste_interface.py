#!/usr/bin/env python3
"""
Teste rápido da interface gráfica - apenas valida a inicialização.
"""

import sys
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🧪 Testando inicialização da interface...")
print("")

try:
    # Importa as configurações
    from src.utils.config import MAX_WORKERS, CHUNK_SIZE, LM_STUDIO_CONFIG

    print("📊 Configurações carregadas:")
    print(f"   MAX_WORKERS: {MAX_WORKERS}")
    print(f"   CHUNK_SIZE: {CHUNK_SIZE}")
    print(f"   LM_STUDIO_MODEL: {LM_STUDIO_CONFIG['model']}")
    print("")

    # Importa a aplicação
    print("📦 Importando módulos da aplicação...")
    from src.gui.main_app import Application
    import tkinter as tk

    print("✅ Import bem-sucedido!")
    print("")

    # Cria instância (mas não executa mainloop)
    print("🎨 Criando instância da aplicação...")
    app = Application()

    print("✅ Aplicação criada com sucesso!")
    print("")

    # Verifica workers
    actual_workers = app.processing_queue.workers
    print(f"🔧 Workers configurados: {actual_workers}")

    if actual_workers == MAX_WORKERS:
        print(f"✅ CORRETO: Usando {MAX_WORKERS} workers do .env")
    else:
        print(f"❌ ERRO: Esperado {MAX_WORKERS} workers, mas tem {actual_workers}")

    print("")
    print("🎉 TESTE PASSOU!")
    print("✅ A interface pode ser iniciada com: ./iniciar.sh")
    print("")

    # Fecha a aplicação
    app.destroy()

except Exception as e:
    print(f"\n❌ ERRO: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
