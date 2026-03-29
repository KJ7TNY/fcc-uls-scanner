#!/usr/bin/env python3
"""
Radiowave Connection v1.2.1
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
BASE_DIR    = os.path.expanduser("~/fcc-scanner")
DB_PATH     = os.path.join(BASE_DIR, "fcc.db")
README_PATH = os.path.join(BASE_DIR, "README.md")

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
        w, h = 860, 580                    # ← Slightly wider
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")
        root.minsize(820, 520)             # ← Better minimum size

        # Fonts
        self.font_title      = tkfont.Font(family="Courier", size=15, weight="bold")
        self.font_sub        = tkfont.Font(family="Courier", size=8)
        self.font_label      = tkfont.Font(family="Courier", size=10, weight="bold")
        self.font_value      = tkfont.Font(family="Courier", size=10)
        self.font_btn        = tkfont.Font(family="Courier", size=11, weight="bold")
        self.font_btnsub     = tkfont.Font(family="Courier", size=8)
        self.font_stat       = tkfont.Font(family="Courier", size=18, weight="bold")
        self.font_statlbl    = tkfont.Font(family="Courier", size=8)
        self.font_status     = tkfont.Font(family="Courier", size=9)
        self.font_readme     = tkfont.Font(family="Courier", size=9)
        self.font_readme_h1  = tkfont.Font(family="Courier", size=13, weight="bold")
        self.font_readme_h2  = tkfont.Font(family="Courier", size=11, weight="bold")
        self.font_readme_h3  = tkfont.Font(family="Courier", size=10, weight="bold")
        self.font_readme_code = tkfont.Font(family="Courier", size=9)

        self.active_btn = None

        self._build_ui()
        self._load_stats()

    def _build_ui(self):
        # ── Top title bar ───────────────────────────────────────
        title_bar = tk.Frame(self.root, bg=BG_SIDEBAR, pady=8)
        title_bar.pack(fill="x")

        tk.Label(title_bar,
                 text="📻  Radiowave Connection  v1.2.1",
                 font=self.font_title,
                 bg=BG_SIDEBAR, fg=FG_GREEN).pack(side="left", padx=16)

        tk.Label(title_bar,
                 text="KJ7TNY & The Wizard 🧙  |  The Jailhouse Edition",
                 font=self.font_sub,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(side="right", padx=16)

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

        # ── Main body ───────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        # ── LEFT SIDEBAR ────────────────────────────────────────
        sidebar = tk.Frame(body, bg=BG_SIDEBAR)
        sidebar.pack(side="left", fill="y")
        # No fixed width — auto-sizes to content!

        tk.Label(sidebar, text="— TOOLS —",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(pady=(16, 8), padx=12)

        # Active buttons
        self.btn_search = self._make_sidebar_btn(
            sidebar,
            "🔍  Search Transmitters",
            "Part 90 — search_fcc.py",
            self._launch_search
        )

        self.btn_hamcall = self._make_sidebar_btn(
            sidebar,
            "📡  HamCall+ Lookup",
            "Ham & GMRS — hamcall.py",
            self._launch_hamcall
        )

        # ── INFO section ────────────────────────────────────────
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=12)

        tk.Label(sidebar, text="— INFO —",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(pady=(0, 8), padx=12)

        self.btn_readme = self._make_sidebar_btn(
            sidebar,
            "📖  README / Help",
            "Docs — open inside app",
            self._show_readme
        )

        self._make_sidebar_btn(sidebar, "📋  Reports",
                                "View saved searches",
                                self._show_reports)

        # ── COMING SOON ─────────────────────────────────────────
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=12)

        tk.Label(sidebar, text="— COMING SOON —",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(pady=(0, 8), padx=12)

        self._make_sidebar_btn_dim(sidebar, "🔄  Update Databases",  "Download + import")
        self._make_sidebar_btn_dim(sidebar, "🔧  Toolbox",           "Ham radio utilities")

        # Push the database status to the bottom
        tk.Frame(sidebar, bg=BG_SIDEBAR).pack(fill="y", expand=True)

        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x", padx=12, pady=4)

        self.lbl_db_status = tk.Label(
            sidebar,
            text="fcc.db — checking...",
            font=self.font_statlbl,
            bg=BG_SIDEBAR, fg=FG_DIM,
            wraplength=240,          # Helps if text gets long
            justify="center"
        )
        self.lbl_db_status.pack(pady=(4, 16), padx=12)

        # Sidebar right border — the green line!
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── RIGHT CONTENT PANEL ─────────────────────────────────
        self.content = tk.Frame(body, bg=BG_DARK)
        self.content.pack(side="left", fill="both", expand=True)

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
        """Create an active sidebar button - auto-sizing and safe padding."""
        frame = tk.Frame(parent, bg=BG_SIDEBAR, cursor="hand2")
        frame.pack(fill="x", padx=12, pady=3)

        inner = tk.Frame(frame, bg=BTN_ACTIVE,
                         highlightbackground=BORDER,
                         highlightthickness=1)
        inner.pack(fill="x")

        # Title label
        title_lbl = tk.Label(inner, 
                             text=title,
                             font=self.font_label,
                             bg=BTN_ACTIVE, 
                             fg=FG_GREEN,
                             anchor="w", 
                             justify="left",
                             padx=12, 
                             pady=4,           # ← Safe single value instead of tuple
                             wraplength=240)
        title_lbl.pack(fill="x")

        # Subtitle label
        sub_lbl = tk.Label(inner, 
                           text=subtitle,
                           font=self.font_btnsub,
                           bg=BTN_ACTIVE, 
                           fg=FG_DIM,
                           anchor="w", 
                           justify="left",
                           padx=12, 
                           pady=4,           # ← Safe single value
                           wraplength=240)
        sub_lbl.pack(fill="x")

        # Bind clicks to the whole button
        for widget in [frame, inner, title_lbl, sub_lbl]:
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

        hdr = tk.Frame(self.content, bg=BG_DARK, pady=20)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr,
                 text="Welcome to the Radiowave Connection",
                 font=self.font_btn,
                 bg=BG_DARK, fg=FG_GREEN).pack(anchor="w")

        tk.Label(hdr,
                 text="Your offline Swiss Army Knife for FCC radio data  —  30 million records, zero internet needed",
                 font=self.font_sub,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(4, 0))

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24)

        stats_frame = tk.Frame(self.content, bg=BG_DARK, pady=20)
        stats_frame.pack(fill="x", padx=24)

        tk.Label(stats_frame, text="— DATABASE STATS —",
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(0, 12))

        cards = tk.Frame(stats_frame, bg=BG_DARK)
        cards.pack(fill="x")

        self.stat_labels = {}

        stat_defs = [
            ("licenses",     "Active Licenses",   "Part 90"),
            ("transmitters", "Transmitter Sites",  "with GPS"),
            ("amateur",      "Ham Callsigns",      "amateur"),
            ("gmrs",         "GMRS Licenses",      "family radio"),
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

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(8, 0))

        tools_frame = tk.Frame(self.content, bg=BG_DARK, pady=16)
        tools_frame.pack(fill="x", padx=24)

        tk.Label(tools_frame, text="— QUICK LAUNCH —",
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(anchor="w", pady=(0, 12))

        launch_row = tk.Frame(tools_frame, bg=BG_DARK)
        launch_row.pack(fill="x")

        self._make_launch_card(
            launch_row,
            "🔍  Search Transmitters",
            "Find any transmitter by county, radius,\ncity, frequency, call sign, or FRN",
            "Launch Terminal",
            self._launch_search,
            FG_GREEN
        )

        self._make_launch_card(
            launch_row,
            "📡  HamCall+ Lookup",
            "Look up any ham or GMRS callsign\ninstantly from 3.9M+ offline records",
            "Open HamCall+",
            self._launch_hamcall,
            FG_AMBER
        )

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24, pady=(8, 0))
        tk.Label(self.content,
                 text='"I Will Find You"  📻  — Minty & The Wizard 🧙',
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM).pack(pady=8)

        # Reload stats every time dashboard is shown
        self._load_stats()

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

    # ── README VIEWER ───────────────────────────────────────────
    def _show_readme(self):
        """Display README.md inside the content panel."""
        self._clear_content()
        self._set_status("📖  README / Help", FG_GREEN)

        # Header row
        hdr = tk.Frame(self.content, bg=BG_DARK, pady=12)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr, text="📖  README / Help",
                 font=self.font_btn,
                 bg=BG_DARK, fg=FG_GREEN).pack(side="left")

        back_btn = tk.Button(hdr,
                             text="⌂  Dashboard",
                             font=self.font_statlbl,
                             bg=BTN_ACTIVE, fg=FG_DIM,
                             activebackground=HIGHLIGHT,
                             activeforeground=FG_GREEN,
                             relief="flat", bd=0,
                             padx=10, pady=4,
                             cursor="hand2",
                             command=self._show_dashboard)
        back_btn.pack(side="right")
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg=HIGHLIGHT, fg=FG_GREEN))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg=BTN_ACTIVE, fg=FG_DIM))

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24)

        # Scrollable text area
        text_frame = tk.Frame(self.content, bg=BG_DARK)
        text_frame.pack(fill="both", expand=True, padx=16, pady=8)

        scrollbar = tk.Scrollbar(text_frame, bg=BG_SIDEBAR,
                                 troughcolor=BG_DARK,
                                 activebackground=FG_DIM)
        scrollbar.pack(side="right", fill="y")

        self.readme_text = tk.Text(
            text_frame,
            bg=BG_PANEL,
            fg=FG_WHITE,
            font=self.font_readme,
            relief="flat",
            bd=0,
            highlightthickness=0,
            highlightbackground=BG_PANEL,
            wrap="word",
            cursor="arrow",
            state="disabled",
            yscrollcommand=scrollbar.set,
            padx=16,
            pady=12,
            spacing1=2,
            spacing2=2,
            spacing3=4,
        )
        self.readme_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.readme_text.yview)
        self.readme_text.bind("<Button-3>", lambda e: self._show_copy_menu(e, self.readme_text))

        # Text tags for markdown styling
        self.readme_text.tag_configure("h1",
            font=self.font_readme_h1, foreground=FG_GREEN,
            spacing1=10, spacing3=4)
        self.readme_text.tag_configure("h2",
            font=self.font_readme_h2, foreground=FG_GREEN,
            spacing1=8, spacing3=2)
        self.readme_text.tag_configure("h3",
            font=self.font_readme_h3, foreground=FG_AMBER,
            spacing1=6, spacing3=2)
        self.readme_text.tag_configure("codeline",
            font=self.font_readme_code, foreground=FG_AMBER,
            background=BG_DARK, lmargin1=16, lmargin2=16)
        self.readme_text.tag_configure("bullet",
            foreground=FG_WHITE, lmargin1=16, lmargin2=24)
        self.readme_text.tag_configure("separator",
            foreground=FG_DIM)
        self.readme_text.tag_configure("dim",
            foreground=FG_DIM)
        self.readme_text.tag_configure("normal",
            foreground=FG_WHITE)

        self._render_readme()

    def _render_readme(self):
        """Load README.md and render with basic markdown styling."""
        self.readme_text.config(state="normal")
        self.readme_text.delete("1.0", tk.END)

        if not os.path.exists(README_PATH):
            self.readme_text.insert(tk.END, "README.md not found!\n\n", "h2")
            self.readme_text.insert(tk.END,
                f"Expected location:\n  {README_PATH}\n\n", "normal")
            self.readme_text.insert(tk.END,
                "Make sure README.md is in your ~/fcc-scanner/ folder.", "dim")
            self.readme_text.config(state="disabled")
            return

        try:
            with open(README_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            self.readme_text.insert(tk.END, f"Error reading README: {e}", "dim")
            self.readme_text.config(state="disabled")
            return

        in_code_block = False

        for line in lines:
            stripped = line.rstrip("\n")

            # Code block toggle
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                self.readme_text.insert(tk.END, "\n", "normal")
                continue

            if in_code_block:
                self.readme_text.insert(tk.END, stripped + "\n", "codeline")
                continue

            # Headings
            if stripped.startswith("### "):
                self.readme_text.insert(tk.END, stripped[4:] + "\n", "h3")
            elif stripped.startswith("## "):
                self.readme_text.insert(tk.END, stripped[3:] + "\n", "h2")
            elif stripped.startswith("# "):
                self.readme_text.insert(tk.END, stripped[2:] + "\n", "h1")
            # Horizontal rule
            elif stripped.startswith("---"):
                self.readme_text.insert(tk.END, "─" * 60 + "\n", "separator")
            # Bullet points
            elif stripped.startswith("- ") or stripped.startswith("* "):
                self.readme_text.insert(tk.END,
                    "  •  " + stripped[2:] + "\n", "bullet")
            # Numbered list
            elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".)":
                self.readme_text.insert(tk.END, "  " + stripped + "\n", "bullet")
            # Empty line
            elif stripped == "":
                self.readme_text.insert(tk.END, "\n", "normal")
            # Normal text
            else:
                self.readme_text.insert(tk.END, stripped + "\n", "normal")

        self.readme_text.config(state="disabled")
        self.readme_text.yview_moveto(0)
        self._set_status("📖  README loaded — scroll to read  |  click ⌂ Dashboard to go back", FG_GREEN)

    # ── REPORTS VIEWER ──────────────────────────────────────────
    def _show_reports(self):
        """Show list of saved reports — click one to read it."""
        self._clear_content()
        self._set_status("📋  Reports — saved search results", FG_GREEN)

        reports_dir = os.path.join(BASE_DIR, "reports")

        # Header
        hdr = tk.Frame(self.content, bg=BG_DARK, pady=12)
        hdr.pack(fill="x", padx=24)

        tk.Label(hdr, text="📋  Saved Reports",
                 font=self.font_btn,
                 bg=BG_DARK, fg=FG_GREEN).pack(side="left")

        back_btn = tk.Button(hdr,
                             text="⌂  Dashboard",
                             font=self.font_statlbl,
                             bg=BTN_ACTIVE, fg=FG_DIM,
                             activebackground=HIGHLIGHT,
                             activeforeground=FG_GREEN,
                             relief="flat", bd=0,
                             padx=10, pady=4,
                             cursor="hand2",
                             command=self._show_dashboard)
        back_btn.pack(side="right")
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg=HIGHLIGHT, fg=FG_GREEN))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg=BTN_ACTIVE, fg=FG_DIM))

        tk.Frame(self.content, bg=BORDER, height=1).pack(fill="x", padx=24)

        # Check reports folder exists
        if not os.path.exists(reports_dir):
            tk.Label(self.content,
                     text="\n  No reports folder found yet.\n  Run a search and save it first!",
                     font=self.font_value,
                     bg=BG_DARK, fg=FG_DIM,
                     justify="left").pack(anchor="w", padx=24, pady=20)
            return

        # Get report files sorted newest first
        files = sorted(
            [f for f in os.listdir(reports_dir) if f.endswith(".txt")],
            reverse=True
        )

        if not files:
            tk.Label(self.content,
                     text="\n  No saved reports yet.\n  Run a search and save it — files appear here!",
                     font=self.font_value,
                     bg=BG_DARK, fg=FG_DIM,
                     justify="left").pack(anchor="w", padx=24, pady=20)
            return

        # Split view — file list left, content right
        split = tk.Frame(self.content, bg=BG_DARK)
        split.pack(fill="both", expand=True, padx=16, pady=8)

        # ── File list panel — auto-sizes to longest filename ────
        list_frame = tk.Frame(split, bg=BG_SIDEBAR)
        list_frame.pack(side="left", fill="y")

        tk.Label(list_frame,
                 text=f"  {len(files)} report(s) — newest first",
                 font=self.font_statlbl,
                 bg=BG_SIDEBAR, fg=FG_DIM).pack(anchor="w", pady=(8, 4))

        tk.Frame(list_frame, bg=BORDER, height=1).pack(fill="x")

        list_scroll = tk.Scrollbar(list_frame, bg=BG_SIDEBAR,
                                   troughcolor=BG_DARK,
                                   activebackground=FG_DIM)
        # Don't pack yet — auto-hide scrollbar shows only when needed!

        # Calculate width from longest filename so nothing gets chopped
        max_len = max(len(f) for f in files) + 4 - 4  # -4 for .txt we strip

        def _autohide_scroll(first, last):
            """Show scrollbar only when list overflows."""
            first, last = float(first), float(last)
            if first <= 0.0 and last >= 1.0:
                list_scroll.pack_forget()   # all items visible — hide it
            else:
                list_scroll.pack(side="right", fill="y")  # overflow — show it
            list_scroll.set(first, last)

        self.file_listbox = tk.Listbox(
            list_frame,
            bg=BG_PANEL,
            fg=FG_WHITE,
            font=self.font_statlbl,
            relief="flat",
            bd=0,
            highlightthickness=0,
            highlightbackground=BG_PANEL,
            width=max_len,
            selectbackground=HIGHLIGHT,
            selectforeground=FG_GREEN,
            activestyle="none",
            exportselection=0,
            yscrollcommand=_autohide_scroll,
            cursor="hand2"
        )
        self.file_listbox.pack(side="left", fill="both", expand=True)
        list_scroll.config(command=self.file_listbox.yview)

        for f in files:
            display = f[:-4] if f.endswith(".txt") else f  # strip .txt for display
            self.file_listbox.insert(tk.END, f"  {display}")

        # ── Divider ─────────────────────────────────────────────
        tk.Frame(split, bg=BORDER, width=1).pack(side="left", fill="y")

        # ── Report content panel ─────────────────────────────────
        content_frame = tk.Frame(split, bg=BG_DARK)
        content_frame.pack(side="left", fill="both", expand=True)

        self.report_filename_lbl = tk.Label(
                 content_frame,
                 text="  ← Select a report to read it",
                 font=self.font_statlbl,
                 bg=BG_DARK, fg=FG_DIM)
        self.report_filename_lbl.pack(anchor="w", pady=(8, 4))

        tk.Frame(content_frame, bg=BORDER, height=1).pack(fill="x")

        report_scroll = tk.Scrollbar(content_frame, bg=BG_SIDEBAR,
                                     troughcolor=BG_DARK,
                                     activebackground=FG_DIM)
        report_scroll.pack(side="right", fill="y")

        self.report_text = tk.Text(
            content_frame,
            bg=BG_PANEL,
            fg=FG_AMBER,
            font=self.font_readme,
            relief="flat",
            bd=0,
            highlightthickness=0,
            highlightbackground=BG_PANEL,
            wrap="word",
            state="disabled",
            yscrollcommand=report_scroll.set,
            padx=12,
            pady=8,
        )
        self.report_text.pack(side="left", fill="both", expand=True)
        report_scroll.config(command=self.report_text.yview)
        self.report_text.bind("<Button-3>", lambda e: self._show_copy_menu(e, self.report_text))

        self._report_files = files
        self._reports_dir  = reports_dir
        self.file_listbox.bind("<<ListboxSelect>>", self._load_report)

        self._set_status(
            f"📋  {len(files)} saved report(s) — click one to read",
            FG_GREEN)

    def _show_copy_menu(self, event, widget):
        """Show right-click context menu with Copy and Select All."""
        menu = tk.Menu(self.root,
                       tearoff=0,
                       bg=BG_PANEL,
                       fg=FG_GREEN,
                       activebackground=HIGHLIGHT,
                       activeforeground=FG_GREEN,
                       relief="flat",
                       bd=1)
        menu.add_command(
            label="  Copy  ",
            command=lambda: self._copy_selection(widget)
        )
        menu.add_command(
            label="  Select All  ",
            command=lambda: self._select_all(widget)
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _copy_selection(self, widget):
        """Copy selected text to clipboard."""
        try:
            selected = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected)
        except tk.TclError:
            pass

    def _select_all(self, widget):
        """Select all text in widget."""
        widget.tag_add(tk.SEL, "1.0", tk.END)
        widget.mark_set(tk.INSERT, "1.0")
        widget.see(tk.INSERT)

    def _load_report(self, event):
        """Load selected report file into the viewer."""
        selection = self.file_listbox.curselection()
        if not selection:
            return

        filename = self._report_files[selection[0]]
        filepath = os.path.join(self._reports_dir, filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            content = f"Error reading file: {e}"

        # Update filename label at top of content panel
        display_name = filename[:-4] if filename.endswith(".txt") else filename
        self.report_filename_lbl.config(
            text=f"  📋  {display_name}",
            fg=FG_AMBER)

        self.report_text.config(state="normal")
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, content)
        self.report_text.config(state="disabled")
        self.report_text.yview_moveto(0)
        self._set_status(f"📋  {display_name}", FG_GREEN)

    # ── TOOL LAUNCHERS ──────────────────────────────────────────
    def _launch_search(self):
        """Launch search_fcc.py in a new terminal window."""
        script = os.path.join(BASE_DIR, "search_fcc.py")
        if not os.path.exists(script):
            self._set_status(f"⚠  search_fcc.py not found at {BASE_DIR}", FG_RED)
            return

        self._set_status("Launching Search Transmitters terminal...", FG_GREEN)

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

        self._set_status("Launching HamCall+...", FG_AMBER)
        try:
            subprocess.Popen([sys.executable, script])
            self._set_status("✓  HamCall+ launched — check your taskbar!", FG_GREEN)
        except Exception as e:
            self._set_status(f"⚠  Could not launch HamCall+: {e}", FG_RED)

    # ── HELPERS ─────────────────────────────────────────────────
    def _load_stats(self):
        """Load DB stats and update dashboard."""
        stats = get_db_stats()

        for key, lbl in getattr(self, "stat_labels", {}).items():
            lbl.config(text=stats.get(key, "—"))

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
        if not hasattr(self, "status_msg"):
            return
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
