#!/usr/bin/env python3
"""
Radiowave Connection v1.0
==========================
The Swiss Army Knife launcher for the FCC ULS Scanner Suite.
Built on the same fcc.db jailhouse that powers search_fcc.py and hamcall.py.

Usage:
    python3 radiowave.py

Requires:
    - fcc.db with all tables loaded
    - search_fcc.py and hamcall.py in the same folder
    - python3-tk installed (sudo apt install python3-tk)
"""

import tkinter as tk
from tkinter import font as tkfont
import sqlite3
import subprocess
import os
import sys

# ── Paths ──────────────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/fcc-scanner")
DB_PATH  = os.path.join(BASE_DIR, "fcc.db")

# ── Colors — same dark radio terminal aesthetic as HamCall ─────
BG_DARK    = "#0a0e0a"
BG_PANEL   = "#0f1a0f"
BG_SIDEBAR = "#080c08"
BG_INPUT   = "#141f14"
FG_GREEN   = "#00ff41"
FG_DIM     = "#4a9e4a"
FG_AMBER   = "#ffd700"
FG_WHITE   = "#e8f5e8"
FG_RED     = "#ff6666"
FG_BLUE    = "#4fc3f7"
BORDER     = "#2a6d2a"
HIGHLIGHT  = "#004400"
BTN_ACTIVE = "#003300"

# ── DB Stats ───────────────────────────────────────────────────
def get_db_stats():
    """Pull live counts from fcc.db for the dashboard."""
    stats = {
        "licenses":     "—",
        "transmitters": "—",
        "amateur":      "—",
        "gmrs":         "—",
        "cities":       "—",
        "status":       "✗  Not found",
        "status_color": FG_RED,
    }
    if not os.path.exists(DB_PATH):
        return stats
    try:
        con = sqlite3.connect(DB_PATH)
        def count(table, where=""):
            try:
                q = f"SELECT COUNT(*) FROM {table}"
                if where:
                    q += f" WHERE {where}"
                return f"{con.execute(q).fetchone()[0]:,}"
            except Exception:
                return "—"

        stats["licenses"]     = count("hd")
        stats["transmitters"] = count("lo")
        stats["amateur"]      = count("amateur")
        stats["gmrs"]         = count("gmrs")
        stats["cities"]       = count("cities")
        stats["status"]       = "✓  Connected"
        stats["status_color"] = FG_GREEN
        con.close()
    except Exception:
        stats["status"]       = "✗  Error reading DB"
        stats["status_color"] = FG_RED
    return stats


class RadiowaveApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Radiowave Connection")
        self.root.configure(bg=BG_DARK)
        self.root.resizable(True, True)

        # Window size and center
        w, h = 820, 560
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(700, 480)

        # Fonts
        self.font_title   = tkfont.Font(family="Courier", size=15, weight="bold")
        self.font_sub     = tkfont.Font(family="Courier", size=8)
        self.font_label   = tkfont.Font(family="Courier", size=10, weight="bold")
        self.font_value   = tkfont.Font(family="Courier", size=10)
        self.font_btn     = tkfont.Font(family="Courier", size=11, weight="bold")
        self.font_btnsub  = tkfont.Font(family="Courier", size=8)
        self.font_stat    = tkfont.Font(family="Courier", size=18, weight="bold")
        self.font_statlbl = tkfont.Font(family="Courier", size=8)
        self.font_status  = tkfont.Font(family="Courier", size=9)

        # Active tool tracking
        self.active_btn = None

        self._build_ui()
        self._load_stats()

    def _build_ui(self):
        # ── Top title bar ───────────────────────────────────────
        title_bar = tk.Frame(self.root, bg=BG_SIDEBAR, pady=8)
        title_bar.pack(fill="x")

        tk.Label(title_bar,
                 text="📻  Radiowave Connection  v1.0",
                 font=self.font_title,
                 bg=BG_SIDEBAR, fg=FG_GREEN).pack(side="left", padx=16)

        tk.Label(title_bar,
                 text="KJ7TNY & The Wizard 🧙  |  The Jailhouse Edition",
                 font=self.font_sub,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(side="right", padx=16)

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ── Main body (sidebar + content) ───────────────────────
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # ── LEFT SIDEBAR ────────────────────────────────────────
        sidebar = tk.Frame(body, bg=BG_SIDEBAR, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(sidebar,
                 text="— TOOLS —",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(pady=(16, 8))

        # Tool buttons
        self.btn_search = self._make_sidebar_btn(
            sidebar,
            "🔍  Search Transmitters",
            "Part 90 — search_fcc.py",
            self._launch_search
        )

        self.btn_hamcall = self._make_sidebar_btn(
            sidebar,
            "📡  HamCall Lookup",
            "Ham & GMRS — hamcall.py",
            self._launch_hamcall
        )

        # Divider
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=12)

        tk.Label(sidebar,
                 text="— COMING SOON —",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(pady=(0, 8))

        # Dimmed future buttons
        self._make_sidebar_btn_dim(sidebar, "🔄  Update Databases",  "Download + import")
        self._make_sidebar_btn_dim(sidebar, "🔧  Toolbox",           "Ham radio utilities")
        self._make_sidebar_btn_dim(sidebar, "📋  Reports",           "Saved search results")

        # Sidebar bottom — db status
        tk.Frame(sidebar, bg=BG_SIDEBAR).pack(fill="y", expand=True)
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=4)

        self.lbl_db_status = tk.Label(
            sidebar,
            text="fcc.db — checking...",
            font=self.font_statlbl,
            bg=BG_SIDEBAR, fg=FG_DIM,
            wraplength=170, justify="center"
        )
        self.lbl_db_status.pack(pady=(4, 12))

        # Sidebar right border
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── RIGHT CONTENT PANEL ─────────────────────────────────
        self.content = tk.Frame(body, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)

        # Show dashboard by default
        self._show_dashboard()

        # ── STATUS BAR ──────────────────────────────────────────
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        status_bar = tk.Frame(self.root, bg=BG_SIDEBAR, pady=4)
        status_bar.pack(fill="x")

        self.status_msg = tk.Label(
            status_bar,
            text="Ready  —  Select a tool from the sidebar",
            font=self.font_status,
            bg=BG_SIDEBAR, fg=FG_DIM
        )
        self.status_msg.pack(side="left", padx=12)

        tk.Label(status_bar,
                 text="Linux Mint  ·  Python 3.12  ·  SQLite",
                 font=self.font_status,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(side="right", padx=12)

    def _make_sidebar_btn(self, parent, title, subtitle, command):
        """Create an active sidebar button."""
        frame = tk.Frame(parent, bg=BG_SIDEBAR, cursor="hand2")
        frame.pack(fill="x", padx=12, pady=3)

        inner = tk.Frame(frame, bg=BTN_ACTIVE,
                         highlightbackground=BORDER,
                         highlightthickness=1)
        inner.pack(fill="x")

        tk.Label(inner, text=title,
                 font=self.font_label,
                 bg=BTN_ACTIVE, fg=FG_GREEN,
                 anchor="w", padx=10, pady=4).pack(fill="x")

        tk.Label(inner, text=subtitle,
                 font=self.font_btnsub,
                 bg=BTN_ACTIVE, fg=FG_DIM,
                 anchor="w", padx=10, pady=2).pack(fill="x")

        # Bind click to all children
        for widget in [frame, inner] + inner.winfo_children():
            widget.bind("<Button-1>", lambda e, cmd=command, f=inner: self._btn_click(cmd, f))
            widget.bind("<Enter>",    lambda e, f=inner: f.config(bg=HIGHLIGHT))
            widget.bind("<Leave>",    lambda e, f=inner: f.config(bg=BTN_ACTIVE))

        return inner

    def _make_sidebar_btn_dim(self, parent, title, subtitle):
        """Create a dimmed/disabled future button."""
        frame = tk.Frame(parent, bg=BG_SIDEBAR)
        frame.pack(fill="x", padx=12, pady=3)

        inner = tk.Frame(frame, bg=BG_SIDEBAR,
                         highlightbackground="#1a3d1a",
                         highlightthickness=1)
        inner.pack(fill="x")

        tk.Label(inner, text=title,
                 font=self.font_label,
                 bg=BG_SIDEBAR, fg="#2a5a2a",
                 anchor="w", padx=10, pady=4).pack(fill="x")

        tk.Label(inner, text=subtitle,
                 font=self.font_btnsub,
                 bg=BG_SIDEBAR, fg="#1a3a1a",
                 anchor="w", padx=10, pady=2).pack(fill="x")

    def _btn_click(self, command, frame):
        """Handle sidebar button click."""
        command()

    def _clear_content(self):
        """Clear the content panel."""
        for widget in self.content.winfo_children():
            widget.destroy()

    # ── DASHBOARD ───────────────────────────────────────────────
    def _show_dashboard(self):
        self._clear_content()

        # Welcome header
        hdr = tk.Frame(self.content, bg=BG_DARK, pady=20)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr,
                 text="Welcome to Radiowave Connection",
                 font=self.font_btn,
                 bg=BG_DARK, fg=FG_GREEN).pack(anchor="w")

        tk.Label(hdr,
                 text="Your offline Swiss Army Knife for FCC radio data  —  30 million records, zero internet needed",
                 font=self.font_sub,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(4, 0))

        # Separator
        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24)

        # Stats grid
        stats_frame = tk.Frame(self.content, bg=BG_DARK, pady=20)
        stats_frame.pack(fill="x", padx=24)

        tk.Label(stats_frame,
                 text="— DATABASE STATS —",
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(0, 12))

        cards = tk.Frame(stats_frame, bg=BG_DARK)
        cards.pack(fill="x")

        self.stat_labels = {}

        stat_defs = [
            ("licenses",     "Active Licenses",  "Part 90"),
            ("transmitters", "Transmitter Sites", "with GPS"),
            ("amateur",      "Ham Callsigns",     "amateur"),
            ("gmrs",         "GMRS Licenses",     "family radio"),
        ]

        for i, (key, label, sublabel) in enumerate(stat_defs):
            card = tk.Frame(cards, bg=BG_PANEL,
                            highlightbackground=BORDER,
                            highlightthickness=1,
                            padx=12, pady=10)
            card.grid(row=0, column=i, padx=(0, 8), sticky="nsew")
            cards.columnconfigure(i, weight=1)

            tk.Label(card, text=label,
                     font=self.font_statlbl,
                     bg=BG_PANEL, fg=FG_DIM).pack()

            lbl = tk.Label(card, text="...",
                           font=self.font_stat,
                           bg=BG_PANEL, fg=FG_GREEN)
            lbl.pack()
            self.stat_labels[key] = lbl

            tk.Label(card, text=sublabel,
                     font=self.font_statlbl,
                     bg=BG_PANEL, fg=FG_DIM).pack()

        # Separator
        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(8, 0))

        # Tool cards
        tools_frame = tk.Frame(self.content, bg=BG_DARK, pady=16)
        tools_frame.pack(fill="x", padx=24)

        tk.Label(tools_frame,
                 text="— QUICK LAUNCH —",
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(0, 12))

        launch_row = tk.Frame(tools_frame, bg=BG_DARK)
        launch_row.pack(fill="x")

        # Search launch card
        self._make_launch_card(
            launch_row,
            "🔍  Search Transmitters",
            "Find any transmitter by county, radius,\ncity, frequency, call sign, or FRN",
            "Launch Terminal",
            self._launch_search,
            FG_GREEN
        )

        # HamCall launch card
        self._make_launch_card(
            launch_row,
            "📡  HamCall Lookup",
            "Look up any ham or GMRS callsign\ninstantly from 3.9M+ offline records",
            "Open HamCall",
            self._launch_hamcall,
            FG_AMBER
        )

        # Footer note
        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(8,0))
        tk.Label(self.content,
                 text='"I Will Find You"  📻  — Minty & The Wizard 🧙',
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(pady=8)

    def _make_launch_card(self, parent, title, desc, btn_text, command, btn_color):
        """Create a quick launch card in the dashboard."""
        card = tk.Frame(parent, bg=BG_PANEL,
                        highlightbackground=BORDER,
                        highlightthickness=1,
                        padx=16, pady=14)
        card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(card, text=title,
                 font=self.font_label,
                 bg=BG_PANEL, fg=btn_color).pack(anchor="w")

        tk.Label(card, text=desc,
                 font=self.font_statlbl,
                 bg=BG_PANEL, fg=FG_DIM,
                 justify="left").pack(anchor="w", pady=(6, 12))

        btn = tk.Button(card,
                        text=btn_text,
                        font=self.font_label,
                        bg=BTN_ACTIVE, fg=btn_color,
                        activebackground=HIGHLIGHT,
                        activeforeground=btn_color,
                        relief="flat", bd=0,
                        padx=12, pady=6,
                        cursor="hand2",
                        command=command)
        btn.pack(anchor="w")
        btn.bind("<Enter>", lambda e: btn.config(bg=HIGHLIGHT))
        btn.bind("<Leave>", lambda e: btn.config(bg=BTN_ACTIVE))

    # ── TOOL LAUNCHERS ──────────────────────────────────────────
    def _launch_search(self):
        """Launch search_fcc.py in a new terminal window."""
        script = os.path.join(BASE_DIR, "search_fcc.py")
        if not os.path.exists(script):
            self._set_status(f"⚠  search_fcc.py not found at {BASE_DIR}", FG_RED)
            return

        self._set_status("Launching Search Transmitters terminal...", FG_GREEN)

        # Try common Linux terminal emulators in order
        terminals = [
            ["x-terminal-emulator", "-e", f"bash -c 'cd {BASE_DIR} && python3 search_fcc.py; exec bash'"],
            ["xterm", "-e", f"bash -c 'cd {BASE_DIR} && python3 search_fcc.py; exec bash'"],
            ["gnome-terminal", "--", "bash", "-c", f"cd {BASE_DIR} && python3 search_fcc.py; exec bash"],
            ["xfce4-terminal", "-e", f"bash -c 'cd {BASE_DIR} && python3 search_fcc.py; exec bash'"],
            ["lxterminal", "-e", f"bash -c 'cd {BASE_DIR} && python3 search_fcc.py; exec bash'"],
            ["mate-terminal", "-e", f"bash -c 'cd {BASE_DIR} && python3 search_fcc.py; exec bash'"],
        ]

        launched = False
        for cmd in terminals:
            try:
                subprocess.Popen(cmd)
                launched = True
                self._set_status("✓  Search Transmitters launched in new terminal", FG_GREEN)
                break
            except FileNotFoundError:
                continue

        if not launched:
            self._set_status("⚠  No terminal emulator found — run search_fcc.py manually", FG_RED)

    def _launch_hamcall(self):
        """Launch hamcall.py as a separate window."""
        script = os.path.join(BASE_DIR, "hamcall.py")
        if not os.path.exists(script):
            self._set_status(f"⚠  hamcall.py not found at {BASE_DIR}", FG_RED)
            return

        self._set_status("Launching HamCall...", FG_AMBER)
        try:
            subprocess.Popen([sys.executable, script])
            self._set_status("✓  HamCall launched — check your taskbar!", FG_GREEN)
        except Exception as e:
            self._set_status(f"⚠  Could not launch HamCall: {e}", FG_RED)

    # ── HELPERS ─────────────────────────────────────────────────
    def _load_stats(self):
        """Load DB stats and update dashboard."""
        stats = get_db_stats()

        # Update stat cards if they exist
        for key, lbl in getattr(self, "stat_labels", {}).items():
            lbl.config(text=stats.get(key, "—"))

        # Update sidebar DB status
        self.lbl_db_status.config(
            text=stats["status"],
            fg=stats["status_color"]
        )

        self._set_status(
            f"fcc.db — {stats['status']}  |  Select a tool to get started",
            stats["status_color"]
        )

    def _set_status(self, msg, color=None):
        """Update the bottom status bar."""
        self.status_msg.config(
            text=msg,
            fg=color if color else FG_DIM
        )


def main():
    root = tk.Tk()
    app = RadiowaveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
