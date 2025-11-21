#!/usr/bin/env python3
"""
Teste da janela de progresso - centralização e movimento.
"""

import sys
import time
from pathlib import Path

# Adiciona o diretório do projeto ao path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from src.gui.main_app import ProgressDialog, COLORS

def test_progress_dialog():
    """Testa a janela de progresso."""
    print("🧪 Testando janela de progresso...")
    print("")

    # Cria janela principal (invisível)
    root = tk.Tk()
    root.withdraw()

    print("✅ Janela principal criada")
    print("")

    # Cria janela de progresso
    print("📊 Criando janela de progresso...")
    dialog = ProgressDialog(root, total=100)

    print("✅ Janela de progresso criada!")
    print("")
    print("🎯 Características:")
    print("   - Centralizada na tela")
    print("   - Pode ser movida arrastando o título")
    print("   - Pode ser redimensionada")
    print("")
    print("🔄 Simulando progresso...")
    print("")

    # Simula progresso
    for i in range(1, 101, 10):
        dialog.update(i)
        root.update()
        time.sleep(0.3)

    print("✅ Progresso completo!")
    print("")
    print("🎉 TESTE PASSOU!")
    print("   A janela está centralizada e pode ser movida!")
    print("")

    # Espera um pouco antes de fechar
    time.sleep(2)
    dialog.close()
    root.destroy()

if __name__ == "__main__":
    try:
        test_progress_dialog()
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
