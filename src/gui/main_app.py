"""Tkinter user interface for the FDS extraction MVP."""

from __future__ import annotations

import queue
import threading
import os
import sys
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ..core.chunk_strategy import ChunkStrategy
from ..core.document_processor import DocumentProcessor, DEFAULT_FIELDS, ADDITIONAL_FIELDS
from ..core.llm_client import LMStudioClient, GeminiClient
from ..core.queue_manager import ProcessingQueue
from ..database.duckdb_manager import DuckDBManager
from ..utils.file_utils import list_supported_files
from ..utils.config import DATA_DIR, ONLINE_SEARCH_PROVIDER
from ..utils.logger import logger


# Modern Color Palette
COLORS = {
    "primary": "#2563eb",      # Blue
    "primary_dark": "#1e40af",
    "primary_light": "#dbeafe",
    "success": "#10b981",      # Green
    "success_light": "#d1fae5",
    "warning": "#f59e0b",      # Orange
    "warning_light": "#fef3c7",
    "error": "#ef4444",        # Red
    "error_light": "#fee2e2",
    "neutral_50": "#f9fafb",
    "neutral_100": "#f3f4f6",
    "neutral_200": "#e5e7eb",
    "neutral_300": "#d1d5db",
    "neutral_400": "#9ca3af",
    "neutral_500": "#6b7280",
    "neutral_600": "#4b5563",
    "neutral_700": "#374151",
    "neutral_800": "#1f2937",
    "neutral_900": "#111827",
    "white": "#ffffff",
    "text_primary": "#111827",
    "text_secondary": "#6b7280",
}


class SetupTab(ttk.Frame):
    """Tab responsible for folder selection and file preview."""

    def __init__(self, master: ttk.Notebook, controller: "Application") -> None:
        super().__init__(master, padding=32)
        self.controller = controller

        self.folder_var = tk.StringVar(value="Nenhuma pasta selecionada.")
        self.llm_status_var = tk.StringVar(value="Verificando conexao com LLM local (Ollama/LM Studio)...")

        # App state for remembering last selected folder
        self._state_path = (DATA_DIR / "config" / "app_state.json")
        self._last_folder = self._load_last_folder()

        # Header frame with gradient-like background
        header_frame = ttk.Frame(self, style="Header.TFrame")
        header_frame.pack(fill="x", pady=(0, 16))

        top_frame = ttk.Frame(header_frame)
        top_frame.pack(fill="x", pady=12, padx=16)

        # Styled buttons with icons (using Unicode symbols)
        ttk.Button(top_frame, text="📁 Selecionar pasta", command=self._select_folder, style="Primary.TButton").pack(side="left")
        self._btn_reload = ttk.Button(top_frame, text="🔄 Recarregar pasta", command=self._reload_folder, style="Secondary.TButton")
        self._btn_reload.pack(side="left", padx=(12, 0))
        ttk.Button(top_frame, text="➕ Adicionar a fila", command=self._enqueue_files, style="Success.TButton").pack(side="left", padx=(12, 0))

        # Info label with better styling
        info_label = ttk.Label(top_frame, textvariable=self.folder_var, style="Info.TLabel")
        info_label.pack(side="left", padx=(24, 0))

        # Show last folder on label at startup, if available
        try:
            if self._last_folder and self._last_folder.exists():
                self.folder_var.set(str(self._last_folder))
        except Exception:
            pass

        # Auto-load files from last folder into the grid on startup
        try:
            if self._last_folder and self._last_folder.exists():
                self._load_folder_files(self._last_folder)
        except Exception:
            # Ignore failures silently; user can reselect manually
            pass
        # Ensure reload button reflects current state at startup
        self._update_reload_button()

        # Status label with badge-like styling
        status_frame = ttk.Frame(self, style="Status.TFrame")
        status_frame.pack(fill="x", pady=(0, 16))
        ttk.Label(status_frame, text="🔌 Status:", style="StatusLabel.TLabel").pack(side="left", padx=(8, 4))
        ttk.Label(status_frame, textvariable=self.llm_status_var, style="StatusValue.TLabel").pack(side="left")

        # Progress bar frame (hidden by default, shown during processing)
        self.progress_frame = ttk.Frame(self, style="Status.TFrame")
        # Don't pack it yet - will be packed when show_progress() is called
        self.progress_visible = False

        # Progress bar with cancel button frame
        progress_container = ttk.Frame(self.progress_frame, style="Status.TFrame")
        progress_container.pack(fill="x", padx=(8, 8), pady=(8, 8))

        # Progress bar (takes up space, grows to fill)
        self.progress_var = tk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_container,
            length=500,
            maximum=100,
            mode="determinate",
            variable=self.progress_var
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Cancel button on the right
        self.cancel_button = ttk.Button(
            progress_container,
            text="⏹️ Cancelar",
            command=self._cancel_processing
        )
        self.cancel_button.pack(side="right")

        # Progress percentage and status label
        self.progress_label_var = tk.StringVar(value="0%")
        ttk.Label(
            progress_container,
            textvariable=self.progress_label_var,
            style="StatusValue.TLabel",
            width=8
        ).pack(side="right", padx=(8, 0))

        # Files list with improved styling
        self.list_frame = ttk.Frame(self, style="Card.TFrame")
        self.list_frame.pack(fill="both", expand=True)

        # Title for the list with file counter
        self.title_label_var = tk.StringVar(value="📄 Arquivos Disponíveis")
        ttk.Label(self.list_frame, textvariable=self.title_label_var, style="SectionTitle.TLabel").pack(anchor="w", pady=(12, 8), padx=16)

        columns = ("documento", "pasta", "tamanho")
        self.tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", height=15, style="Modern.Treeview")
        self.tree.heading("documento", text="📄 Documento")
        self.tree.heading("pasta", text="📁 Pasta")
        self.tree.heading("tamanho", text="💾 Tamanho (KB)")
        self.tree.column("documento", width=600, anchor="w")
        self.tree.column("pasta", width=400, anchor="w")
        self.tree.column("tamanho", width=150, anchor="center")

        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 16))
        scrollbar.pack(side="right", fill="y", padx=(0, 16), pady=(0, 16))

        # Configure alternating row colors for better readability
        self.tree.tag_configure("oddrow", background=COLORS["white"])
        self.tree.tag_configure("evenrow", background=COLORS["neutral_50"])

    def _select_folder(self) -> None:
        # Use last folder as starting point if available
        kwargs: dict[str, object] = {"title": "Escolha a pasta com FDS"}
        try:
            if self._last_folder and self._last_folder.exists():
                kwargs["initialdir"] = str(self._last_folder)
        except Exception:
            pass
        folder = filedialog.askdirectory(**kwargs)  # type: ignore[arg-type]
        if not folder:
            return
        self._load_folder_files(Path(folder))

    def _enqueue_files(self) -> None:
        if not self.controller.selected_files:
            messagebox.showinfo("Nenhum arquivo", "Selecione uma pasta com arquivos suportados primeiro.")
            return
        self.controller.start_processing()

    def update_llm_status(self, status: str) -> None:
        """Update the connection status label."""
        self.llm_status_var.set(status)

    def show_progress(self, total: int) -> None:
        """Show the integrated progress bar."""
        self.progress_var.set(0)
        self.progress_bar.configure(maximum=total)
        self.progress_label_var.set("0%")
        if not self.progress_visible:
            # Pack it before the list_frame to show it between status and files list
            self.progress_frame.pack(fill="x", pady=(0, 7), before=self.list_frame)
            self.progress_visible = True

    def update_progress(self, current: int, total: int) -> None:
        """Update the integrated progress bar."""
        if total > 0:
            self.progress_var.set(current)
            percentage = (current * 100) // total
            self.progress_label_var.set(f"{percentage}%")

    def hide_progress(self) -> None:
        """Hide the integrated progress bar."""
        if self.progress_visible:
            self.progress_frame.pack_forget()
            self.progress_visible = False
        self.progress_var.set(0)
        self.progress_label_var.set("0%")

    def _cancel_processing(self) -> None:
        """Cancel the current processing."""
        if hasattr(self.controller, 'processing_queue') and self.controller.processing_queue:
            self.controller.processing_queue.stop()
            self.hide_progress()
            messagebox.showinfo("Cancelado", "Processamento cancelado pelo usuário.")

    # --- Persistence helpers ---
    def _reload_folder(self) -> None:
        """Reload files from the last selected folder into the grid."""
        try:
            if self._last_folder and self._last_folder.exists():
                self._load_folder_files(self._last_folder)
            else:
                messagebox.showinfo("Recarregar pasta", "Nenhuma pasta previa encontrada. Selecione uma pasta primeiro.")
        except Exception as exc:  # noqa: BLE001
            self.controller._show_error_dialog(
                title="Falha ao recarregar pasta",
                message="Nao foi possivel recarregar a pasta.",
                details=str(exc),
            )
        finally:
            self._update_reload_button()
    
    def _load_folder_files(self, path: Path) -> None:
        try:
            files = list_supported_files(path, recursive=True)
        except Exception as exc:  # noqa: BLE001
            # Use the unified error dialog with hints
            self.controller._show_error_dialog(
                title="Erro ao listar arquivos",
                message="Nao foi possivel listar os arquivos da pasta selecionada.",
                details=str(exc),
                suggestions=(
                    "• Verifique permissoes de leitura na pasta selecionada.\n"
                    "• Confirme se os arquivos sao PDFs ou imagens suportadas.\n"
                    "• Se forem PDFs digitalizados, considere instalar o Tesseract OCR."
                ),
            )
            return

        # Update selected files for controller
        self.controller.set_selected_files(files)

        # Refresh tree content
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Count unique folders
        unique_folders = set()
        for idx, file_path in enumerate(files):
            try:
                size_kb = file_path.stat().st_size / 1024
            except Exception:
                size_kb = 0.0

            # Get relative path from base folder
            try:
                relative_path = file_path.relative_to(path)
                folder_path = str(relative_path.parent) if relative_path.parent != Path(".") else "."
                unique_folders.add(folder_path)
            except ValueError:
                folder_path = str(file_path.parent.name)

            # Apply alternating row colors
            row_tag = "evenrow" if idx % 2 == 0 else "oddrow"

            self.tree.insert(
                "",
                "end",
                iid=str(file_path),
                values=(file_path.name, folder_path, f"{size_kb:.1f}"),
                tags=(row_tag,),
            )

        # Update title with counts
        folder_count = len(unique_folders)
        self.title_label_var.set(
            f"📄 Arquivos Disponíveis ({len(files)} arquivo(s) em {folder_count} pasta(s))"
        )

        self.folder_var.set(f"{path} ({len(files)} arquivo(s))")
        # Persist last selected folder
        self._last_folder = path
        self._save_last_folder(path)
        # Update reload button text/state with fresh count
        self._update_reload_button(len(files))

    def _load_last_folder(self) -> Path | None:
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            if self._state_path.exists():
                import json
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                last = data.get("last_folder") if isinstance(data, dict) else None
                if isinstance(last, str):
                    p = Path(last)
                    return p
        except Exception:
            pass
        return None

    def _save_last_folder(self, path: Path) -> None:
        try:
            import json
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"last_folder": str(path)}
            self._state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # Non-fatal if we can't save
            pass

    def _update_reload_button(self, count: int | None = None) -> None:
        """Enable/disable and update text for the 'Recarregar pasta' button.

        If count is None and a last folder exists, try to compute it lazily.
        """
        try:
            if getattr(self, "_btn_reload", None) is None:
                return
            if not (self._last_folder and self._last_folder.exists()):
                self._btn_reload.configure(text="Recarregar pasta")
                self._btn_reload.state(["disabled"])  # type: ignore[attr-defined]
                return
            # Ensure enabled
            try:
                self._btn_reload.state(["!disabled"])  # type: ignore[attr-defined]
            except Exception:
                pass
            # Compute count if not provided
            if count is None:
                try:
                    files = list_supported_files(self._last_folder)
                    count = len(files)
                except Exception:
                    count = None
            label = "Recarregar pasta" if count is None else f"Recarregar pasta ({count})"
            self._btn_reload.configure(text=label)
        except Exception:
            # Silent UI failure tolerance
            pass


class ProcessingTab(ttk.Frame):
    """Tab displaying processing progress and extracted results."""

    def __init__(self, master: ttk.Notebook, controller: "Application") -> None:
        super().__init__(master, padding=24)
        self.controller = controller
        self._modes: dict[str, str] = {}  # iid -> mode ("online"|"local")
        self._mode_editor: ttk.Combobox | None = None

        # Header frame
        header_frame = ttk.Frame(self, style="Header.TFrame")
        header_frame.pack(fill="x", pady=(0, 16))

        # Toolbar for bulk actions (set mode for selected rows)
        toolbar = ttk.Frame(header_frame)
        toolbar.pack(fill="x", pady=12, padx=16)
        ttk.Label(toolbar, text="⚙️ Alterar modo:", style="ToolbarLabel.TLabel").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="🌐 Modo: Online", command=self._set_selected_mode_online, style="Primary.TButton").pack(side="left", padx=(0, 8))
        ttk.Button(toolbar, text="💻 Modo: Local", command=self._set_selected_mode_local, style="Secondary.TButton").pack(side="left")

        # Table frame with card styling
        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True, pady=(0, 16))

        # Title frame
        title_frame = ttk.Frame(table_frame, style="Card.TFrame")
        title_frame.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(title_frame, text="📊 Progresso do Processamento", style="SectionTitle.TLabel").pack(anchor="w")

        # Tree container for grid layout
        tree_container = ttk.Frame(table_frame, style="Card.TFrame")
        tree_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        columns = (
            "documento",
            "status",
            "modo",
                "nome_produto",
                "fabricante",
                "numero_onu",
                "onu_validacao",
                "numero_cas",
                "cas_validacao",
                "classe_onu",
                "grupo_embalagem",
                "incompatibilidades",
        )
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=15, style="Modern.Treeview")
        self.tree.heading("documento", text="📄 Documento")
        self.tree.heading("status", text="Status")
        self.tree.heading("modo", text="Modo")
        self.tree.heading("nome_produto", text="Produto")
        self.tree.heading("fabricante", text="Fabricante")
        self.tree.heading("numero_onu", text="ONU")
        self.tree.heading("onu_validacao", text="ONU ✓")
        self.tree.heading("numero_cas", text="CAS")
        self.tree.heading("cas_validacao", text="CAS ✓")
        self.tree.heading("classe_onu", text="Classe")
        self.tree.heading("grupo_embalagem", text="Grupo Emb")
        self.tree.heading("incompatibilidades", text="Incompatibilidades")
        self.tree.column("documento", width=280, anchor="w")
        self.tree.column("status", width=140, anchor="center")
        self.tree.column("modo", width=100, anchor="center")
        self.tree.column("nome_produto", width=400, anchor="w")
        self.tree.column("fabricante", width=350, anchor="w")
        self.tree.column("numero_onu", width=100, anchor="center")
        self.tree.column("onu_validacao", width=80, anchor="center")
        self.tree.column("numero_cas", width=180, anchor="center")
        self.tree.column("cas_validacao", width=80, anchor="center")
        self.tree.column("classe_onu", width=100, anchor="center")
        self.tree.column("grupo_embalagem", width=140, anchor="center")
        self.tree.column("incompatibilidades", width=350, anchor="w")

        # Add scrollbars
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Modern color scheme with better contrast
        self.tree.tag_configure("valid", background=COLORS["success_light"], foreground=COLORS["text_primary"])
        self.tree.tag_configure("warning", background=COLORS["warning_light"], foreground=COLORS["text_primary"])
        self.tree.tag_configure("invalid", background=COLORS["error_light"], foreground=COLORS["text_primary"])
        # Alternating row colors (used when no validation status)
        self.tree.tag_configure("oddrow", background=COLORS["white"])
        self.tree.tag_configure("evenrow", background=COLORS["neutral_50"])
        # Enable editing of 'modo' on double-click
        self.tree.bind("<Double-1>", self._on_double_click)

        # Context menu for changing mode via right-click
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Alterar modo para online", command=self._set_selected_mode_online)
        self._context_menu.add_command(label="Alterar modo para local", command=self._set_selected_mode_local)
        self.tree.bind("<Button-3>", self._on_processing_right_click)

    def update_status(
        self,
        file_path: Path,
        status: str,
        field_details: dict[str, dict[str, object]] | None = None,
    ) -> None:
        iid = str(file_path)
        field_details = field_details or {}

        def format_simple(name: str) -> str:
            data = field_details.get(name) or {}
            value = str(data.get("value") or "-")
            if value == "NAO ENCONTRADO":
                return "-"
            return value

        def format_validation(name: str) -> str:
            data = field_details.get(name) or {}
            st = data.get("validation_status")
            icons = {"valid": "✓", "warning": "⚠", "invalid": "✗"}
            key = st if isinstance(st, str) else ""
            return icons.get(key, "-")

        nome_produto = format_simple("nome_produto")
        fabricante = format_simple("fabricante")
        onu_value = format_simple("numero_onu")
        onu_valid = format_validation("numero_onu")
        cas_value = format_simple("numero_cas")
        cas_valid = format_validation("numero_cas")
        classe_value = format_simple("classificacao_onu")
        grupo_emb = format_simple("grupo_embalagem")
        incompat = format_simple("incompatibilidades")

        # Selected mode with default 'online'
        mode_val = self._modes.get(iid, "online")

        values = (
            file_path.name,
            status,
            mode_val,
            nome_produto,
            fabricante,
            onu_value,
            onu_valid,
            cas_value,
            cas_valid,
            classe_value,
            grupo_emb,
            incompat,
        )
        # combine tags based on any invalid/warning statuses
        statuses = [
            data.get("validation_status")
            for data in field_details.values()
            if data.get("validation_status") in {"valid", "warning", "invalid"}
        ]
        severity_order = ["invalid", "warning", "valid"]
        selected_tag = None
        for severity in severity_order:
            if severity in statuses:
                selected_tag = severity
                break
        tags = (selected_tag,) if selected_tag else ()
        if self.tree.exists(iid):
            self.tree.item(iid, values=values, tags=tags)
        else:
            self.tree.insert("", "end", iid=iid, values=values, tags=tags)

    def get_mode(self, file_path: Path) -> str:
        """Return selected processing mode for a file (default 'online')."""
        return self._modes.get(str(file_path), "online")

    def set_mode(self, file_path: Path, mode: str) -> None:
        iid = str(file_path)
        if mode not in {"online", "local"}:
            mode = "online"
        self._modes[iid] = mode
        # Refresh row to show updated value
        if self.tree.exists(iid):
            vals = list(self.tree.item(iid, "values"))
            # 'modo' is the third column (index 2)
            if len(vals) >= 3:
                vals[2] = mode
                self.tree.item(iid, values=tuple(vals))

        # Hide editor if visible
        if self._mode_editor:
            try:
                self._mode_editor.destroy()
            except Exception:
                pass
            self._mode_editor = None

    def _edit_mode_cell(self, iid: str) -> None:
        """Overlay a Combobox on top of the 'modo' cell for a given row."""
        try:
            bbox = self.tree.bbox(iid, column="#3")  # third displayed column
            if not bbox:
                return
            x, y, w, h = bbox
            # Convert to absolute coordinates within this frame
            abs_x = x + self.tree.winfo_rootx() - self.winfo_rootx()
            abs_y = y + self.tree.winfo_rooty() - self.winfo_rooty()

            if self._mode_editor:
                try:
                    self._mode_editor.destroy()
                except Exception:
                    pass
                self._mode_editor = None

            editor = ttk.Combobox(self, values=("online", "local"), state="readonly", width=10)
            editor.place(x=abs_x, y=abs_y, width=w, height=h)
            current = self._modes.get(iid, "online")
            editor.set(current)

            def _on_select(_: object = None) -> None:
                try:
                    self._modes[iid] = editor.get()
                except Exception:
                    self._modes[iid] = "online"
                # Update tree cell
                vals = list(self.tree.item(iid, "values"))
                if len(vals) >= 3:
                    vals[2] = self._modes[iid]
                    self.tree.item(iid, values=tuple(vals))
                # Remove editor
                try:
                    editor.destroy()
                except Exception:
                    pass
                self._mode_editor = None

            editor.bind("<<ComboboxSelected>>", _on_select)
            editor.focus_set()
            self._mode_editor = editor
        except Exception:
            # best-effort; ignore overlay errors
            pass

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Start editing the 'modo' cell when it's double-clicked."""
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        # '#3' corresponds to our 'modo' column
        if row_id and col_id == "#3":
            self._edit_mode_cell(row_id)

    def _on_processing_right_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Select row under cursor and show context menu for mode change."""
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                current = set(self.tree.selection())
                if row_id not in current:
                    self.tree.selection_set(row_id)
                self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._context_menu.grab_release()
            except Exception:
                pass

    def _set_selected_mode(self, mode: str) -> None:
        """Apply mode to all selected rows and update the UI values."""
        sel = self.tree.selection()
        if not sel:
            return
        for iid in sel:
            self._modes[iid] = mode
            vals = list(self.tree.item(iid, "values"))
            if len(vals) >= 3:
                vals[2] = mode
                self.tree.item(iid, values=tuple(vals))

    def _set_selected_mode_online(self) -> None:
        self._set_selected_mode("online")

    def _set_selected_mode_local(self) -> None:
        self._set_selected_mode("local")


class ResultsTab(ttk.Frame):
    """Tab to show processed outputs and trigger exports."""

    def __init__(self, master: ttk.Notebook, controller: "Application") -> None:
        super().__init__(master, padding=24)
        self.controller = controller
        self._results: list[dict[str, object]] = []
        self._filtered_results: list[dict[str, object]] = []

        # Header frame
        header_frame = ttk.Frame(self, style="Header.TFrame")
        header_frame.pack(fill="x", pady=(0, 16))

        toolbar = ttk.Frame(header_frame)
        toolbar.pack(fill="x", pady=12, padx=16)

        # Action buttons
        ttk.Button(toolbar, text="🔄 Atualizar", command=self.refresh, style="Primary.TButton").pack(side="left")
        ttk.Button(toolbar, text="📊 Exportar CSV", command=self._export_csv, style="Success.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="📈 Exportar Excel", command=self._export_excel, style="Success.TButton").pack(side="left", padx=(8, 0))

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=16)

        # Filters
        ttk.Label(toolbar, text="Status:", style="FilterLabel.TLabel").pack(side="left", padx=(0, 4))
        self.status_filter = tk.StringVar(value="Todos")
        status_combo = ttk.Combobox(
            toolbar,
            textvariable=self.status_filter,
            values=("Todos", "success", "failed", "partial"),
            state="readonly",
            width=12,
        )
        status_combo.pack(side="left")
        status_combo.current(0)
        status_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        ttk.Label(toolbar, text="Validação:", style="FilterLabel.TLabel").pack(side="left", padx=(16, 4))
        self.validation_filter = tk.StringVar(value="Todas")
        validation_combo = ttk.Combobox(
            toolbar,
            textvariable=self.validation_filter,
            values=("Todas", "valid", "warning", "invalid"),
            state="readonly",
            width=12,
        )
        validation_combo.pack(side="left")
        validation_combo.current(0)
        validation_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        ttk.Label(toolbar, text="🔍 Buscar:", style="FilterLabel.TLabel").pack(side="left", padx=(16, 4))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=24)
        search_entry.pack(side="left")
        self.search_var.trace_add("write", lambda *_: self._apply_filters())

        self.info_var = tk.StringVar(value="0 registros carregados.")
        ttk.Label(toolbar, textvariable=self.info_var, style="Info.TLabel").pack(side="left", padx=(16, 0))

        # Table frame with card styling
        table_frame = ttk.Frame(self, style="Card.TFrame")
        table_frame.pack(fill="both", expand=True)

        # Title frame
        title_frame = ttk.Frame(table_frame, style="Card.TFrame")
        title_frame.pack(fill="x", padx=16, pady=(12, 8))
        ttk.Label(title_frame, text="📋 Resultados Processados", style="SectionTitle.TLabel").pack(anchor="w")

        # Tree container for grid layout
        tree_container = ttk.Frame(table_frame, style="Card.TFrame")
        tree_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        columns = (
            "documento",
            "status",
            "nome_produto",
            "fabricante",
            "numero_onu",
            "numero_cas",
            "classe_onu",
            "grupo_embalagem",
            "incompatibilidades",
            "processado_em",
        )
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=15, style="Modern.Treeview")
        self.tree.heading("documento", text="📄 Documento")
        self.tree.heading("status", text="Status")
        self.tree.heading("nome_produto", text="Produto")
        self.tree.heading("fabricante", text="Fabricante")
        self.tree.heading("numero_onu", text="ONU")
        self.tree.heading("numero_cas", text="CAS")
        self.tree.heading("classe_onu", text="Classe")
        self.tree.heading("grupo_embalagem", text="Grupo Emb")
        self.tree.heading("incompatibilidades", text="Incompatibilidades")
        self.tree.heading("processado_em", text="⏰ Processado em")

        self.tree.column("documento", width=280, anchor="w")
        self.tree.column("status", width=160, anchor="center")
        self.tree.column("nome_produto", width=400, anchor="w")
        self.tree.column("fabricante", width=350, anchor="w")
        self.tree.column("numero_onu", width=100, anchor="center")
        self.tree.column("numero_cas", width=180, anchor="center")
        self.tree.column("classe_onu", width=100, anchor="center")
        self.tree.column("grupo_embalagem", width=140, anchor="center")
        self.tree.column("incompatibilidades", width=350, anchor="w")
        self.tree.column("processado_em", width=280, anchor="center")

        # Add scrollbars
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Context menu (right-click) for quick actions
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="🔄 Reprocessar seleção (online)", command=self._reprocess_selected_online)
        self.tree.bind("<Button-3>", self._on_results_right_click)

        # Modern color scheme
        self.tree.tag_configure("valid", background=COLORS["success_light"], foreground=COLORS["text_primary"])
        self.tree.tag_configure("warning", background=COLORS["warning_light"], foreground=COLORS["text_primary"])
        self.tree.tag_configure("invalid", background=COLORS["error_light"], foreground=COLORS["text_primary"])
        # Alternating row colors (used when no validation status)
        self.tree.tag_configure("oddrow", background=COLORS["white"])
        self.tree.tag_configure("evenrow", background=COLORS["neutral_50"])

    def _reprocess_selected_online(self) -> None:
        """Trigger online reprocessing (Gemini) for selected rows in the Results grid."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Reprocessar", "Selecione um ou mais registros na lista.")
            return

        doc_ids = []
        for iid in sel:
            try:
                doc_ids.append(int(iid))
            except Exception:  # noqa: BLE001
                continue

        if not doc_ids:
            messagebox.showinfo("Reprocessar", "Selecao invalida.")
            return

        # Show a small progress dialog for this action
        try:
            progress = ProgressDialog(self.controller, total=len(doc_ids))
            progress.show()
        except Exception:
            progress = None  # Graceful fallback

        def _work() -> None:
            ok_count = 0
            for idx, doc_id in enumerate(doc_ids, start=1):
                try:
                    self.controller.processor.reprocess_online(doc_id)
                    ok_count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.error("Falha ao reprocessar %s: %s", doc_id, exc)
                finally:
                    def _update_prog(i: int) -> None:
                        if progress:
                            progress.update(i)
                    self.controller.after(0, lambda i=idx: _update_prog(i))

            def _done() -> None:
                self.refresh()
                if progress:
                    progress.close()
                messagebox.showinfo("Reprocessamento concluido", f"Atualizados {ok_count} documento(s).")

            self.controller.after(0, _done)

        threading.Thread(target=_work, daemon=True).start()

    def _on_results_right_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Select row under cursor and show context menu."""
        try:
            row_id = self.tree.identify_row(event.y)
            if row_id:
                current = set(self.tree.selection())
                if row_id not in current:
                    self.tree.selection_set(row_id)
                self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                self._context_menu.grab_release()
            except Exception:
                pass

    def refresh(self) -> None:
        """Reload data from DuckDB and render in the grid."""
        try:
            self._results = self.controller.db_manager.fetch_recent_results(limit=400)
        except Exception as exc:  # noqa: BLE001
            logger.error("Falha ao carregar resultados: %s", exc)
            messagebox.showerror("Erro", f"Nao foi possivel carregar os resultados.\n{exc}")
            return

        self._apply_filters()

    def _apply_filters(self) -> None:
        """Apply in-memory filters and update the tree view."""
        results = list(self._results)
        status_filter = self.status_filter.get()
        validation_filter = self.validation_filter.get()
        search_term = self.search_var.get().strip().lower()

        if status_filter != "Todos":
            results = [row for row in results if row.get("status") == status_filter]

        if validation_filter != "Todas":
            results = [
                row
                for row in results
                if validation_filter
                in {
                    row.get("numero_onu_status"),
                    row.get("numero_cas_status"),
                    row.get("classificacao_onu_status"),
                }
            ]

        if search_term:
            results = [
                row for row in results if search_term in str(row.get("filename", "")).lower()
            ]

        self._filtered_results = results

        for item in self.tree.get_children():
            self.tree.delete(item)

        def format_simple(val: object) -> str:
            if not val or str(val).upper() == "NAO ENCONTRADO":
                return "-"
            return str(val)

        # Build list of validation statuses to determine row color
        def collect_statuses(row: dict[str, object]) -> list[str]:
            statuses: list[str] = []
            for field in ["numero_onu", "numero_cas", "classificacao_onu"]:
                st = row.get(f"{field}_status")
                if isinstance(st, str) and st:
                    statuses.append(st)
            return statuses

        for row in results:
            processed_at = row.get("processed_at")
            processed_str = (
                processed_at.strftime("%d/%m %H:%M")
                if isinstance(processed_at, datetime)
                else ""
            )

            statuses = collect_statuses(row)
            severity_order = ["invalid", "warning", "valid"]
            selected_tag = None
            for severity in severity_order:
                if severity in statuses:
                    selected_tag = severity
                    break

            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["filename"],
                    row["status"],
                        format_simple(row.get("nome_produto")),
                        format_simple(row.get("fabricante")),
                        format_simple(row.get("numero_onu")),
                        format_simple(row.get("numero_cas")),
                        format_simple(row.get("classificacao_onu")),
                        format_simple(row.get("grupo_embalagem")),
                        format_simple(row.get("incompatibilidades")),
                    processed_str,
                ),
                tags=(selected_tag,) if selected_tag else (),
            )

        total = len(self._results)
        self.info_var.set(f"{len(results)} de {total} registros.")

    def _export_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salvar CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        if self._export_dataframe(Path(path), fmt="csv"):
            messagebox.showinfo("Exportacao concluida", f"Arquivo salvo em:\n{path}")

    def _export_excel(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Salvar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not path:
            return
        if self._export_dataframe(Path(path), fmt="excel"):
            messagebox.showinfo("Exportacao concluida", f"Arquivo salvo em:\n{path}")

    def _export_dataframe(self, target: Path, fmt: str) -> bool:
        """Export current filtered results using pandas as backend."""
        from pandas import DataFrame  # Lazy import to avoid GUI startup cost

        data = self._filtered_results or self._results or []
        if not data:
            messagebox.showinfo("Sem dados", "Nao ha resultados para exportar.")
            return False

        try:
            df = DataFrame(data)
            if fmt == "csv":
                df.to_csv(target, index=False, encoding="utf-8")
            else:
                df.to_excel(target, index=False, sheet_name="Resultados")
            return True
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Erro na exportacao",
                f"Nao foi possivel exportar os resultados para '{target.name}'.\n\nDetalhes: {exc}",
            )
            return False


class Application(tk.Tk):
    """Main Tkinter application."""

    def __init__(self) -> None:
        super().__init__()
        self.title("FDS-2-Matrix")
        self.geometry("1700x1000")
        self.minsize(1200, 700)

        # Set window background
        self.configure(bg=COLORS["neutral_50"])

        # Configure LARGE fonts for better readability
        default_font = ("Segoe UI", 14, "normal")
        text_font = ("Segoe UI", 14)
        fixed_font = ("Consolas", 13)
        menu_font = ("Segoe UI", 14)
        heading_font = ("Segoe UI", 15, "bold")
        title_font = ("Segoe UI", 16, "bold")

        self.option_add("*TCombobox*Listbox*Font", default_font)
        self.option_add("*Font", default_font)
        self.option_add("*TkDefaultFont", default_font)
        self.option_add("*TkTextFont", text_font)
        self.option_add("*TkFixedFont", fixed_font)
        self.option_add("*TkMenuFont", menu_font)

        # Configure modern ttk styles
        style = ttk.Style(self)
        style.theme_use('clam')  # Modern theme base

        # Base styles
        style.configure(".", font=default_font, background=COLORS["neutral_50"])
        style.configure("TFrame", background=COLORS["neutral_50"])
        style.configure("TLabel", font=default_font, background=COLORS["neutral_50"], foreground=COLORS["text_primary"])
        style.configure("TEntry", font=default_font, fieldbackground=COLORS["white"], padding=8)
        style.configure("TCombobox", font=default_font, fieldbackground=COLORS["white"], padding=6)

        # Button styles - Primary (Blue)
        style.configure("Primary.TButton",
                       font=default_font,
                       background=COLORS["primary"],
                       foreground=COLORS["white"],
                       borderwidth=0,
                       focuscolor='none',
                       padding=(16, 10))
        style.map("Primary.TButton",
                 background=[("active", COLORS["primary_dark"]), ("pressed", COLORS["primary_dark"])],
                 relief=[("pressed", "flat"), ("active", "flat")])

        # Button styles - Secondary (Gray)
        style.configure("Secondary.TButton",
                       font=default_font,
                       background=COLORS["neutral_300"],
                       foreground=COLORS["text_primary"],
                       borderwidth=0,
                       focuscolor='none',
                       padding=(16, 10))
        style.map("Secondary.TButton",
                 background=[("active", COLORS["neutral_400"]), ("pressed", COLORS["neutral_400"])],
                 relief=[("pressed", "flat"), ("active", "flat")])

        # Button styles - Success (Green)
        style.configure("Success.TButton",
                       font=default_font,
                       background=COLORS["success"],
                       foreground=COLORS["white"],
                       borderwidth=0,
                       focuscolor='none',
                       padding=(16, 10))
        style.map("Success.TButton",
                 background=[("active", "#059669"), ("pressed", "#059669")],
                 relief=[("pressed", "flat"), ("active", "flat")])

        # Frame styles
        style.configure("Header.TFrame", background=COLORS["white"], relief="flat")
        style.configure("Card.TFrame", background=COLORS["white"], relief="flat", borderwidth=1)
        style.configure("Status.TFrame", background=COLORS["primary_light"], relief="flat")

        # Label styles
        style.configure("SectionTitle.TLabel",
                       font=title_font,
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"])
        style.configure("StatusLabel.TLabel",
                       font=("Segoe UI", 13, "bold"),
                       background=COLORS["primary_light"],
                       foreground=COLORS["primary_dark"])
        style.configure("StatusValue.TLabel",
                       font=default_font,
                       background=COLORS["primary_light"],
                       foreground=COLORS["text_primary"])
        style.configure("Info.TLabel",
                       font=default_font,
                       background=COLORS["white"],
                       foreground=COLORS["text_secondary"])
        style.configure("ToolbarLabel.TLabel",
                       font=("Segoe UI", 14, "bold"),
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"])
        style.configure("FilterLabel.TLabel",
                       font=default_font,
                       background=COLORS["white"],
                       foreground=COLORS["text_secondary"])

        # Treeview (Table) styles
        style.configure("Modern.Treeview",
                       font=("Segoe UI", 13),
                       background=COLORS["white"],
                       foreground=COLORS["text_primary"],
                       fieldbackground=COLORS["white"],
                       borderwidth=0,
                       rowheight=42)
        style.configure("Modern.Treeview.Heading",
                       font=heading_font,
                       background=COLORS["neutral_100"],
                       foreground=COLORS["text_primary"],
                       relief="flat",
                       borderwidth=0)
        style.map("Modern.Treeview.Heading",
                 background=[("active", COLORS["neutral_200"])])
        style.map("Modern.Treeview",
                 background=[("selected", COLORS["primary_light"])],
                 foreground=[("selected", COLORS["text_primary"])])

        # Configure striped rows
        self.tree_stripe_color = COLORS["neutral_50"]

        # Notebook (Tabs) styles - Harmonized & Equal Height
        style.configure("TNotebook",
                       background=COLORS["neutral_50"],
                       borderwidth=0,
                       relief="flat",
                       lightcolor=COLORS["neutral_50"],
                       darkcolor=COLORS["neutral_50"])

        style.configure("TNotebook.Tab",
                       font=("Segoe UI", 14, "bold"),
                       padding=(16, 10),  # Altura padronizada (vertical reduzido)
                       background=COLORS["neutral_200"],
                       foreground=COLORS["text_secondary"],
                       relief="flat",  # Sem efeito 3D
                       borderwidth=0,
                       lightcolor=COLORS["neutral_200"],
                       darkcolor=COLORS["neutral_200"],
                       focuscolor=COLORS["white"])  # Foco também branco

        style.map("TNotebook.Tab",
                 background=[("selected", COLORS["white"]),
                            ("active", COLORS["white"])],
                 foreground=[("selected", COLORS["primary"]),
                            ("active", COLORS["primary"])],
                 relief=[("selected", "flat"),
                        ("active", "flat")],  # Mantém flat quando selecionada/ativa
                 borderwidth=[("selected", 0),
                             ("active", 0)],  # Sem bordas quando selecionada/ativa
                 lightcolor=[("selected", COLORS["white"]),
                            ("active", COLORS["white"])],
                 darkcolor=[("selected", COLORS["white"]),
                           ("active", COLORS["white"])]
                 )

        # Status bar style
        style.configure("StatusBar.TFrame",
                       background=COLORS["neutral_800"],
                       relief="flat")
        style.configure("StatusBar.TLabel",
                       font=("Segoe UI", 12),
                       background=COLORS["neutral_800"],
                       foreground=COLORS["white"])

        self.db_manager = DuckDBManager()
        self.llm_client = LMStudioClient()
        # Optional Gemini client for online search if configured
        self.gemini_client = GeminiClient() if ONLINE_SEARCH_PROVIDER.lower() == "gemini" else None
        self.processor = DocumentProcessor(
            db_manager=self.db_manager,
            llm_client=self.llm_client,
            online_search_client=self.gemini_client,
            chunk_strategy=ChunkStrategy(),
            fields=[*DEFAULT_FIELDS, *ADDITIONAL_FIELDS],
        )

        self.selected_files: list[Path] = []
        self.status_queue: queue.Queue[tuple[str, Path]] = queue.Queue()

        self.processing_queue = ProcessingQueue(
            processor=self.processor,
            # workers usa MAX_WORKERS do .env por padrão
            on_started=self._on_job_started,
            on_finished=self._on_job_finished,
            on_failed=self._on_job_failed,
        )
        self.processing_queue.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Main container with padding
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        notebook = ttk.Notebook(main_container)
        notebook.pack(fill="both", expand=True)

        self.setup_tab = SetupTab(notebook, self)
        self.processing_tab = ProcessingTab(notebook, self)
        self.results_tab = ResultsTab(notebook, self)
        notebook.add(self.setup_tab, text="⚙️ Configuração")
        notebook.add(self.processing_tab, text="⚡ Processamento")
        notebook.add(self.results_tab, text="📊 Resultados")

        # Status bar at the bottom
        self.status_bar = ttk.Frame(main_container, style="StatusBar.TFrame", height=32)
        self.status_bar.pack(fill="x", side="bottom", pady=(8, 0))

        self.status_text = tk.StringVar(value="Pronto")
        status_label = ttk.Label(self.status_bar, textvariable=self.status_text, style="StatusBar.TLabel")
        status_label.pack(side="left", padx=12, pady=6)

        # Version info on the right
        version_label = ttk.Label(self.status_bar, text="FDS Extractor v1.0", style="StatusBar.TLabel")
        version_label.pack(side="right", padx=12, pady=6)

        # Menu bar with quick actions
        menubar = tk.Menu(self)
        menu_file = tk.Menu(menubar, tearoff=0)
        menu_file.add_command(label="Abrir pasta de exportacao", command=self._open_export_folder)
        menu_file.add_separator()
        menu_file.add_command(label="Exportar CSV", command=self._menu_export_csv)
        menu_file.add_command(label="Exportar Excel", command=self._menu_export_excel)
        menu_file.add_separator()
        menu_file.add_command(label="Sair", command=self._on_close)
        menubar.add_cascade(label="Arquivo", menu=menu_file)
        self.config(menu=menubar)

        self.after(200, self._drain_status_queue)
        self.after(100, self._check_llm_connection)
        self.after(400, self.results_tab.refresh)
        # Progress tracking
        self._progress_total: int = 0
        self._progress_done: int = 0

    def set_selected_files(self, files: list[Path]) -> None:
        """Set the list of files chosen by the user."""
        self.selected_files = files
        for file_path in files:
            self.processing_tab.update_status(file_path, "Na fila", field_details={})

    def start_processing(self) -> None:
        """Queue selected files for background processing."""
        logger.info("Starting processing of %s file(s)", len(self.selected_files))
        self._update_status_bar(f"Iniciando processamento de {len(self.selected_files)} arquivo(s)...")
        # Setup and show integrated progress bar
        self._progress_total = len(self.selected_files)
        self._progress_done = 0
        if self._progress_total > 0:
            self.setup_tab.show_progress(self._progress_total)
        for file_path in self.selected_files:
            self.processing_tab.update_status(file_path, "Na fila", field_details={})
            mode = self.processing_tab.get_mode(file_path)
            self.processing_queue.enqueue(file_path, mode=mode)

    def _on_job_started(self, _: str, file_path: Path) -> None:
        self.status_queue.put(("Processando", file_path))

    def _on_job_finished(self, _: str, file_path: Path) -> None:
        self.status_queue.put(("Concluido", file_path))

    def _on_job_failed(self, file_path: Path, exc: Exception) -> None:
        logger.error("Erro no processamento de %s: %s", file_path, exc)
        self.status_queue.put(("Erro", file_path))
        # Show user-friendly error dialog
        self._show_error_dialog(
            title="Falha no processamento",
            message=f"O arquivo '{file_path.name}' falhou ao processar.",
            details=str(exc),
        )

    def _drain_status_queue(self) -> None:
        """Apply status updates generated by background workers."""
        refresh_results = False
        while not self.status_queue.empty():
            status, file_path = self.status_queue.get()
            field_details: dict[str, dict[str, object]] = {}

            if status == "Concluido":
                document_id = self.db_manager.get_document_id(file_path)
                if document_id:
                    details = self.db_manager.get_field_details(document_id)
                    if details:
                        field_details = details
                    refresh_results = True
            elif status == "Erro":
                refresh_results = True

            self.processing_tab.update_status(
                file_path,
                status,
                field_details=field_details,
            )

            # Update progress bar
            if status in {"Concluido", "Erro"}:
                self._progress_done += 1
                self.setup_tab.update_progress(self._progress_done, self._progress_total)

        if refresh_results:
            self.results_tab.refresh()

        # Hide progress bar when all tasks are done
        if self._progress_done >= self._progress_total and self._progress_total > 0:
            self.setup_tab.hide_progress()
            self._update_status_bar(f"Processamento concluído - {self._progress_total} arquivo(s) processado(s)")

        self.after(200, self._drain_status_queue)

    def _check_llm_connection(self) -> None:
        """Check local LLM availability (Ollama/LM Studio) and update UI."""
        ok = self.llm_client.test_connection()
        status = "LLM local conectado." if ok else "LLM local nao respondeu."
        # Append Gemini info if configured
        try:
            if self.gemini_client and self.gemini_client.test_connection():
                status += " | Gemini pronto para pesquisa online."
        except Exception:
            pass
        self.setup_tab.update_llm_status(status)
        self._update_status_bar("Pronto - Conexões verificadas")

    def _update_status_bar(self, message: str) -> None:
        """Update the status bar with a message."""
        self.status_text.set(message)

    def _on_close(self) -> None:
        """Cleanup resources when the user closes the app."""
        logger.info("Shutting down application.")
        self._update_status_bar("Encerrando...")
        self.processing_queue.stop()
        self.destroy()

    def _open_export_folder(self) -> None:
        """Open the export/data folder in the system file explorer."""
        try:
            path = DATA_DIR
            path.mkdir(parents=True, exist_ok=True)
            # Windows
            if os.name == 'nt':
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                # macOS or Linux fallbacks
                import subprocess
                if sys.platform == 'darwin':
                    subprocess.run(['open', str(path)], check=False)
                else:
                    subprocess.run(['xdg-open', str(path)], check=False)
        except Exception as exc:  # noqa: BLE001
            self._show_error_dialog(
                title="Falha ao abrir pasta",
                message="Nao foi possivel abrir a pasta de exportacao.",
                details=str(exc),
            )

    def _menu_export_csv(self) -> None:
        """Trigger CSV export using the Results tab logic."""
        try:
            self.results_tab._export_csv()  # uses existing dialog and filtered data
        except Exception as exc:  # noqa: BLE001
            self._show_error_dialog(
                title="Erro ao exportar CSV",
                message="Nao foi possivel exportar os resultados para CSV.",
                details=str(exc),
            )

    def _menu_export_excel(self) -> None:
        """Trigger Excel export using the Results tab logic."""
        try:
            self.results_tab._export_excel()  # uses existing dialog and filtered data
        except Exception as exc:  # noqa: BLE001
            self._show_error_dialog(
                title="Erro ao exportar Excel",
                message="Nao foi possivel exportar os resultados para Excel.",
                details=str(exc),
            )

    def _show_error_dialog(
        self,
        *,
        title: str,
        message: str,
        details: str | None = None,
        suggestions: str | None = None,
    ) -> None:
        """Show a modern modal error dialog with details and copy-to-clipboard.

        - message: short summary line
        - details: raw exception or traceback
        - suggestions: optional actionable hints to help the user recover
        """

        def _copy(text: str) -> None:
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
                self.update_idletasks()
            except Exception:
                pass

        dlg = tk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("950x750")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(True, True)
        dlg.configure(bg=COLORS["white"])

        # Header with error icon
        header = ttk.Frame(dlg, style="Header.TFrame")
        header.pack(fill="x")

        title_frame = ttk.Frame(header, style="Header.TFrame")
        title_frame.pack(fill="x", padx=24, pady=20)
        ttk.Label(title_frame, text="⚠️", font=("Segoe UI", 36), style="SectionTitle.TLabel").pack(side="left", padx=(0, 16))

        title_content = ttk.Frame(title_frame, style="Header.TFrame")
        title_content.pack(side="left", fill="both", expand=True)
        ttk.Label(title_content, text=title, font=("Segoe UI", 18, "bold"), style="SectionTitle.TLabel").pack(anchor="w")
        error_label = ttk.Label(title_content, text=message, font=("Segoe UI", 13), wraplength=750, justify="left")
        error_label.configure(foreground=COLORS["error"])
        error_label.pack(anchor="w", pady=(4, 0))

        # Main content area
        content_frame = ttk.Frame(dlg)
        content_frame.configure(bg=COLORS["white"])
        content_frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        if suggestions:
            # Suggestions section
            suggestions_frame = ttk.Frame(content_frame, style="Card.TFrame")
            suggestions_frame.pack(fill="x", pady=(0, 16))

            ttk.Label(suggestions_frame, text="💡 Sugestões", font=("Segoe UI", 14, "bold"), style="SectionTitle.TLabel").pack(anchor="w", padx=16, pady=(12, 8))

            txt_sug = tk.Text(suggestions_frame, height=6, wrap="word", font=("Segoe UI", 12), relief="flat", bg=COLORS["warning_light"], fg=COLORS["text_primary"])
            txt_sug.insert("1.0", suggestions)
            txt_sug.configure(state="disabled")
            txt_sug.pack(fill="x", padx=16, pady=(0, 12))

        if details:
            # Details section
            details_frame = ttk.Frame(content_frame, style="Card.TFrame")
            details_frame.pack(fill="both", expand=True)

            detail_header = ttk.Frame(details_frame, style="Card.TFrame")
            detail_header.pack(fill="x", padx=16, pady=(12, 8))
            ttk.Label(detail_header, text="📋 Detalhes Técnicos", font=("Segoe UI", 14, "bold"), style="SectionTitle.TLabel").pack(side="left")
            ttk.Button(detail_header, text="📋 Copiar", command=lambda: _copy(details), style="Secondary.TButton").pack(side="right")

            txt = tk.Text(details_frame, height=15, wrap="word", font=("Consolas", 11), relief="flat", bg=COLORS["neutral_100"], fg=COLORS["text_primary"])
            txt.insert("1.0", details)
            txt.configure(state="disabled")

            # Add scrollbar for details
            scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=scrollbar.set)

            txt.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=(0, 12))
            scrollbar.pack(side="right", fill="y", padx=(0, 16), pady=(0, 12))

        # Button footer
        footer = ttk.Frame(dlg, style="Header.TFrame")
        footer.pack(fill="x", pady=(12, 0))

        btn_frame = ttk.Frame(footer, style="Header.TFrame")
        btn_frame.pack(fill="x", padx=24, pady=16)
        ttk.Button(btn_frame, text="Fechar", command=dlg.destroy, style="Primary.TButton").pack(side="right")


def run_app() -> None:
    """Entrypoint for launching the GUI."""
    app = Application()
    app.mainloop()


class ProgressDialog:
    """Modern modal progress dialog with enhanced styling."""

    def __init__(self, parent: tk.Tk, total: int) -> None:
        self.parent = parent
        self.total = max(total, 1)
        self.top = tk.Toplevel(parent)
        self.top.title("Processamento em Andamento")

        # Configuração da janela - MOVÍVEL
        width = 700
        height = 280
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(True, True)  # Permite redimensionar
        self.top.configure(bg=COLORS["white"])

        # Centralizar na tela (não no parent)
        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.top.geometry(f"{width}x{height}+{x}+{y}")

        # Header with icon - PERMITE ARRASTAR
        header = ttk.Frame(self.top, style="Header.TFrame")
        header.pack(fill="x", pady=(0, 0))

        title_frame = ttk.Frame(header, style="Header.TFrame")
        title_frame.pack(fill="x", padx=24, pady=16)
        ttk.Label(title_frame, text="⚡", font=("Segoe UI", 32), style="SectionTitle.TLabel").pack(side="left", padx=(0, 12))
        title_label = ttk.Label(title_frame, text="Processando Arquivos", font=("Segoe UI", 18, "bold"), style="SectionTitle.TLabel")
        title_label.pack(side="left")

        # Habilitar arrastar pela barra de título
        self._enable_drag(title_frame)

        # Main content
        frame = ttk.Frame(self.top)
        frame.configure(style="Card.TFrame")
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        # Status text
        self.label_var = tk.StringVar(value=f"Processando 0 de {self.total} arquivos...")
        status_label = ttk.Label(frame, textvariable=self.label_var, font=("Segoe UI", 14))
        status_label.pack(anchor="w", pady=(16, 8), padx=16)

        # Progress bar with modern styling
        progress_frame = ttk.Frame(frame, style="Card.TFrame")
        progress_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.bar = ttk.Progressbar(progress_frame, mode="determinate", maximum=self.total, length=620)
        self.bar.pack(fill="x")

        # Percentage label
        self.percent_var = tk.StringVar(value="0%")
        percent_label = ttk.Label(frame, textvariable=self.percent_var, font=("Segoe UI", 16, "bold"))
        percent_label.configure(foreground=COLORS["primary"])
        percent_label.pack(anchor="center", pady=(8, 16))

        # Button frame
        btn_frame = ttk.Frame(frame, style="Card.TFrame")
        btn_frame.pack(fill="x", padx=16, pady=(8, 16))
        ttk.Button(btn_frame, text="Minimizar", command=self.top.withdraw, style="Secondary.TButton").pack(side="right")

        # Variáveis para arrastar
        self._drag_x = 0
        self._drag_y = 0

        # Ensure dialog stays on top initially
        self.top.attributes("-topmost", True)
        self.top.after(500, lambda: self.top.attributes("-topmost", False))

    def _enable_drag(self, widget) -> None:
        """Habilita arrastar a janela pelo widget."""
        widget.bind("<Button-1>", self._start_drag)
        widget.bind("<B1-Motion>", self._on_drag)
        # Cursor de "mover" quando passar o mouse
        widget.bind("<Enter>", lambda e: widget.configure(cursor="fleur"))
        widget.bind("<Leave>", lambda e: widget.configure(cursor=""))

    def _start_drag(self, event) -> None:
        """Inicia o arraste da janela."""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event) -> None:
        """Arrasta a janela."""
        x = self.top.winfo_x() + (event.x - self._drag_x)
        y = self.top.winfo_y() + (event.y - self._drag_y)
        self.top.geometry(f"+{x}+{y}")

    def show(self) -> None:
        self.top.deiconify()

    def update(self, current: int) -> None:
        current = max(0, min(current, self.total))
        percent = int((current / self.total) * 100) if self.total > 0 else 0
        self.label_var.set(f"Processando {current} de {self.total} arquivos...")
        self.percent_var.set(f"{percent}%")
        self.bar['value'] = current
        self.top.update_idletasks()

    def close(self) -> None:
        try:
            self.top.grab_release()
        except Exception:
            pass
        self.top.destroy()
