#!/usr/bin/env python3
"""
HamCall — Amateur Radio Callsign Lookup
========================================
A simple desktop GUI for looking up FCC amateur radio callsigns
from the local fcc.db database.

Phase 1: Callsign lookup
Phase 2: DX logging, notes, photos (coming soon!)

Usage:
    python3 hamcall.py

Requires:
    - fcc.db with amateur table loaded (run import_amateur.py first)
"""

import tkinter as tk
from tkinter import font as tkfont
import sqlite3
import os
import sys

# ── Database ───────────────────────────────────────────────────
DB_PATH = os.path.expanduser("~/fcc-scanner/fcc.db")

# ── Colors — Dark radio terminal aesthetic ─────────────────────
BG_DARK    = "#0a0e0a"   # near black with green tint
BG_PANEL   = "#0f1a0f"   # slightly lighter panel
BG_INPUT   = "#141f14"   # input field background
FG_GREEN   = "#00ff41"   # bright matrix green
FG_DIM     = "#4a9e4a"   # dimmed green - was #2a6e2a
FG_AMBER   = "#ffd700"   # amber accent for labels - was #ffb000
FG_WHITE   = "#e8f5e8"   # soft white-green for values - was #c8e6c8
FG_RED     = "#ff6666"   # error / expired - was #ff4444
FG_ACTIVE  = "#00ff41"   # active status
BORDER     = "#2a6d2a"   # subtle border - was #1a4d1a
HIGHLIGHT  = "#004400"   # highlight color - was #003300

# ── License class decoder ──────────────────────────────────────
CLASS_MAP = {
    "A": "Advanced",
    "B": "Technician Plus",
    "C": "Amateur Extra",
    "D": "Technician",
    "E": "Amateur Extra",
    "G": "General",
    "N": "Novice",
    "T": "Technician",
    "P": "Technician Plus",
    "":  "General",
}

STATUS_MAP = {
    "HA": ("Active", FG_ACTIVE),
    "HV": ("Active — Vanity", FG_ACTIVE),
    "HX": ("Expired", FG_RED),
    "HB": ("Cancelled", FG_RED),
    "A":  ("Active", FG_ACTIVE),
    "L":  ("Active", FG_ACTIVE),
}


def lookup_callsign(callsign):
    """Query fcc.db for a ham callsign."""
    if not os.path.exists(DB_PATH):
        return None, "Database not found! Run import_fcc.py first."

    try:
        con = sqlite3.connect(DB_PATH)
        con.row_factory = sqlite3.Row
        row = con.execute("""
            SELECT call_sign, full_name, first_name, last_name,
                   city, state, zip_code, operator_class,
                   class_code, group_code, grant_date,
                   expired_date, frn, status
            FROM amateur
            WHERE call_sign = ?
        """, (callsign.upper().strip(),)).fetchone()
        con.close()
        return row, None
    except Exception as e:
        return None, str(e)


class HamCallApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HamCall")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(False, False)

        # Center on screen
        w, h = 480, 520
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Fonts
        self.font_title  = tkfont.Font(family="Courier", size=16, weight="bold")
        self.font_sub    = tkfont.Font(family="Courier", size=8)
        self.font_input  = tkfont.Font(family="Courier", size=14, weight="bold")
        self.font_label  = tkfont.Font(family="Courier", size=10, weight="bold")
        self.font_value  = tkfont.Font(family="Courier", size=10)
        self.font_large  = tkfont.Font(family="Courier", size=18, weight="bold")
        self.font_status = tkfont.Font(family="Courier", size=11, weight="bold")
        self.font_btn    = tkfont.Font(family="Courier", size=11, weight="bold")

        self._build_ui()

    def _build_ui(self):
        # ── Header ─────────────────────────────────────────────
        hdr = tk.Frame(self.root, bg=BG_DARK, pady=10)
        hdr.pack(fill="x", padx=20)

        tk.Label(hdr, text="📻  HamCall",
                 font=self.font_title, bg=BG_DARK,
                 fg=FG_GREEN).pack(side="left")

        tk.Label(hdr, text="v1.0  |  KJ7TNY & The Wizard 🧙",
                 font=self.font_sub, bg=BG_DARK,
                 fg=FG_DIM).pack(side="right", pady=6)

        # Separator
        tk.Frame(self.root, bg=FG_DIM, height=1).pack(fill="x", padx=20)

        # ── Search bar ─────────────────────────────────────────
        search_frame = tk.Frame(self.root, bg=BG_DARK, pady=15)
        search_frame.pack(fill="x", padx=20)

        tk.Label(search_frame, text="CALLSIGN",
                 font=self.font_label, bg=BG_DARK,
                 fg=FG_AMBER).pack(anchor="w")

        input_row = tk.Frame(search_frame, bg=BG_DARK)
        input_row.pack(fill="x", pady=5)

        # Callsign entry
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(
            input_row,
            textvariable=self.entry_var,
            font=self.font_large,
            bg=BG_INPUT,
            fg=FG_GREEN,
            insertbackground=FG_GREEN,
            relief="flat",
            bd=0,
            width=12,
            justify="center"
        )
        self.entry.pack(side="left", ipady=8, padx=(0, 10))
        self.entry.bind("<Return>", lambda e: self._do_lookup())
        self.entry.bind("<KeyRelease>", self._auto_upper)
        self.entry.focus_set()

        # Lookup button
        self.btn = tk.Button(
            input_row,
            text="LOOK UP",
            font=self.font_btn,
            bg=FG_DIM,
            fg=FG_GREEN,
            activebackground=FG_GREEN,
            activeforeground=BG_DARK,
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            command=self._do_lookup
        )
        self.btn.pack(side="left")
        self.btn.bind("<Enter>", lambda e: self.btn.config(bg="#005500"))
        self.btn.bind("<Leave>", lambda e: self.btn.config(bg=FG_DIM))

        # Clear button
        clr = tk.Button(
            input_row,
            text="CLR",
            font=self.font_sub,
            bg=BG_PANEL,
            fg=FG_DIM,
            activebackground=HIGHLIGHT,
            activeforeground=FG_GREEN,
            relief="flat",
            bd=0,
            padx=8,
            pady=8,
            cursor="hand2",
            command=self._clear
        )
        clr.pack(side="left", padx=(6, 0))

        # Hint
        self.hint = tk.Label(search_frame, text="Press ENTER or click LOOK UP",
                             font=self.font_sub, bg=BG_DARK, fg=FG_DIM)
        self.hint.pack(anchor="w")

        # Separator
        tk.Frame(self.root, bg=FG_DIM, height=1).pack(fill="x", padx=20)

        # ── Results panel ──────────────────────────────────────
        results_outer = tk.Frame(self.root, bg=BG_PANEL,
                                 highlightbackground=BORDER,
                                 highlightthickness=1)
        results_outer.pack(fill="both", expand=True, padx=20, pady=15)

        # Callsign display (big)
        self.lbl_callsign = tk.Label(
            results_outer,
            text="- - - - -",
            font=tkfont.Font(family="Courier", size=28, weight="bold"),
            bg=BG_PANEL, fg=FG_DIM,
            pady=10
        )
        self.lbl_callsign.pack()

        tk.Frame(results_outer, bg=BORDER, height=1).pack(fill="x", padx=10)

        # Fields grid
        fields_frame = tk.Frame(results_outer, bg=BG_PANEL, pady=8)
        fields_frame.pack(fill="both", expand=True, padx=15)

        self.fields = {}
        field_defs = [
            ("NAME",     "name"),
            ("LOCATION", "location"),
            ("CLASS",    "cls"),
            ("EXPIRES",  "expires"),
            ("FRN",      "frn"),
            ("STATUS",   "status"),
        ]

        for label, key in field_defs:
            row = tk.Frame(fields_frame, bg=BG_PANEL, pady=3)
            row.pack(fill="x")

            tk.Label(row, text=f"{label:<10}",
                     font=self.font_label,
                     bg=BG_PANEL, fg=FG_AMBER,
                     width=10, anchor="w").pack(side="left")

            tk.Label(row, text=":",
                     font=self.font_label,
                     bg=BG_PANEL, fg=FG_DIM).pack(side="left", padx=(0, 8))

            lbl = tk.Label(row, text="—",
                           font=self.font_value,
                           bg=BG_PANEL, fg=FG_DIM,
                           anchor="w")
            lbl.pack(side="left", fill="x", expand=True)
            self.fields[key] = lbl

        # ── Footer ─────────────────────────────────────────────
        tk.Frame(self.root, bg=FG_DIM, height=1).pack(fill="x", padx=20)
        footer = tk.Frame(self.root, bg=BG_DARK, pady=6)
        footer.pack(fill="x", padx=20)

        self.status_bar = tk.Label(
            footer,
            text="Ready  —  3,346,184 hams loaded  —  fully offline",
            font=self.font_sub,
            bg=BG_DARK, fg=FG_DIM
        )
        self.status_bar.pack(side="left")

        tk.Label(footer, text="fcc.db",
                 font=self.font_sub,
                 bg=BG_DARK, fg=FG_DIM).pack(side="right")

    def _auto_upper(self, event=None):
        """Auto-uppercase the callsign entry."""
        val = self.entry_var.get().upper()
        self.entry_var.set(val)
        self.entry.icursor(tk.END)

    def _clear(self):
        self.entry_var.set("")
        self.lbl_callsign.config(text="- - - - -", fg=FG_DIM)
        for key, lbl in self.fields.items():
            lbl.config(text="—", fg=FG_DIM)
        self.status_bar.config(text="Ready  —  3,346,184 hams loaded  —  fully offline")
        self.entry.focus_set()

    def _do_lookup(self):
        callsign = self.entry_var.get().strip().upper()
        if not callsign:
            self.status_bar.config(text="⚠  Enter a callsign first!", fg=FG_AMBER)
            return

        self.status_bar.config(text=f"Looking up {callsign}...", fg=FG_DIM)
        self.root.update()

        row, error = lookup_callsign(callsign)

        if error:
            self.lbl_callsign.config(text="ERROR", fg=FG_RED)
            self.status_bar.config(text=f"⚠  {error}", fg=FG_RED)
            return

        if not row:
            self.lbl_callsign.config(text=callsign, fg=FG_RED)
            for key, lbl in self.fields.items():
                lbl.config(text="—", fg=FG_DIM)
            self.status_bar.config(
                text=f"⚠  {callsign} not found — license may be expired or invalid",
                fg=FG_AMBER
            )
            return

        # ── Populate fields ────────────────────────────────────
        self.lbl_callsign.config(text=row["call_sign"], fg=FG_GREEN)

        # Name
        name = row["full_name"] or f"{row['first_name']} {row['last_name']}".strip()
        self.fields["name"].config(text=name or "—", fg=FG_WHITE)

        # Location
        city     = row["city"] or ""
        state    = row["state"] or ""
        zipcode  = row["zip_code"] or ""
        location = f"{city}, {state}  {zipcode}".strip(", ")
        self.fields["location"].config(text=location or "—", fg=FG_WHITE)

        # License class
        class_code = row["class_code"] or ""
        class_str  = CLASS_MAP.get(class_code, class_code or "General")
        group      = row["group_code"] or ""
        self.fields["cls"].config(text=class_str, fg=FG_WHITE)

        # Expiration — calculate from grant date (FCC = 10 years)
        grant   = row["grant_date"] or ""
        expires = row["expired_date"] or ""
        if not expires and grant:
            try:
                parts   = grant.split("/")
                expires = f"{parts[0]}/{parts[1]}/{int(parts[2])+10}"
            except Exception:
                expires = "—"
        self.fields["expires"].config(text=expires or "—", fg=FG_WHITE)

        # FRN
        self.fields["frn"].config(
            text=row["frn"] or "—", fg=FG_WHITE)

        # Status
        status_code = row["status"] or ""
        status_text, status_color = STATUS_MAP.get(
            status_code, (status_code or "Unknown", FG_DIM))
        self.fields["status"].config(text=status_text, fg=status_color)

        self.status_bar.config(
            text=f"✓  Found: {row['call_sign']}  —  {name}",
            fg=FG_GREEN
        )


def main():
    if not os.path.exists(DB_PATH):
        print(f"⚠  Database not found at {DB_PATH}")
        print("   Run import_fcc.py and import_amateur.py first!")
        sys.exit(1)

    root = tk.Tk()
    app = HamCallApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
