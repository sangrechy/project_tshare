"""Tkinter Dark Fallback Interface for Transaction Deep Verifier.

Provides full parity verification, smart block hashing, and SHA-256 bit-by-bit
checks with live progress, ETA, and audit certificate export.
"""
from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from backend.verify_engine import (
    VerificationEngine,
    DEFAULT_SOURCE,
    DEFAULT_DEST,
    format_bytes,
    format_duration,
)

BG_COLOR = "#24272c"
CARD_BG = "#2a2d33"
TEXT_COLOR = "#f1f5f9"
TEXT_MUTED = "#9ba1a6"
ACCENT_LIGHT = "#a78bfa"
DEST_LIGHT = "#38bdf8"
SUCCESS_COLOR = "#10b981"
DANGER_COLOR = "#ef4444"
TERMINAL_BG = "#191b1e"


class TkinterVerifier(tk.Tk):
    def __init__(self, source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
        super().__init__()
        self.title("Transaction Deep Verifier • Dark Soft UI")
        self.geometry("920x720")
        self.minsize(800, 600)
        self.configure(bg=BG_COLOR)

        self.events: queue.Queue = queue.Queue()
        self.engine = VerificationEngine(on_event=self._engine_callback)
        self.engine.source_path = source_path
        self.engine.dest_path = dest_path

        self._init_styles()
        self._build_ui()

        self.after(100, self._drain_events)
        self.after(400, self._tick)

    def _engine_callback(self, event_type: str, data: any) -> None:
        self.events.put((event_type, data))

    def _init_styles(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 9))
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
        style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_COLOR)
        style.configure("CardMuted.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 8))
        style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 14, "bold"))

        style.configure("TRadiobutton", background=CARD_BG, foreground=TEXT_COLOR, font=("Segoe UI", 9))

        style.configure(
            "Primary.TButton",
            background=CARD_BG,
            foreground=ACCENT_LIGHT,
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map("Primary.TButton", background=[("active", "#7c3aed")], foreground=[("active", "#ffffff")])

        style.configure(
            "Danger.TButton",
            background=CARD_BG,
            foreground="#f87171",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )
        style.map("Danger.TButton", background=[("active", DANGER_COLOR)], foreground=[("active", "#ffffff")])

        style.configure("Horizontal.TProgressbar", troughcolor=TERMINAL_BG, background="#7c3aed", bordercolor=CARD_BG)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=16)
        outer.pack(fill="both", expand=True)

        # Header
        hdr = ttk.Frame(outer)
        hdr.pack(fill="x", pady=(0, 10))
        ttk.Label(hdr, text="TRANSACTION DEEP VERIFIER", style="Title.TLabel").pack(side="left")
        self.status_pill = ttk.Label(hdr, text="Auditor Ready", foreground=SUCCESS_COLOR, font=("Segoe UI", 9, "bold"))
        self.status_pill.pack(side="right")

        # Inventory Parity Banner
        banner = ttk.Frame(outer, style="Card.TFrame", padding=12)
        banner.pack(fill="x", pady=(0, 10))

        row1 = ttk.Frame(banner, style="Card.TFrame")
        row1.pack(fill="x")
        ttk.Label(row1, text="SOURCE: ", foreground=ACCENT_LIGHT, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(row1, text=f"{self.engine.source_path}", style="Card.TLabel").pack(side="left")

        row2 = ttk.Frame(banner, style="Card.TFrame")
        row2.pack(fill="x", pady=(4, 0))
        ttk.Label(row2, text="DEST:   ", foreground=DEST_LIGHT, style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(row2, text=f"{self.engine.dest_path}", style="Card.TLabel").pack(side="left")

        # Mode Selection
        mode_box = ttk.Frame(outer, style="Card.TFrame", padding=12)
        mode_box.pack(fill="x", pady=(0, 10))

        ttk.Label(mode_box, text="Audit Rigor Mode:", style="Card.TLabel", font=("Segoe UI", 9, "bold")).pack(anchor="w")

        self.mode_var = tk.StringVar(value="metadata")
        r_row = ttk.Frame(mode_box, style="Card.TFrame")
        r_row.pack(fill="x", pady=(6, 8))

        ttk.Radiobutton(r_row, text="1. Fast Parity Audit (Byte sizes & Timestamps)", variable=self.mode_var, value="metadata").pack(side="left", padx=(0, 14))
        ttk.Radiobutton(r_row, text="2. Smart Block Checksum (Header/Mid/Foot SHA-256)", variable=self.mode_var, value="smart").pack(side="left", padx=(0, 14))
        ttk.Radiobutton(r_row, text="3. Full Bit-by-Bit SHA-256", variable=self.mode_var, value="full_sha256").pack(side="left")

        btn_row = ttk.Frame(mode_box, style="Card.TFrame")
        btn_row.pack(fill="x")

        self.btn_start = ttk.Button(btn_row, text="Start Deep Verification", style="Primary.TButton", command=self._on_start)
        self.btn_start.pack(side="left")

        self.btn_stop = ttk.Button(btn_row, text="Stop Audit", style="Danger.TButton", command=self._on_stop, state="disabled")
        self.btn_stop.pack(side="left", padx=10)

        self.btn_cert = ttk.Button(btn_row, text="Export Audit Certificate", command=self._on_export)
        self.btn_cert.pack(side="left", padx=4)

        self.btn_open = ttk.Button(btn_row, text="Open D:\\temp", command=lambda: os.startfile(DEFAULT_DEST))
        self.btn_open.pack(side="left", padx=4)

        # Telemetry Card
        stats = ttk.Frame(outer, style="Card.TFrame", padding=12)
        stats.pack(fill="x", pady=(0, 10))

        self.progress_lbl_var = tk.StringVar(value="Audit Progress: 0 B / 207.78 GB (0.0%)")
        ttk.Label(stats, textvariable=self.progress_lbl_var, style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.bar = ttk.Progressbar(stats, mode="determinate", maximum=100, style="Horizontal.TProgressbar")
        self.bar.pack(fill="x", pady=(6, 10))

        # Metrics grid: ETA, Speed, Matched, Mismatched
        grid = ttk.Frame(stats, style="Card.TFrame")
        grid.pack(fill="x")

        self.eta_var = tk.StringVar(value="—")
        self.speed_var = tk.StringVar(value="0 B/s")
        self.matched_var = tk.StringVar(value="0")
        self.mismatch_var = tk.StringVar(value="0")

        cols = [
            ("ESTIMATION TIME (ETA)", self.eta_var),
            ("Hashing Speed", self.speed_var),
            ("Matched OK", self.matched_var),
            ("Discrepancies", self.mismatch_var),
        ]

        for col_idx, (lbl, var) in enumerate(cols):
            cell = ttk.Frame(grid, style="Card.TFrame")
            cell.grid(row=0, column=col_idx, sticky="ew", padx=(0, 8 if col_idx < 3 else 0))
            ttk.Label(cell, text=lbl, style="CardMuted.TLabel").pack(anchor="w")
            val_lbl = ttk.Label(cell, textvariable=var, style="Card.TLabel", font=("Segoe UI", 11, "bold"))
            if "ETA" in lbl:
                val_lbl.configure(foreground=DEST_LIGHT)
            elif "Matched" in lbl:
                val_lbl.configure(foreground=SUCCESS_COLOR)
            elif "Discrepancies" in lbl:
                val_lbl.configure(foreground=DANGER_COLOR)
            val_lbl.pack(anchor="w", pady=(2, 0))
            grid.columnconfigure(col_idx, weight=1)

        self.active_file_var = tk.StringVar(value="Active: Ready")
        ttk.Label(stats, textvariable=self.active_file_var, foreground=TEXT_MUTED, style="Card.TLabel", font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 0))

        # Terminal Log
        self.log = tk.Text(
            outer,
            height=11,
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

        self._log("INIT", "Transaction Deep Verifier initialized.")

    def _log(self, tag: str, text: str) -> None:
        self.log.configure(state="normal")
        now_str = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{now_str}] [{tag}] {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _on_start(self) -> None:
        mode = self.mode_var.get()
        ok, msg = self.engine.start_verification(mode=mode, workers=4)
        if not ok:
            messagebox.showerror("Error", msg)
        else:
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.status_pill.configure(text=f"Auditing ({mode.upper()})…", foreground=ACCENT_LIGHT)

    def _on_stop(self) -> None:
        self.engine.stop_verification()
        self.btn_stop.configure(state="disabled")

    def _on_export(self) -> None:
        path = self.engine.export_html_report()
        if os.path.exists(path):
            os.startfile(path)
            messagebox.showinfo("Certificate Exported", f"Audit Certificate opened:\n{path}")

    def _drain_events(self) -> None:
        while True:
            try:
                ev_type, data = self.events.get_nowait()
            except queue.Empty:
                break
            if ev_type == "log":
                self._log(data.get("level", "info").upper(), data.get("text", ""))
            elif ev_type in ("telemetry", "verification_finished"):
                self._update_telemetry_ui()

        self.after(120, self._drain_events)

    def _update_telemetry_ui(self) -> None:
        st = self.engine.get_status()

        pct = st["progress_percent"]
        self.bar["value"] = pct
        self.progress_lbl_var.set(
            f"Audit Progress: {st['bytes_processed_formatted']} / {st['total_source_bytes_formatted'] or '207.78 GB'} ({pct:.1f}%)"
        )

        self.speed_var.set(st["hashing_speed_formatted"])
        self.matched_var.set(f"{st['matched_count']:,} / {st['total_source_files']:,}")
        self.mismatch_var.set(f"{st['mismatch_count']:,}")

        if st["is_running"]:
            if st["eta_seconds"] > 0:
                self.eta_var.set(format_duration(st["eta_seconds"]))
            else:
                self.eta_var.set("Estimating…" if pct < 100 else "Complete")
            self.active_file_var.set(f"Auditing: {st['current_file']}")
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
        else:
            self.eta_var.set("Audit Done" if pct >= 100 else "—")
            self.active_file_var.set("Active: Ready")
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            if st["files_processed"] > 0:
                if st["mismatch_count"] == 0 and st["missing_count"] == 0:
                    self.status_pill.configure(text="Parity 100% Verified", foreground=SUCCESS_COLOR)
                else:
                    self.status_pill.configure(text="Discrepancy Found", foreground=DANGER_COLOR)

    def _tick(self) -> None:
        self._update_telemetry_ui()
        self.after(400, self._tick)


def run_tkinter_verifier(source_path: str = DEFAULT_SOURCE, dest_path: str = DEFAULT_DEST) -> None:
    app = TkinterVerifier(source_path=source_path, dest_path=dest_path)
    app.mainloop()


if __name__ == "__main__":
    run_tkinter_verifier()
