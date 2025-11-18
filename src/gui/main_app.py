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

        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", pady=(0, 24))
        ttk.Button(top_frame, text="Selecionar pasta", command=self._select_folder).pack(side="left")
        self._btn_reload = ttk.Button(top_frame, text="Recarregar pasta", command=self._reload_folder)
        self._btn_reload.pack(side="left", padx=(16, 0))
        ttk.Button(top_frame, text="Adicionar a fila", command=self._enqueue_files).pack(side="left", padx=(16, 0))
        ttk.Label(top_frame, textvariable=self.folder_var).pack(side="left", padx=(24, 0))

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

        ttk.Label(self, textvariable=self.llm_status_var, foreground="#1e88e5").pack(anchor="w", pady=(0, 16))

        columns = ("documento", "tamanho")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        self.tree.heading("documento", text="Documento")
        self.tree.heading("tamanho", text="Tamanho (KB)")
        self.tree.column("documento", width=1000, anchor="w")
        self.tree.column("tamanho", width=220, anchor="center")
        self.tree.pack(fill="both", expand=True)

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
            files = list_supported_files(path)
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

        for file_path in files:
            try:
                size_kb = file_path.stat().st_size / 1024
            except Exception:
                size_kb = 0.0
            self.tree.insert(
                "",
                "end",
                iid=str(file_path),
                values=(file_path.name, f"{size_kb:.1f}"),
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
        super().__init__(master, padding=16)
        self.controller = controller
        self._modes: dict[str, str] = {}  # iid -> mode ("online"|"local")
        self._mode_editor: ttk.Combobox | None = None

        # Toolbar for bulk actions (set mode for selected rows)
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(toolbar, text="Alterar modo:").pack(side="left")
        ttk.Button(toolbar, text="Modo: Online", command=self._set_selected_mode_online).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Modo: Local", command=self._set_selected_mode_local).pack(side="left", padx=(6, 0))

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
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        self.tree.heading("documento", text="Documento")
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
        
        # Add horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)
        self.tree.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")

        self.tree.tag_configure("valid", background="#e8f5e9")
        self.tree.tag_configure("warning", background="#fff8e1")
        self.tree.tag_configure("invalid", background="#ffebee")
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
        super().__init__(master, padding=16)
        self.controller = controller
        self._results: list[dict[str, object]] = []
        self._filtered_results: list[dict[str, object]] = []

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Button(toolbar, text="Atualizar", command=self.refresh).pack(side="left")
        ttk.Button(toolbar, text="Exportar CSV", command=self._export_csv).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Exportar Excel", command=self._export_excel).pack(side="left", padx=(8, 0))

        ttk.Label(toolbar, text="Status proc.:").pack(side="left", padx=(16, 4))
        self.status_filter = tk.StringVar(value="Todos")
        status_combo = ttk.Combobox(
            toolbar,
            textvariable=self.status_filter,
            values=("Todos", "success", "failed", "partial"),
            state="readonly",
            width=10,
        )
        status_combo.pack(side="left")
        status_combo.current(0)
        status_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        ttk.Label(toolbar, text="Validacao:").pack(side="left", padx=(16, 4))
        self.validation_filter = tk.StringVar(value="Todas")
        validation_combo = ttk.Combobox(
            toolbar,
            textvariable=self.validation_filter,
            values=("Todas", "valid", "warning", "invalid"),
            state="readonly",
            width=10,
        )
        validation_combo.pack(side="left")
        validation_combo.current(0)
        validation_combo.bind("<<ComboboxSelected>>", lambda _: self._apply_filters())

        ttk.Label(toolbar, text="Buscar:").pack(side="left", padx=(16, 4))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=24)
        search_entry.pack(side="left")
        self.search_var.trace_add("write", lambda *_: self._apply_filters())

        self.info_var = tk.StringVar(value="0 registros carregados.")
        ttk.Label(toolbar, textvariable=self.info_var).pack(side="left", padx=(12, 0))

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
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)
        self.tree.heading("documento", text="Documento")
        self.tree.heading("status", text="Status proc.")
        self.tree.heading("nome_produto", text="Produto")
        self.tree.heading("fabricante", text="Fabricante")
        self.tree.heading("numero_onu", text="ONU")
        self.tree.heading("numero_cas", text="CAS")
        self.tree.heading("classe_onu", text="Classe")
        self.tree.heading("grupo_embalagem", text="Grupo Emb")
        self.tree.heading("incompatibilidades", text="Incompatibilidades")
        self.tree.heading("processado_em", text="Processado em")

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
        
        # Add horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)
        self.tree.pack(side="top", fill="both", expand=True)
        h_scrollbar.pack(side="bottom", fill="x")

        # Context menu (right-click) for quick actions
        self._context_menu = tk.Menu(self, tearoff=0)
        self._context_menu.add_command(label="Reprocessar selecao (online)", command=self._reprocess_selected_online)
        self.tree.bind("<Button-3>", self._on_results_right_click)

        self.tree.tag_configure("valid", background="#e8f5e9")
        self.tree.tag_configure("warning", background="#fff8e1")
        self.tree.tag_configure("invalid", background="#ffebee")

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
        self.title("FDS Extractor MVP")
        self.geometry("1600x1000")
        
        # Configure LARGE fonts for better readability (2x size)
        default_font = ("TkDefaultFont", 16, "normal")
        text_font = ("TkTextFont", 16)
        fixed_font = ("TkFixedFont", 14)
        menu_font = ("TkMenuFont", 16)
        heading_font = ("TkDefaultFont", 17, "bold")
        
        self.option_add("*TCombobox*Listbox*Font", default_font)
        self.option_add("*Font", default_font)
        self.option_add("*TkDefaultFont", default_font)
        self.option_add("*TkTextFont", text_font)
        self.option_add("*TkFixedFont", fixed_font)
        self.option_add("*TkMenuFont", menu_font)
        
        # Configure ttk styles with MUCH LARGER fonts and buttons
        style = ttk.Style(self)
        style.configure(".", font=default_font)
        style.configure("Treeview", font=("TkDefaultFont", 15), rowheight=40)
        style.configure("Treeview.Heading", font=heading_font)
        style.configure("TButton", font=("TkDefaultFont", 16), padding=12)
        style.configure("TLabel", font=("TkDefaultFont", 16))
        style.configure("TEntry", font=("TkDefaultFont", 16))
        style.configure("TCombobox", font=("TkDefaultFont", 16))

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
            workers=1,
            on_started=self._on_job_started,
            on_finished=self._on_job_finished,
            on_failed=self._on_job_failed,
        )
        self.processing_queue.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.setup_tab = SetupTab(notebook, self)
        self.processing_tab = ProcessingTab(notebook, self)
        self.results_tab = ResultsTab(notebook, self)
        notebook.add(self.setup_tab, text="Configuracao")
        notebook.add(self.processing_tab, text="Processamento")
        notebook.add(self.results_tab, text="Resultados")

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
        self._progress_dialog: ProgressDialog | None = None
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
        # Setup and show progress dialog
        self._progress_total = len(self.selected_files)
        self._progress_done = 0
        if self._progress_total > 0:
            self._progress_dialog = ProgressDialog(self, total=self._progress_total)
            self._progress_dialog.show()
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
                if self._progress_dialog:
                    self._progress_dialog.update(self._progress_done)

        if refresh_results:
            self.results_tab.refresh()

        # Close progress dialog when all tasks are done
        if self._progress_dialog and self._progress_done >= self._progress_total and self._progress_total > 0:
            self._progress_dialog.close()
            self._progress_dialog = None

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

    def _on_close(self) -> None:
        """Cleanup resources when the user closes the app."""
        logger.info("Shutting down application.")
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
        """Show a modal error dialog with details and copy-to-clipboard.

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
        dlg.geometry("900x700")
        dlg.transient(self)
        dlg.grab_set()
        dlg.resizable(True, True)

        frame = ttk.Frame(dlg, padding=24)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=message, foreground="#d32f2f", wraplength=820, justify="left").pack(anchor="w")

        if suggestions:
            ttk.Separator(frame).pack(fill="x", pady=16)
            ttk.Label(frame, text="Sugestoes:", foreground="#455a64").pack(anchor="w")
            txt_sug = tk.Text(frame, height=6, wrap="word", font=("TkDefaultFont", 14))
            txt_sug.insert("1.0", suggestions)
            txt_sug.configure(state="disabled")
            txt_sug.pack(fill="x", padx=0, pady=(4, 0))

        if details:
            ttk.Separator(frame).pack(fill="x", pady=16)
            header = ttk.Frame(frame)
            header.pack(fill="x")
            ttk.Label(header, text="Detalhes do erro:").pack(side="left")
            ttk.Button(header, text="Copiar", command=lambda: _copy(details)).pack(side="right")

            txt = tk.Text(frame, height=15, wrap="word", font=("TkFixedFont", 13))
            txt.insert("1.0", details)
            txt.configure(state="disabled")
            txt.pack(fill="both", expand=True)

        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=(20, 0))
        ttk.Button(btns, text="Fechar", command=dlg.destroy).pack(side="right")


def run_app() -> None:
    """Entrypoint for launching the GUI."""
    app = Application()
    app.mainloop()


class ProgressDialog:
    """Simple modal progress dialog with a label and a progress bar."""

    def __init__(self, parent: tk.Tk, total: int) -> None:
        self.parent = parent
        self.total = max(total, 1)
        self.top = tk.Toplevel(parent)
        self.top.title("Processando arquivos...")
        self.top.geometry("800x200")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.resizable(False, False)

        frame = ttk.Frame(self.top, padding=24)
        frame.pack(fill="both", expand=True)

        self.label_var = tk.StringVar(value=f"Processando 0 de {self.total}... (0%)")
        ttk.Label(frame, textvariable=self.label_var).pack(anchor="w", pady=(0, 16))

        self.bar = ttk.Progressbar(frame, mode="determinate", maximum=self.total, length=720)
        self.bar.pack(fill="x")
        
        # Percentage label below progress bar
        self.percent_var = tk.StringVar(value="0%")
        ttk.Label(frame, textvariable=self.percent_var, foreground="#1565c0").pack(anchor="center", pady=(8, 0))

        ttk.Button(frame, text="Minimizar", command=self.top.withdraw).pack(anchor="e", pady=(20, 0))

        # Ensure dialog stays on top while processing
        self.top.attributes("-topmost", True)
        self.top.after(500, lambda: self.top.attributes("-topmost", False))

    def show(self) -> None:
        self.top.deiconify()

    def update(self, current: int) -> None:
        current = max(0, min(current, self.total))
        percent = int((current / self.total) * 100) if self.total > 0 else 0
        self.label_var.set(f"Processando {current} de {self.total}... ({percent}%)")
        self.percent_var.set(f"{percent}%")
        self.bar['value'] = current
        self.top.update_idletasks()

    def close(self) -> None:
        try:
            self.top.grab_release()
        except Exception:
            pass
        self.top.destroy()
