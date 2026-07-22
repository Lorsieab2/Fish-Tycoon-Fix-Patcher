#!/usr/bin/env python3
"""Tkinter GUI for the offline Fish Tycoon bug-fix patcher."""

from __future__ import annotations

from argparse import Namespace
import contextlib
import io
import json
from pathlib import Path
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

import offline_fish_tycoon_patcher as patcher


APP_NAME = "Fish Tycoon Fix Patcher"
RELEASES_URL = "https://github.com/Lorsieab2/Fish-Tycoon-Fix-Patcher/releases"
SETTINGS_FILE = "patcher_local_settings.json"
CREATOR_MESSAGE = (
    "Created with Codex AI in collaboration with Lorsieab2. This passion project "
    "repairs a verified Fish Tycoon PC gameplay defect. No copyright infringement "
    "is intended; please support the original game creators. :)"
)


def base_dir() -> Path:
    return Path(__file__).resolve().parent


def default_manifest() -> Path:
    adjacent = base_dir() / "manifest.json"
    if adjacent.is_file():
        return adjacent
    return base_dir().parent / "patches" / "fish-tycoon-fixes" / "manifest.json"


def settings_path(root: Path | None = None) -> Path:
    return (root or base_dir()) / SETTINGS_FILE


def load_paths(path: Path | None = None) -> dict[str, str]:
    try:
        value = json.loads((path or settings_path()).read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        key: str(value[key]).strip()
        for key in ("game_dir", "output_dir", "backup_dir")
        if isinstance(value.get(key), str) and str(value[key]).strip()
    }


def default_output_dir(game_dir: str, saved: str = "") -> str:
    if saved.strip():
        return saved.strip()
    if game_dir.strip():
        return str(Path(game_dir).parent / "Fish Tycoon - Fixed")
    return ""


def save_paths(values: dict[str, str], path: Path | None = None) -> None:
    destination = path or settings_path()
    destination.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")


class FishTycoonPatcherGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title(APP_NAME)
        root.geometry("900x700")
        root.minsize(780, 620)
        self.busy = False
        self.setting_vars: dict[str, tk.BooleanVar] = {}

        saved = load_paths()
        saved_game = saved.get("game_dir", "")
        self.game_dir = tk.StringVar(value=saved_game)
        self.output_dir = tk.StringVar(value=default_output_dir(saved_game, saved.get("output_dir", "")))
        self.manifest = tk.StringVar(value=str(default_manifest()))
        self.backup_dir = tk.StringVar(value=saved.get("backup_dir", ""))
        self.status = tk.StringVar(value="Ready. Close Fish Tycoon before patching.")

        self._build()
        self.load_manifest()
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.pack(fill="both", expand=True)

        title = ttk.Label(outer, text=APP_NAME, font=("Segoe UI", 18, "bold"))
        title.pack(anchor="w")
        subtitle = ttk.Label(
            outer,
            text="Offline, manifest-driven patcher for the supported classic Windows Fish Tycoon build",
        )
        subtitle.pack(anchor="w", pady=(0, 4))
        link = tk.Label(outer, text="Check for updates", fg="#0066cc", cursor="hand2", font=("Segoe UI", 9, "underline"))
        link.pack(anchor="w", pady=(0, 8))
        link.bind("<Button-1>", lambda _event: webbrowser.open(RELEASES_URL))

        paths = ttk.LabelFrame(outer, text="Files and folders", padding=10)
        paths.pack(fill="x")
        self._path_row(paths, 0, "Vanilla game folder", self.game_dir, self.browse_game, self.open_game_folder)
        self._path_row(paths, 1, "Patch manifest", self.manifest, self.browse_manifest)
        self._path_row(paths, 2, "Modded output folder", self.output_dir, self.browse_output, self.open_output_folder)
        self._path_row(paths, 3, "Backup folder (restore)", self.backup_dir, self.browse_backup, self.open_backup_folder)

        self.settings_frame = ttk.LabelFrame(outer, text="Main patches", padding=10)
        self.settings_frame.pack(fill="x", pady=(10, 0))

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=10)
        self.dry_button = ttk.Button(actions, text="Dry Run (Validate Only)", command=lambda: self.start_apply(True))
        self.dry_button.pack(side="left")
        self.apply_button = tk.Button(
            actions,
            text="Create Fixed Copy",
            command=lambda: self.start_apply(False),
            bg="#07852f",
            fg="white",
            activebackground="#056d27",
            activeforeground="white",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=5,
        )
        self.apply_button.pack(side="left", padx=8)
        self.restore_button = ttk.Button(actions, text="Restore Output EXE from Backup", command=self.start_restore)
        self.restore_button.pack(side="left")

        log_frame = ttk.LabelFrame(outer, text="Patcher log", padding=8)
        log_frame.pack(fill="both", expand=True)
        self.log = tk.Text(log_frame, wrap="word", height=15, font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(8, 2))
        ttk.Label(outer, text=CREATOR_MESSAGE, wraplength=850, foreground="#555555").pack(anchor="w")

    def _path_row(self, parent: tk.Widget, row: int, label: str, value: tk.StringVar,
                  command: object, open_command: object | None = None) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=3)
        ttk.Entry(parent, textvariable=value).grid(row=row, column=1, sticky="ew", padx=8, pady=3)
        ttk.Button(parent, text="Browse...", command=command).grid(row=row, column=2, pady=3)
        if open_command is not None:
            ttk.Button(parent, text="Open Folder", command=open_command).grid(row=row, column=3, padx=(6, 0), pady=3)
        parent.columnconfigure(1, weight=1)

    def open_folder(self, value: tk.StringVar, label: str) -> None:
        raw = value.get().strip().strip('"')
        if not raw:
            messagebox.showerror(APP_NAME, f"Select the {label} first.")
            return
        folder = Path(raw).expanduser()
        if not folder.is_dir():
            messagebox.showerror(APP_NAME, f"The {label} does not exist:\n\n{folder}")
            return
        try:
            subprocess.Popen(["explorer", str(folder.resolve())])
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not open the {label}:\n\n{exc}")

    def open_game_folder(self) -> None:
        self.open_folder(self.game_dir, "vanilla game folder")

    def open_output_folder(self) -> None:
        self.open_folder(self.output_dir, "modded EXE folder")

    def open_backup_folder(self) -> None:
        self.open_folder(self.backup_dir, "backup folder")

    def browse_game(self) -> None:
        selected = filedialog.askdirectory(title="Select the folder containing Fish Tycoon.exe")
        if selected:
            self.game_dir.set(selected)
            if not self.output_dir.get().strip():
                game = Path(selected)
                self.output_dir.set(str(game.parent / "Fish Tycoon - Fixed"))

    def browse_manifest(self) -> None:
        selected = filedialog.askopenfilename(title="Select manifest.json", filetypes=[("JSON", "*.json")])
        if selected:
            self.manifest.set(selected)
            self.load_manifest()

    def browse_output(self) -> None:
        selected = filedialog.askdirectory(title="Select or create the parent location for the fixed folder")
        if selected:
            candidate = Path(selected)
            if candidate.name != "Fish Tycoon - Fixed":
                candidate /= "Fish Tycoon - Fixed"
            self.output_dir.set(str(candidate))

    def browse_backup(self) -> None:
        selected = filedialog.askdirectory(title="Select a timestamped Fish Tycoon patch backup folder")
        if selected:
            self.backup_dir.set(selected)

    def load_manifest(self) -> bool:
        for child in self.settings_frame.winfo_children():
            child.destroy()
        self.setting_vars.clear()
        try:
            manifest = patcher.read_json(Path(self.manifest.get()).expanduser().resolve())
            settings = patcher.manifest_settings(manifest)
        except Exception as exc:
            ttk.Label(self.settings_frame, text=f"Manifest could not be loaded: {exc}", foreground="#b00020").pack(anchor="w")
            return False
        for setting_id, value in settings.items():
            var = tk.BooleanVar(value=bool(value.get("default", False)))
            self.setting_vars[setting_id] = var
            row = ttk.Frame(self.settings_frame)
            row.pack(fill="x", pady=2)
            ttk.Checkbutton(row, text=str(value.get("name", setting_id)), variable=var).pack(anchor="w")
            ttk.Label(row, text=str(value.get("description", "")), wraplength=820, foreground="#444444").pack(anchor="w", padx=(24, 0))
        return True

    def selected_settings(self) -> list[str]:
        return sorted(key for key, value in self.setting_vars.items() if value.get())

    def apply_namespace(self, dry_run: bool) -> Namespace:
        game = self.game_dir.get().strip().strip('"')
        manifest = self.manifest.get().strip().strip('"')
        if not game or not manifest:
            raise patcher.PatchError("Vanilla game folder and patch manifest are required.")
        return Namespace(
            game_dir=game,
            manifest=manifest,
            output_dir=self.output_dir.get().strip().strip('"') or None,
            dry_run=dry_run,
            enable=self.selected_settings(),
            disable=None,
            disable_all=True,
        )

    def start_apply(self, dry_run: bool) -> None:
        if self.busy or not self.load_manifest():
            return
        try:
            args = self.apply_namespace(dry_run)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        self.save_current_paths()
        self.run_worker("Dry run" if dry_run else "Apply", lambda: patcher.apply_manifest(args), args, dry_run)

    def start_restore(self) -> None:
        if self.busy:
            return
        backup = self.backup_dir.get().strip().strip('"')
        if not backup:
            messagebox.showerror(APP_NAME, "Select a timestamped backup folder first.")
            return
        args = Namespace(
            backup_dir=backup,
            output_dir=self.output_dir.get().strip().strip('"') or None,
        )
        self.save_current_paths()
        self.run_worker("Restore", lambda: patcher.restore_backup(args))

    def run_worker(self, label: str, operation: object, context_args: object | None = None,
                   dry_run: bool = False) -> None:
        self.busy = True
        self.set_buttons("disabled")
        self.status.set(f"{label} in progress...")
        self.append_log(f"\n=== {label} ===\n")

        def worker() -> None:
            stream = io.StringIO()
            result = 3
            error = ""
            try:
                with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    result = int(operation())
            except Exception as exc:
                error = str(exc)
                stream.write(f"ERROR: {exc}\n")
            summary = getattr(context_args, "last_apply_summary", None) if context_args is not None else None
            self.root.after(0, lambda: self.finish_worker(label, result, stream.getvalue(), error, summary, dry_run))

        threading.Thread(target=worker, daemon=True).start()

    def finish_worker(self, label: str, result: int, text: str, error: str,
                      summary: dict[str, object] | None = None, dry_run: bool = False) -> None:
        self.append_log(text)
        self.busy = False
        self.set_buttons("normal")
        if result == 0 and not error:
            self.status.set(f"{label} completed successfully.")
            self.save_current_paths()
            if summary and not dry_run:
                self.show_apply_success(summary)
            else:
                messagebox.showinfo(APP_NAME, f"{label} completed successfully.\n\nSee the patcher log for exact paths and hashes.")
        else:
            self.status.set(f"{label} failed.")
            messagebox.showerror(APP_NAME, error or "The operation failed. See the patcher log.")

    def set_buttons(self, state: str) -> None:
        self.dry_button.configure(state=state)
        self.apply_button.configure(state=state)
        self.restore_button.configure(state=state)

    def append_log(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def show_apply_success(self, summary: dict[str, object]) -> None:
        win = tk.Toplevel(self.root)
        win.title(f"{APP_NAME} complete")
        win.geometry("780x330")
        win.minsize(620, 280)
        win.transient(self.root)
        body = ttk.Frame(win, padding=14)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Fixed game created successfully!", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(body, text="Click any path below to open it in File Explorer.").pack(anchor="w", pady=(4, 12))
        paths = ttk.Frame(body)
        paths.pack(fill="x")
        paths.columnconfigure(1, weight=1)
        self.path_link_row(paths, 0, "Vanilla Game Folder Path", str(summary.get("vanilla_game_dir", "")))
        self.path_link_row(paths, 1, "Modded Game Folder Path", str(summary.get("output_dir", "")))
        self.path_link_row(paths, 2, "Backup Folder Path", str(summary.get("backup_dir", "")))
        ttk.Label(body, text="Have fun! -Lorsieab2 :)").pack(anchor="w", pady=(18, 0))
        ttk.Button(body, text="Close", command=win.destroy).pack(anchor="e", pady=(18, 0))

    def path_link_row(self, parent: tk.Widget, row: int, label: str, path: str) -> None:
        ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
        link = tk.Label(parent, text=path or "(not available)", fg="#0057c2",
                        font=("Segoe UI", 9, "bold"), cursor="hand2" if path else "arrow", anchor="w")
        link.grid(row=row, column=1, sticky="ew", pady=4)
        if path:
            link.bind("<Button-1>", lambda _event, value=path: self.open_path(value))

    def open_path(self, path: str) -> None:
        try:
            subprocess.Popen(["explorer", path])
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not open path:\n{path}\n\n{exc}")

    def save_current_paths(self) -> None:
        save_paths({
            "game_dir": self.game_dir.get().strip(),
            "output_dir": self.output_dir.get().strip(),
            "backup_dir": self.backup_dir.get().strip(),
        })

    def close(self) -> None:
        if self.busy and not messagebox.askyesno(APP_NAME, "An operation is running. Close the patcher anyway?"):
            return
        self.save_current_paths()
        self.root.destroy()


def main() -> int:
    root = tk.Tk()
    FishTycoonPatcherGUI(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
