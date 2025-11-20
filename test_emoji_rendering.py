#!/usr/bin/env python
"""Test script to verify emoji rendering in the application."""

import tkinter as tk
from tkinter import ttk
import platform


def test_emoji_rendering():
    """Test emoji rendering with different font configurations."""
    
    root = tk.Tk()
    root.title("Teste de Renderização de Emojis")
    root.geometry("800x600")
    
    # Get system info
    system = platform.system()
    
    # Configure fonts based on system
    if system == "Linux":
        base_font = "DejaVu Sans"
        fixed_font = "DejaVu Sans Mono"
    elif system == "Darwin":  # macOS
        base_font = "SF Pro Text"
        fixed_font = "Monaco"
    else:  # Windows
        base_font = "Segoe UI"
        fixed_font = "Consolas"
    
    # Create main frame
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    # Title
    title = ttk.Label(
        main_frame,
        text="🧪 Teste de Renderização de Emojis",
        font=(base_font, 18, "bold")
    )
    title.pack(pady=(0, 20))
    
    # System info
    info = ttk.Label(
        main_frame,
        text=f"Sistema: {system}\nFonte Base: {base_font}\nFonte Mono: {fixed_font}",
        font=(base_font, 12)
    )
    info.pack(pady=(0, 20))
    
    # Test emojis used in the application
    emojis_to_test = [
        ("✨", "Estrela (campos atualizados)"),
        ("📄", "Documento"),
        ("🔍", "Buscar"),
        ("📊", "Exportar CSV"),
        ("📈", "Exportar Excel"),
        ("🔄", "Atualizar/Reprocessar"),
        ("✓", "Válido"),
        ("⚠", "Aviso"),
        ("✗", "Inválido"),
        ("⚙️", "Configurações"),
        ("🌐", "Online"),
        ("💻", "Local"),
        ("💡", "Sugestões"),
        ("📋", "Detalhes"),
        ("🚀", "Ícones diversos"),
    ]
    
    # Create scrollable text widget
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True)
    
    text = tk.Text(
        text_frame,
        font=(base_font, 14),
        wrap="word",
        height=20,
        relief="solid",
        borderwidth=1
    )
    scrollbar = ttk.Scrollbar(text_frame, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    
    text.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Insert test emojis
    text.insert("1.0", "Emojis utilizados na aplicação:\n\n")
    
    for emoji, description in emojis_to_test:
        text.insert("end", f"  {emoji}  →  {description}\n")
    
    text.insert("end", "\n" + "="*60 + "\n\n")
    text.insert("end", "Se todos os emojis acima aparecerem corretamente,\n")
    text.insert("end", "a fonte está configurada adequadamente!\n\n")
    text.insert("end", "Caso alguns emojis apareçam como □ ou ?,\n")
    text.insert("end", "você pode precisar instalar fontes adicionais:\n\n")
    text.insert("end", "Linux:\n")
    text.insert("end", "  sudo apt install fonts-noto-color-emoji\n")
    text.insert("end", "  sudo apt install fonts-dejavu\n\n")
    text.insert("end", "macOS:\n")
    text.insert("end", "  Emojis já incluídos no sistema\n\n")
    text.insert("end", "Windows:\n")
    text.insert("end", "  Segoe UI Emoji já incluída\n")
    
    text.configure(state="disabled")
    
    # Close button
    close_btn = ttk.Button(
        main_frame,
        text="Fechar",
        command=root.destroy
    )
    close_btn.pack(pady=(10, 0))
    
    root.mainloop()


if __name__ == "__main__":
    print("=" * 70)
    print("Teste de Renderização de Emojis")
    print("=" * 70)
    print("\nAbrindo janela de teste...")
    print("Verifique se todos os emojis aparecem corretamente.")
    print("\nSistema detectado:", platform.system())
    
    test_emoji_rendering()
