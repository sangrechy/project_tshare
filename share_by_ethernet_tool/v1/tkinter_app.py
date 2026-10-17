"""Tkinter Dark Theme Monitor for Ethernet File Transfer.

Provides a clean dark UI fallback featuring dual upload/download speed tracking,
prominent Estimation Time (ETA), SMB latency, and safe resume controls.
"""
from __future__ import annotations

import ctypes
import os
import queue
import subprocess
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from backend.transfer_engine import (
    TransferEngine,
    DEFAULT_SOURCE,
    DEFAULT_DEST,
    format_bytes,
    format_duration,
)

# Dark Neumorphic Soft UI Palette
BG_COLOR = "#24272c"
CARD_BG = "#2a2d33"
TEXT_COLOR = "#f1f5f9"
TEXT_MUTED = "#9ba1a6"
SOURCE_ACCENT = "#a78bfa"
DEST_ACCENT = "#38bdf8"
ACCENT_COLOR = "#7c3aed"
DANGER_COLOR = "#ef4444"
SUCCESS_COLOR = "#10b981"
WARNING_COLOR = "#f59e0b"
TERMINAL_BG = "#191b1e"


class TkinterTransferMonitor(tk.Tk):
    def __init__(self, source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
        super().__init__()
        self.title("Robocopy Dual-Deck Safe Resume Monitor • Dark Soft UI")
        self.geometry("900x740")
        self.minsize(800, 620)
        self.configure(bg=BG_COLOR)

        self.events: queue.Queue = queue.Queue()
        self.engine = TransferEngine(on_event=self._engine_callback)
        self.engine.source_path = source_path
        self.engine.dest_path = dest_path
        self.engine.current_folder = os.path.basename(source_path.rstrip(r"\/")) or "Source"

        self._init_styles()
        self._build_ui()

        # Start periodic tasks
        self.after(100, self._drain_events)
        self.after(500, self._tick)
        self.after(300, lambda: self.engine.start_background_scan())

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _engine_callback(self, event_type: str, data: any) -> None:
        self.events.put((event_type, data))

    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 9))
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_COLOR)
        style.configure("Muted.TLabel", background=BG_COLOR, foreground=TEXT_MUTED, font=("Segoe UI", 8))
        style.configure("CardMuted.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 8))
        style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 15, "bold"))
        style.configure("Heading.TLabel", background=CARD_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10, "bold"))

        style.configure("Horizontal.TProgressbar", troughcolor=TERMINAL_BG, background=ACCENT_COLOR, bordercolor=CARD_BG)

        style.configure(
            "Action.TButton",
            background=CARD_BG,
            foreground=SOURCE_ACCENT,
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map("Action.TButton", background=[("active", ACCENT_COLOR)], foreground=[("active", "#ffffff")])

        style.configure(
            "Danger.TButton",
            background=CARD_BG,
            foreground="#f87171",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map("Danger.TButton", background=[("active", DANGER_COLOR)], foreground=[("active", "#ffffff")])

        style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT_COLOR, font=("Segoe UI", 9))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        # Header
        hdr = ttk.Frame(outer)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="Ethernet Transfer Cockpit", style="Title.TLabel").pack(side="left")

        right_hdr = ttk.Frame(hdr)
        right_hdr.pack(side="right")
        self.latency_lbl = ttk.Label(right_hdr, text="SMB Latency: …", foreground=WARNING_COLOR, font=("Segoe UI", 8, "bold"))
        self.latency_lbl.pack(side="left", padx=(0, 12))
        self.status_pill = ttk.Label(right_hdr, text="Checking system…", foreground=WARNING_COLOR, font=("Segoe UI", 9, "bold"))
        self.status_pill.pack(side="left")

        # DUAL-WING CARDS (Source Deck & Destination Deck)
        decks = ttk.Frame(outer)
        decks.pack(fill="x", pady=(0, 10))

        # Left Deck: Source System
        src_card = ttk.Frame(decks, style="Card.TFrame", padding=12)
        src_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ttk.Label(src_card, text="SOURCE: Network / Share", foreground=SOURCE_ACCENT, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(src_card, text=self.engine.source_path, style="CardMuted.TLabel").pack(anchor="w", pady=(2, 6))

        self.src_speed_var = tk.StringVar(value="0 B/s")
        ttk.Label(src_card, text="Upload / Read Outflow Speed:", style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(src_card, textvariable=self.src_speed_var, foreground=SOURCE_ACCENT, style="Card.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")

        self.src_meta_var = tk.StringVar(value="Capacity: — | Used: —")
        ttk.Label(src_card, textvariable=self.src_meta_var, style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))

        # Right Deck: Destination System
        dst_card = ttk.Frame(decks, style="Card.TFrame", padding=12)
        dst_card.pack(side="left", fill="both", expand=True, padx=(6, 0))

        ttk.Label(dst_card, text="DESTINATION: Target Storage", foreground=DEST_ACCENT, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ttk.Label(dst_card, text=self.engine.dest_path, style="CardMuted.TLabel").pack(anchor="w", pady=(2, 6))

        self.dst_speed_var = tk.StringVar(value="0 B/s")
        ttk.Label(dst_card, text="Download / Disk Write Speed:", style="CardMuted.TLabel").pack(anchor="w")
        ttk.Label(dst_card, textvariable=self.dst_speed_var, foreground=DEST_ACCENT, style="Card.TLabel", font=("Segoe UI", 13, "bold")).pack(anchor="w")

        self.dst_meta_var = tk.StringVar(value="Free Space: — | Drive: —")
        ttk.Label(dst_card, textvariable=self.dst_meta_var, style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))

        # Main Progress & ETA Card
        stats = ttk.Frame(outer, style="Card.TFrame", padding=14)
        stats.pack(fill="x", pady=(0, 10))

        self.progress_title_var = tk.StringVar(value="Total Progress: 0 B / 0 B (0.0%)")
        ttk.Label(stats, textvariable=self.progress_title_var, style="Heading.TLabel").pack(anchor="w")

        self.bar = ttk.Progressbar(stats, mode="determinate", maximum=100, style="Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=(8, 10))

        # 4-Column Metrics: ETA, Elapsed, Files, Active File
        grid = ttk.Frame(stats, style="Card.TFrame")
        grid.pack(fill="x")

        self.eta_var = tk.StringVar(value="—")  # PROMINENT ESTIMATION TIME
        self.elapsed_var = tk.StringVar(value="00:00:00")
        self.files_var = tk.StringVar(value="0 / 0")

        cols = [
            ("ESTIMATION TIME (ETA)", self.eta_var),
            ("Elapsed Time", self.elapsed_var),
            ("Files Transferred", self.files_var),
        ]

        for col_idx, (lbl, var) in enumerate(cols):
            cell = ttk.Frame(grid, style="Card.TFrame")
            cell.grid(row=0, column=col_idx, sticky="ew", padx=(0, 8 if col_idx < 2 else 0))
            ttk.Label(cell, text=lbl, style="CardMuted.TLabel").pack(anchor="w")
            val_lbl = ttk.Label(cell, textvariable=var, style="Card.TLabel", font=("Segoe UI", 11, "bold"))
            if "ETA" in lbl:
                val_lbl.configure(foreground=DEST_ACCENT)
            val_lbl.pack(anchor="w", pady=(2, 0))
            grid.columnconfigure(col_idx, weight=1)

        self.active_file_var = tk.StringVar(value="Active: Ready (Waiting for transfer)")
        ttk.Label(stats, textvariable=self.active_file_var, foreground=TEXT_MUTED, style="Card.TLabel", font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

        # Controls Frame
        ctl = ttk.Frame(outer, style="Card.TFrame", padding=12)
        ctl.pack(fill="x", pady=(0, 10))

        self.confirm_var = tk.BooleanVar(value=False)
        self.chk_confirm = ttk.Checkbutton(
            ctl,
            text="I confirmed the previous Robocopy transfer has finished or was stopped (/E /Z /J /XO)",
            variable=self.confirm_var,
            command=self._update_buttons,
        )
        self.chk_confirm.pack(anchor="w", pady=(0, 8))

        btn_row = ttk.Frame(ctl, style="Card.TFrame")
        btn_row.pack(fill="x")

        self.btn_resume = ttk.Button(btn_row, text="Resume Copy", style="Action.TButton", command=self._on_resume)
        self.btn_resume.pack(side="left")

        self.btn_stop = ttk.Button(btn_row, text="Stop Copy", style="Danger.TButton", command=self._on_stop)
        self.btn_stop.pack(side="left", padx=10)

        self.btn_refresh = ttk.Button(btn_row, text="Rescan Storage", command=self._on_refresh)
        self.btn_refresh.pack(side="left", padx=4)

        self.btn_open_src = ttk.Button(btn_row, text="Open Source Share", command=lambda: os.startfile(DEFAULT_SOURCE))
        self.btn_open_src.pack(side="left", padx=4)

        self.btn_open_dest = ttk.Button(btn_row, text="Open D:\\temp", command=lambda: os.startfile(DEFAULT_DEST))
        self.btn_open_dest.pack(side="left", padx=4)

        # Terminal Log
        self.log = tk.Text(
            outer,
            height=8,
            wrap="word",
            state="disabled",
            bg=TERMINAL_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            relief="flat",
            font=("Consolas", 9),
            padx=8,
            pady=8,
        )
        self.log.pack(fill="both", expand=True)

        self._log("Init", "Tkinter Dual-Deck Dark Transfer Monitor initialized.")
        self._update_buttons()

    def _log(self, tag: str, text: str) -> None:
        self.log.configure(state="normal")
        now_str = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{now_str}] [{tag}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _update_buttons(self) -> None:
        status = self.engine.get_system_status()
        is_running = status["is_managed_running"]

        if is_running:
            self.btn_resume.configure(state="disabled", text="Copy Running")
            self.btn_stop.configure(state="normal")
            self.chk_confirm.configure(state="disabled")
            self.status_pill.configure(text=f"Active (PID {status['managed_pid']})", foreground=SOURCE_ACCENT)
        else:
            self.btn_resume.configure(text="Resume Copy")
            self.btn_resume.configure(state="normal" if self.confirm_var.get() else "disabled")
            self.btn_stop.configure(state="disabled")
            self.chk_confirm.configure(state="normal")
            if status["external_processes"]:
                ext = ", ".join(str(p["pid"]) for p in status["external_processes"])
                self.status_pill.configure(text=f"External Robocopy Active ({ext})", foreground=WARNING_COLOR)
            else:
                self.status_pill.configure(text="Ready to resume", foreground=SUCCESS_COLOR)

    def _on_resume(self) -> None:
        if not self.confirm_var.get():
            return
        status = self.engine.get_system_status()
        if status["is_managed_running"]:
            messagebox.showwarning("Already Running", "Robocopy is already running.")
            return
        if status["external_processes"]:
            pids = ", ".join(str(p["pid"]) for p in status["external_processes"])
            if not messagebox.askyesno(
                "External Robocopy Detected",
                f"Another Robocopy process is currently active ({pids}).\n\nAre you sure you want to proceed?",
            ):
                return

        ok, msg = self.engine.start_transfer()
        if not ok:
            messagebox.showerror("Could not start", msg)
        else:
            self._log("Start", msg)
        self._update_buttons()

    def _on_stop(self) -> None:
        if messagebox.askyesno(
            "Stop Copy",
            "Stop the Robocopy transfer process? Any copied files on D:\\temp will remain intact, and resume can continue anytime.",
        ):
            ok, msg = self.engine.stop_transfer()
            if not ok:
                messagebox.showerror("Error", msg)
            else:
                self._log("Stop", msg)
            self._update_buttons()

    def _on_refresh(self) -> None:
        self.engine.start_background_scan()
        self._log("Scan", "Requested background folder scan and drive space check.")

    def _drain_events(self) -> None:
        while True:
            try:
                ev_type, data = self.events.get_nowait()
            except queue.Empty:
                break

            if ev_type == "log":
                self._log(data.get("level", "info").upper(), data.get("text", ""))
            elif ev_type in ("telemetry", "scan_finished", "transfer_started", "transfer_stopped", "transfer_completed"):
                self._update_telemetry_ui()

        self.after(150, self._drain_events)

    def _update_telemetry_ui(self) -> None:
        status = self.engine.get_system_status()

        # SMB Latency
        if status["smb_latency_ms"] is not None:
            self.latency_lbl.configure(text=f"SMB Latency: {status['smb_latency_ms']} ms")
        else:
            self.latency_lbl.configure(text="SMB: Connected" if status["source_reachable"] else "SMB: Offline")

        # Source / Dest Meta
        if status["source_disk"]:
            self.src_meta_var.set(f"Capacity: {format_bytes(status['source_disk']['total'])} | Used: {format_bytes(status['source_disk']['used'])}")
        if status["dest_disk"]:
            self.dst_meta_var.set(f"Free Space: {format_bytes(status['dest_disk']['free'])} | Drive: {format_bytes(status['dest_disk']['total'])}")

        # Dual Speeds
        if status["is_managed_running"]:
            self.src_speed_var.set(status["source_upload_formatted"])
            self.dst_speed_var.set(status["dest_download_formatted"])
        else:
            self.src_speed_var.set("0 B/s")
            self.dst_speed_var.set("0 B/s")

        # Progress
        pct = status["progress_percent"]
        self.bar["value"] = pct
        self.progress_title_var.set(
            f"Total Progress: {format_bytes(status['dest_copied_bytes'])} / {format_bytes(status['source_total_bytes'])} ({pct:.1f}%)"
        )

        # ETA & Elapsed
        self.elapsed_var.set(status["elapsed_formatted"])
        self.files_var.set(f"{status['dest_copied_files']:,} / {status['source_total_files']:,}")

        if status["is_managed_running"]:
            if status["eta_seconds"] > 0:
                self.eta_var.set(format_duration(status["eta_seconds"]))
            else:
                self.eta_var.set("Estimating…" if pct < 100 else "Complete")
        else:
            self.eta_var.set("Complete" if pct >= 100 else "—")

        # Active File
        if status["is_managed_running"]:
            self.active_file_var.set(f"Active Folder: {status['current_folder']} | File: {status['current_file']}")
        else:
            self.active_file_var.set("Active: Ready (Waiting for transfer)")

        self._update_buttons()

    def _tick(self) -> None:
        self._update_telemetry_ui()
        self.after(500, self._tick)

    def _on_close(self) -> None:
        status = self.engine.get_system_status()
        if status["is_managed_running"]:
            answer = messagebox.askyesnocancel(
                "Copy is running",
                "Yes: Stop the copy safely and close.\nNo: Leave it running in background (monitor will re-attach when reopened).\nCancel: Keep this window open.",
            )
            if answer is None:
                return
            if answer:
                self.engine.stop_transfer()
        self.destroy()


def run_tkinter_app(source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
    app = TkinterTransferMonitor(source_path=source_path, dest_path=dest_path)
    app.mainloop()


if __name__ == "__main__":
    run_tkinter_app()
