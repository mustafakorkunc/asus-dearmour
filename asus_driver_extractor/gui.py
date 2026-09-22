"""
Graphical User Interface (GUI) for DeArmour.
Features ASUS Hardware Auto-Detection, Official ASUS Cloud Driver Downloader,
Pure INF/SYS Extraction Engine, One-Click Automated Deployment Script Generation,
Multi-Theme Support (including Hacker Mode / Matrix), and an About & Community Hub.

Special thanks and architectural attribution to:
- Seerge & the G-Helper project (https://github.com/seerge/g-helper)
  for pioneering the reverse engineering and discovery of the official ASUS Support REST API.
"""

import io
import os
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Dict, List, Any
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Safeguard for windowed executable (no console)
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from asus_driver_extractor import __version__
from asus_driver_extractor.cli import collect_target_files, run_pipeline
from asus_driver_extractor.core.asus_downloader import AsusDownloader, AsusDriverPackage


THEMES: Dict[str, Dict[str, str]] = {
    "Catppuccin Mocha": {
        "name": "Catppuccin Mocha",
        "bg_color": "#1e1e2e",
        "card_bg": "#28283d",
        "card_secondary": "#181825",
        "fg_color": "#cdd6f4",
        "accent_color": "#89b4fa",
        "btn_bg": "#313244",
        "btn_hover": "#45475a",
        "btn_fg": "#cdd6f4",
        "btn_accent_bg": "#b4befe",
        "btn_accent_fg": "#11111b",
        "success_color": "#a6e3a1",
        "warning_color": "#f9e2af",
        "text_bg": "#11111b",
        "entry_bg": "#181825",
        "muted_fg": "#a6adc8",
        "log_fg": "#a6adc8",
        "tree_select": "#45475a",
        "border_color": "#45475a",
    },
    "Hacker Mode (Matrix)": {
        "name": "Hacker Mode (Matrix)",
        "bg_color": "#070c08",
        "card_bg": "#0f1710",
        "card_secondary": "#0a100a",
        "fg_color": "#00ff66",
        "accent_color": "#00ff66",
        "btn_bg": "#142616",
        "btn_hover": "#1f3b23",
        "btn_fg": "#00ff66",
        "btn_accent_bg": "#00ff66",
        "btn_accent_fg": "#000000",
        "success_color": "#00ff66",
        "warning_color": "#ffe600",
        "text_bg": "#020502",
        "entry_bg": "#071008",
        "muted_fg": "#33aa55",
        "log_fg": "#00ff66",
        "tree_select": "#1a381d",
        "border_color": "#00ff66",
    },
    "Cyberpunk Neon": {
        "name": "Cyberpunk Neon",
        "bg_color": "#0d0b1a",
        "card_bg": "#181432",
        "card_secondary": "#110e26",
        "fg_color": "#f0f0ff",
        "accent_color": "#00f0ff",
        "btn_bg": "#281e52",
        "btn_hover": "#3f2c82",
        "btn_fg": "#ff79c6",
        "btn_accent_bg": "#00f0ff",
        "btn_accent_fg": "#0d0b1a",
        "success_color": "#00f0ff",
        "warning_color": "#ffb86c",
        "text_bg": "#07050e",
        "entry_bg": "#110e24",
        "muted_fg": "#a292ca",
        "log_fg": "#00f0ff",
        "tree_select": "#3d2b78",
        "border_color": "#ff007f",
    },
    "Nordic Dark": {
        "name": "Nordic Dark",
        "bg_color": "#242933",
        "card_bg": "#2e3440",
        "card_secondary": "#21252b",
        "fg_color": "#eceff4",
        "accent_color": "#88c0d0",
        "btn_bg": "#3b4252",
        "btn_hover": "#4c566a",
        "btn_fg": "#eceff4",
        "btn_accent_bg": "#88c0d0",
        "btn_accent_fg": "#2e3440",
        "success_color": "#a3be8c",
        "warning_color": "#ebcb8b",
        "text_bg": "#1e222a",
        "entry_bg": "#282c34",
        "muted_fg": "#d8dee9",
        "log_fg": "#d8dee9",
        "tree_select": "#434c5e",
        "border_color": "#4c566a",
    },
    "Clean Light": {
        "name": "Clean Light",
        "bg_color": "#f0f2f5",
        "card_bg": "#ffffff",
        "card_secondary": "#f6f8fa",
        "fg_color": "#1f2328",
        "accent_color": "#0969da",
        "btn_bg": "#eaeef2",
        "btn_hover": "#d0d7de",
        "btn_fg": "#1f2328",
        "btn_accent_bg": "#0969da",
        "btn_accent_fg": "#ffffff",
        "success_color": "#1a7f37",
        "warning_color": "#9a6700",
        "text_bg": "#f6f8fa",
        "entry_bg": "#ffffff",
        "muted_fg": "#656d76",
        "log_fg": "#1f2328",
        "tree_select": "#d0d7de",
        "border_color": "#d0d7de",
    },
}


class DeArmourGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"DeArmour v{__version__} - ASUS Driver Stripper & Cloud Downloader")
        self.root.geometry("900x700")
        self.root.minsize(820, 620)

        # Theme Tracking Collections
        self.theme_widgets_bg: List[tk.Widget] = []
        self.theme_widgets_card: List[tk.Widget] = []
        self.theme_widgets_card_sec: List[tk.Widget] = []
        self.theme_widgets_fg_label: List[tk.Widget] = []
        self.theme_widgets_muted_label: List[tk.Widget] = []
        self.theme_widgets_accent_label: List[tk.Widget] = []
        self.theme_widgets_btn_standard: List[tk.Widget] = []
        self.theme_widgets_btn_accent: List[tk.Widget] = []
        self.theme_widgets_entry: List[tk.Widget] = []

        # Initialize Default Theme (Catppuccin Mocha)
        self.current_theme = "Catppuccin Mocha"
        t = THEMES[self.current_theme]
        self.bg_color = t["bg_color"]
        self.card_bg = t["card_bg"]
        self.card_secondary = t["card_secondary"]
        self.fg_color = t["fg_color"]
        self.accent_color = t["accent_color"]
        self.btn_bg = t["btn_bg"]
        self.btn_hover = t["btn_hover"]
        self.btn_fg = t["btn_fg"]
        self.btn_accent_bg = t["btn_accent_bg"]
        self.btn_accent_fg = t["btn_accent_fg"]
        self.success_color = t["success_color"]
        self.warning_color = t["warning_color"]
        self.text_bg = t["text_bg"]
        self.entry_bg = t["entry_bg"]
        self.muted_fg = t["muted_fg"]
        self.log_fg = t["log_fg"]

        self.root.configure(bg=self.bg_color)
        self.theme_widgets_bg.append(self.root)

        self.downloader = AsusDownloader()
        self.detected_system = self.downloader.detect_local_system()
        self.fetched_packages: List[AsusDriverPackage] = []
        self.package_map: Dict[str, AsusDriverPackage] = {}

        self._init_styles()
        self._build_ui()
        self._apply_detected_system()

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Notebook tabs styling
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.btn_bg,
            foreground=self.fg_color,
            padding=[16, 8],
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.card_bg)],
            foreground=[("selected", self.accent_color)],
        )

        # Treeview styling
        style.configure(
            "Treeview",
            background=self.text_bg,
            foreground=self.fg_color,
            fieldbackground=self.text_bg,
            rowheight=26,
            font=("Segoe UI", 9),
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=self.btn_bg,
            foreground=self.accent_color,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
        )
        style.map("Treeview", background=[("selected", THEMES[self.current_theme]["tree_select"])])

        # Progressbar styling
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.card_bg,
            background=self.accent_color,
            thickness=6,
        )

    def _build_ui(self):
        # 1. Header Frame
        self.header = tk.Frame(self.root, bg=self.bg_color, pady=10)
        self.header.pack(fill=tk.X, padx=20)
        self.theme_widgets_bg.append(self.header)

        # Title Left Box
        self.title_box = tk.Frame(self.header, bg=self.bg_color)
        self.title_box.pack(side=tk.LEFT)
        self.theme_widgets_bg.append(self.title_box)

        self.title_lbl = tk.Label(
            self.title_box,
            text="DeArmour",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        )
        self.title_lbl.pack(side=tk.LEFT)
        self.theme_widgets_bg.append(self.title_lbl)
        self.theme_widgets_accent_label.append(self.title_lbl)

        self.version_lbl = tk.Label(
            self.title_box,
            text=f"v{__version__}",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg=self.muted_fg,
            padx=8,
            pady=4,
        )
        self.version_lbl.pack(side=tk.LEFT)
        self.theme_widgets_bg.append(self.version_lbl)
        self.theme_widgets_muted_label.append(self.version_lbl)

        # Theme & Toolbar Right Box
        self.header_tools = tk.Frame(self.header, bg=self.bg_color)
        self.header_tools.pack(side=tk.RIGHT, pady=2)
        self.theme_widgets_bg.append(self.header_tools)

        self.theme_lbl = tk.Label(
            self.header_tools,
            text="Theme:",
            font=("Segoe UI", 9, "bold"),
            bg=self.bg_color,
            fg=self.fg_color,
        )
        self.theme_lbl.pack(side=tk.LEFT, padx=(0, 6))
        self.theme_widgets_bg.append(self.theme_lbl)
        self.theme_widgets_fg_label.append(self.theme_lbl)

        self.theme_combo = ttk.Combobox(
            self.header_tools,
            values=list(THEMES.keys()),
            width=20,
            state="readonly",
        )
        self.theme_combo.current(0)
        self.theme_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)

        self.about_header_btn = tk.Button(
            self.header_tools,
            text="ℹ️ About & Links",
            command=self._switch_to_about,
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
        )
        self.about_header_btn.pack(side=tk.LEFT)
        self.theme_widgets_btn_standard.append(self.about_header_btn)

        self.subtitle_lbl = tk.Label(
            self.header,
            text="Extract pure, bare-metal INF/SYS drivers from ASUS packages & download directly from ASUS servers.",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.muted_fg,
        )
        self.subtitle_lbl.pack(anchor="w", pady=(2, 0))
        self.theme_widgets_bg.append(self.subtitle_lbl)
        self.theme_widgets_muted_label.append(self.subtitle_lbl)

        # 2. Main Tabs (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=False, padx=20, pady=(5, 5))

        self.tab_cloud = tk.Frame(self.notebook, bg=self.card_bg, padx=15, pady=12)
        self.tab_local = tk.Frame(self.notebook, bg=self.card_bg, padx=15, pady=15)
        self.tab_about = tk.Frame(self.notebook, bg=self.card_bg, padx=15, pady=15)
        self.theme_widgets_card.extend([self.tab_cloud, self.tab_local, self.tab_about])

        self.notebook.add(self.tab_cloud, text="  ASUS Cloud Downloader  ")
        self.notebook.add(self.tab_local, text="  Local File Extractor  ")
        self.notebook.add(self.tab_about, text="  ℹ️ About & Community  ")

        self._build_cloud_tab()
        self._build_local_tab()
        self._build_about_tab()

        # 3. Status & Progress Indicator
        self.status_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=6)
        self.status_frame.pack(fill=tk.X)
        self.theme_widgets_bg.append(self.status_frame)

        self.status_lbl = tk.Label(
            self.status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.muted_fg,
            anchor="w",
        )
        self.status_lbl.pack(fill=tk.X)
        self.theme_widgets_bg.append(self.status_lbl)
        self.theme_widgets_muted_label.append(self.status_lbl)

        self.prog = ttk.Progressbar(self.root, style="Horizontal.TProgressbar", mode="determinate")
        self.prog.pack(fill=tk.X, padx=20, pady=(2, 6))

        # 4. Shared Console Log Frame
        self.log_frame = tk.Frame(self.root, bg=self.bg_color, padx=20)
        self.log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.theme_widgets_bg.append(self.log_frame)

        self.log_text = tk.Text(
            self.log_frame,
            bg=self.text_bg,
            fg=self.log_fg,
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=10,
            pady=8,
            height=7,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 5. Bottom Action Bar & Footer
        self.footer_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=8)
        self.footer_frame.pack(fill=tk.X)
        self.theme_widgets_bg.append(self.footer_frame)

        self.footer_btn_box = tk.Frame(self.footer_frame, bg=self.bg_color)
        self.footer_btn_box.pack(side=tk.LEFT)
        self.theme_widgets_bg.append(self.footer_btn_box)

        self.open_downloads_btn = tk.Button(
            self.footer_btn_box,
            text="Open Downloads Folder",
            command=self._open_downloads,
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.open_downloads_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.theme_widgets_btn_standard.append(self.open_downloads_btn)

        self.open_extracted_btn = tk.Button(
            self.footer_btn_box,
            text="Open Extracted Drivers Folder",
            command=self._open_extracted,
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        self.open_extracted_btn.pack(side=tk.LEFT)
        self.theme_widgets_btn_standard.append(self.open_extracted_btn)

        self.footer_lbl = tk.Label(
            self.footer_frame,
            text="DeArmour by Mustafa Korkunç  |  API discovery inspired by G-Helper (seerge/g-helper)",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg=self.muted_fg,
        )
        self.footer_lbl.pack(side=tk.RIGHT)
        self.theme_widgets_bg.append(self.footer_lbl)
        self.theme_widgets_muted_label.append(self.footer_lbl)

    def _build_cloud_tab(self):
        # System Hardware Info Card
        self.sys_card = tk.Frame(self.tab_cloud, bg=self.card_secondary, padx=12, pady=8, relief=tk.FLAT)
        self.sys_card.pack(fill=tk.X, pady=(0, 10))
        self.theme_widgets_card_sec.append(self.sys_card)

        self.sys_info_lbl = tk.Label(
            self.sys_card,
            text="Detecting system hardware...",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_secondary,
            fg=self.success_color,
            anchor="w",
        )
        self.sys_info_lbl.pack(side=tk.LEFT)
        self.theme_widgets_card_sec.append(self.sys_info_lbl)

        # Query Controls
        self.query_bar = tk.Frame(self.tab_cloud, bg=self.card_bg)
        self.query_bar.pack(fill=tk.X, pady=(0, 8))
        self.theme_widgets_card.append(self.query_bar)

        self.model_lbl = tk.Label(self.query_bar, text="Model:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold"))
        self.model_lbl.pack(side=tk.LEFT)
        self.theme_widgets_card.append(self.model_lbl)
        self.theme_widgets_fg_label.append(self.model_lbl)

        self.model_entry = tk.Entry(self.query_bar, font=("Segoe UI", 9), bg=self.entry_bg, fg=self.fg_color, width=14, insertbackground=self.fg_color)
        self.model_entry.pack(side=tk.LEFT, padx=6)
        self.theme_widgets_entry.append(self.model_entry)

        self.os_lbl = tk.Label(self.query_bar, text="OS:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold"))
        self.os_lbl.pack(side=tk.LEFT, padx=(6, 0))
        self.theme_widgets_card.append(self.os_lbl)
        self.theme_widgets_fg_label.append(self.os_lbl)

        self.os_combo = ttk.Combobox(
            self.query_bar,
            values=["Windows 11 64-bit", "Windows 10 64-bit"],
            width=18,
            state="readonly",
        )
        self.os_combo.current(0)
        self.os_combo.pack(side=tk.LEFT, padx=6)

        self.fetch_btn = tk.Button(
            self.query_bar,
            text="Fetch Drivers from ASUS",
            command=self._fetch_drivers,
            bg=self.accent_color,
            fg=self.btn_accent_fg,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
        )
        self.fetch_btn.pack(side=tk.LEFT, padx=8)
        self.theme_widgets_btn_accent.append(self.fetch_btn)

        # Driver Selection Treeview
        self.tree_container = tk.Frame(self.tab_cloud, bg=self.card_bg)
        self.tree_container.pack(fill=tk.BOTH, expand=True, pady=4)
        self.theme_widgets_card.append(self.tree_container)

        columns = ("Category", "Title", "Version", "Date", "Size")
        self.driver_tree = ttk.Treeview(
            self.tree_container,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=6,
        )

        self.driver_tree.heading("Category", text="Category")
        self.driver_tree.heading("Title", text="Driver Package Title")
        self.driver_tree.heading("Version", text="Version")
        self.driver_tree.heading("Date", text="Date")
        self.driver_tree.heading("Size", text="Size")

        self.driver_tree.column("Category", width=120, minwidth=90)
        self.driver_tree.column("Title", width=310, minwidth=180)
        self.driver_tree.column("Version", width=130, minwidth=100)
        self.driver_tree.column("Date", width=90, minwidth=80)
        self.driver_tree.column("Size", width=80, minwidth=70)

        self.driver_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll = tk.Scrollbar(self.tree_container, command=self.driver_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.driver_tree.config(yscrollcommand=tree_scroll.set)

        self.driver_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Quick Selection Bar & Count
        self.sel_bar = tk.Frame(self.tab_cloud, bg=self.card_bg, pady=4)
        self.sel_bar.pack(fill=tk.X)
        self.theme_widgets_card.append(self.sel_bar)

        self.sel_all_btn = tk.Button(self.sel_bar, text="Select All", command=self._select_all_drivers, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, font=("Segoe UI", 8), padx=8, cursor="hand2")
        self.sel_all_btn.pack(side=tk.LEFT, padx=2)
        self.theme_widgets_btn_standard.append(self.sel_all_btn)

        self.sel_clear_btn = tk.Button(self.sel_bar, text="Clear", command=self._clear_selection, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, font=("Segoe UI", 8), padx=8, cursor="hand2")
        self.sel_clear_btn.pack(side=tk.LEFT, padx=2)
        self.theme_widgets_btn_standard.append(self.sel_clear_btn)

        self.sel_ess_btn = tk.Button(self.sel_bar, text="Select Essentials", command=self._select_essential_drivers, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, font=("Segoe UI", 8), padx=8, cursor="hand2")
        self.sel_ess_btn.pack(side=tk.LEFT, padx=2)
        self.theme_widgets_btn_standard.append(self.sel_ess_btn)

        self.sel_count_lbl = tk.Label(
            self.sel_bar,
            text="0 drivers selected",
            bg=self.card_bg,
            fg=self.muted_fg,
            font=("Segoe UI", 8),
        )
        self.sel_count_lbl.pack(side=tk.RIGHT)
        self.theme_widgets_card.append(self.sel_count_lbl)
        self.theme_widgets_muted_label.append(self.sel_count_lbl)

        # Action Buttons (Download & Extract)
        self.act_box = tk.Frame(self.tab_cloud, bg=self.card_bg, pady=6)
        self.act_box.pack(fill=tk.X)
        self.theme_widgets_card.append(self.act_box)

        self.download_btn = tk.Button(
            self.act_box,
            text="Download Selected",
            command=self._start_download_selected,
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=5,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.theme_widgets_btn_standard.append(self.download_btn)

        self.pipeline_btn = tk.Button(
            self.act_box,
            text="Download & DeArmour (Full Pipeline)",
            command=self._start_cloud_pipeline,
            bg=self.btn_accent_bg,
            fg=self.btn_accent_fg,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=5,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.pipeline_btn.pack(side=tk.LEFT)
        self.theme_widgets_btn_accent.append(self.pipeline_btn)

    def _build_local_tab(self):
        self.local_desc_lbl = tk.Label(
            self.tab_local,
            text="Select an ASUS driver installer .exe or folder containing multiple packages to strip into bare-metal INF/SYS drivers.",
            bg=self.card_bg,
            fg=self.muted_fg,
            font=("Segoe UI", 9),
        )
        self.local_desc_lbl.pack(anchor="w", pady=(0, 12))
        self.theme_widgets_card.append(self.local_desc_lbl)
        self.theme_widgets_muted_label.append(self.local_desc_lbl)

        # Input Path
        self.inp_lbl = tk.Label(self.tab_local, text="Driver Package (.exe) or Directory:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold"))
        self.inp_lbl.pack(anchor="w", pady=(2, 2))
        self.theme_widgets_card.append(self.inp_lbl)
        self.theme_widgets_fg_label.append(self.inp_lbl)

        self.inp_box = tk.Frame(self.tab_local, bg=self.card_bg)
        self.inp_box.pack(fill=tk.X, pady=(0, 8))
        self.theme_widgets_card.append(self.inp_box)

        self.input_entry = tk.Entry(self.inp_box, font=("Segoe UI", 9), bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.theme_widgets_entry.append(self.input_entry)

        self.browse_file_btn = tk.Button(self.inp_box, text="File...", command=self._browse_file, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, cursor="hand2")
        self.browse_file_btn.pack(side=tk.LEFT, padx=2)
        self.theme_widgets_btn_standard.append(self.browse_file_btn)

        self.browse_dir_btn = tk.Button(self.inp_box, text="Folder...", command=self._browse_dir, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, cursor="hand2")
        self.browse_dir_btn.pack(side=tk.LEFT)
        self.theme_widgets_btn_standard.append(self.browse_dir_btn)

        # Output Path
        self.out_lbl = tk.Label(self.tab_local, text="Target Output Directory:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold"))
        self.out_lbl.pack(anchor="w", pady=(4, 2))
        self.theme_widgets_card.append(self.out_lbl)
        self.theme_widgets_fg_label.append(self.out_lbl)

        self.out_box = tk.Frame(self.tab_local, bg=self.card_bg)
        self.out_box.pack(fill=tk.X, pady=(0, 14))
        self.theme_widgets_card.append(self.out_box)

        self.output_entry = tk.Entry(self.out_box, font=("Segoe UI", 9), bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.theme_widgets_entry.append(self.output_entry)

        self.browse_out_btn = tk.Button(self.out_box, text="Browse...", command=self._browse_output, bg=self.btn_bg, fg=self.btn_fg, relief=tk.FLAT, cursor="hand2")
        self.browse_out_btn.pack(side=tk.LEFT)
        self.theme_widgets_btn_standard.append(self.browse_out_btn)

        # Start Extraction Button
        self.local_extract_btn = tk.Button(
            self.tab_local,
            text="Extract & DeArmour Local Drivers",
            command=self._start_local_extraction,
            bg=self.btn_accent_bg,
            fg=self.btn_accent_fg,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=7,
            cursor="hand2",
        )
        self.local_extract_btn.pack(anchor="w")
        self.theme_widgets_btn_accent.append(self.local_extract_btn)

    def _build_about_tab(self):
        container = tk.Frame(self.tab_about, bg=self.card_bg)
        container.pack(fill=tk.BOTH, expand=True)
        self.theme_widgets_card.append(container)

        # Hero Banner
        hero = tk.Frame(container, bg=self.card_secondary, padx=16, pady=10, relief=tk.FLAT)
        hero.pack(fill=tk.X, pady=(0, 10))
        self.theme_widgets_card_sec.append(hero)

        hero_title = tk.Label(
            hero,
            text=f"DeArmour v{__version__}  |  Bare-Metal Driver Stripper & Cloud Downloader",
            font=("Segoe UI", 12, "bold"),
            bg=self.card_secondary,
            fg=self.accent_color,
        )
        hero_title.pack(anchor="w")
        self.theme_widgets_card_sec.append(hero_title)
        self.theme_widgets_accent_label.append(hero_title)

        hero_sub = tk.Label(
            hero,
            text="Strip bloated ASUS installer wrappers into pure, bare-metal INF/SYS/CAT driver repositories.\n"
                 "Zero telemetry, zero background services, and automated 1-click batch deployment.",
            font=("Segoe UI", 9),
            bg=self.card_secondary,
            fg=self.fg_color,
            justify=tk.LEFT,
        )
        hero_sub.pack(anchor="w", pady=(4, 0))
        self.theme_widgets_card_sec.append(hero_sub)
        self.theme_widgets_fg_label.append(hero_sub)

        # 2 Columns Container
        cols = tk.Frame(container, bg=self.card_bg)
        cols.pack(fill=tk.BOTH, expand=True)
        self.theme_widgets_card.append(cols)

        # Column 1: GitHub & Community
        col1 = tk.Frame(cols, bg=self.card_secondary, padx=14, pady=12)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        self.theme_widgets_card_sec.append(col1)

        c1_title = tk.Label(
            col1,
            text="GitHub & Open Source",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_secondary,
            fg=self.accent_color,
        )
        c1_title.pack(anchor="w", pady=(0, 4))
        self.theme_widgets_card_sec.append(c1_title)
        self.theme_widgets_accent_label.append(c1_title)

        c1_info = tk.Label(
            col1,
            text="Creator: Mustafa Korkunç (@mustafakorkunc)\n"
                 "License: MIT Open Source License\n"
                 "Repository: mustafakorkunc/asus-dearmour",
            font=("Segoe UI", 8),
            bg=self.card_secondary,
            fg=self.fg_color,
            justify=tk.LEFT,
        )
        c1_info.pack(anchor="w", pady=(0, 8))
        self.theme_widgets_card_sec.append(c1_info)
        self.theme_widgets_fg_label.append(c1_info)

        btn_gh = tk.Button(
            col1,
            text="🌐 Open GitHub Repository",
            command=lambda: self._open_url("https://github.com/mustafakorkunc/asus-dearmour"),
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            pady=3,
            cursor="hand2",
        )
        btn_gh.pack(fill=tk.X, pady=2)
        self.theme_widgets_btn_standard.append(btn_gh)

        btn_star = tk.Button(
            col1,
            text="⭐ Star on GitHub",
            command=lambda: self._open_url("https://github.com/mustafakorkunc/asus-dearmour"),
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            pady=3,
            cursor="hand2",
        )
        btn_star.pack(fill=tk.X, pady=2)
        self.theme_widgets_btn_standard.append(btn_star)

        btn_issues = tk.Button(
            col1,
            text="🐛 Report Bug / Verify Model",
            command=lambda: self._open_url("https://github.com/mustafakorkunc/asus-dearmour/issues"),
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            pady=3,
            cursor="hand2",
        )
        btn_issues.pack(fill=tk.X, pady=2)
        self.theme_widgets_btn_standard.append(btn_issues)

        btn_rel = tk.Button(
            col1,
            text="📦 Releases & Standalone Executable",
            command=lambda: self._open_url("https://github.com/mustafakorkunc/asus-dearmour/releases"),
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            pady=2,
            cursor="hand2",
        )
        btn_rel.pack(fill=tk.X, pady=2)
        self.theme_widgets_btn_standard.append(btn_rel)

        # Column 2: Architecture & Attribution & Hacker Mode Quick Switch
        col2 = tk.Frame(cols, bg=self.card_secondary, padx=14, pady=12)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self.theme_widgets_card_sec.append(col2)

        c2_title = tk.Label(
            col2,
            text="Special Thanks & Attribution",
            font=("Segoe UI", 10, "bold"),
            bg=self.card_secondary,
            fg=self.accent_color,
        )
        c2_title.pack(anchor="w", pady=(0, 4))
        self.theme_widgets_card_sec.append(c2_title)
        self.theme_widgets_accent_label.append(c2_title)

        c2_info = tk.Label(
            col2,
            text="• Seerge & G-Helper (github.com/seerge/g-helper):\n"
                 "  Architectural discovery of official ASUS REST API\n"
                 "• Google Jules: Automated test coverage & code health\n"
                 "• Antigravity AI: Pair programming & engine architecture",
            font=("Segoe UI", 8),
            bg=self.card_secondary,
            fg=self.fg_color,
            justify=tk.LEFT,
        )
        c2_info.pack(anchor="w", pady=(0, 6))
        self.theme_widgets_card_sec.append(c2_info)
        self.theme_widgets_fg_label.append(c2_info)

        btn_ghp = tk.Button(
            col2,
            text="⚡ Visit G-Helper Project",
            command=lambda: self._open_url("https://github.com/seerge/g-helper"),
            bg=self.btn_bg,
            fg=self.btn_fg,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            pady=3,
            cursor="hand2",
        )
        btn_ghp.pack(fill=tk.X, pady=2)
        self.theme_widgets_btn_standard.append(btn_ghp)

        # Hacker mode quick toggle button
        hack_frame = tk.Frame(col2, bg=self.card_secondary, pady=4)
        hack_frame.pack(fill=tk.X, pady=(6, 0))
        self.theme_widgets_card_sec.append(hack_frame)

        self.hacker_quick_btn = tk.Button(
            hack_frame,
            text="⚡ Activate Hacker Mode (Matrix)",
            command=lambda: self._select_theme_by_name("Hacker Mode (Matrix)"),
            bg="#162818",
            fg="#00ff66",
            font=("Segoe UI", 8, "bold"),
            relief=tk.FLAT,
            pady=4,
            cursor="hand2",
        )
        self.hacker_quick_btn.pack(fill=tk.X)

    def _switch_to_about(self):
        self.notebook.select(self.tab_about)

    def _on_theme_selected(self, event=None):
        theme_name = self.theme_combo.get()
        self._apply_theme(theme_name)

    def _select_theme_by_name(self, theme_name: str):
        if theme_name in THEMES:
            idx = list(THEMES.keys()).index(theme_name)
            self.theme_combo.current(idx)
            self._apply_theme(theme_name)

    def _apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            return
        self.current_theme = theme_name
        t = THEMES[theme_name]

        self.bg_color = t["bg_color"]
        self.card_bg = t["card_bg"]
        self.card_secondary = t["card_secondary"]
        self.fg_color = t["fg_color"]
        self.accent_color = t["accent_color"]
        self.btn_bg = t["btn_bg"]
        self.btn_hover = t["btn_hover"]
        self.btn_fg = t["btn_fg"]
        self.btn_accent_bg = t["btn_accent_bg"]
        self.btn_accent_fg = t["btn_accent_fg"]
        self.success_color = t["success_color"]
        self.warning_color = t["warning_color"]
        self.text_bg = t["text_bg"]
        self.entry_bg = t["entry_bg"]
        self.muted_fg = t["muted_fg"]
        self.log_fg = t["log_fg"]

        self.root.configure(bg=self.bg_color)

        # Update ttk Styles
        style = ttk.Style()
        style.configure("TNotebook", background=self.bg_color)
        style.configure("TNotebook.Tab", background=self.btn_bg, foreground=self.fg_color)
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.card_bg)],
            foreground=[("selected", self.accent_color)],
        )

        style.configure(
            "Treeview",
            background=self.text_bg,
            foreground=self.fg_color,
            fieldbackground=self.text_bg,
        )
        style.configure(
            "Treeview.Heading",
            background=self.btn_bg,
            foreground=self.accent_color,
        )
        style.map("Treeview", background=[("selected", t["tree_select"])])

        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.card_bg,
            background=self.accent_color,
        )

        # Batch update standard widgets
        for w in self.theme_widgets_bg:
            try:
                w.config(bg=self.bg_color)
            except Exception:
                pass

        for w in self.theme_widgets_card:
            try:
                w.config(bg=self.card_bg)
            except Exception:
                pass

        for w in self.theme_widgets_card_sec:
            try:
                w.config(bg=self.card_secondary)
            except Exception:
                pass

        for w in self.theme_widgets_fg_label:
            try:
                w.config(fg=self.fg_color)
            except Exception:
                pass

        for w in self.theme_widgets_muted_label:
            try:
                w.config(fg=self.muted_fg)
            except Exception:
                pass

        for w in self.theme_widgets_accent_label:
            try:
                w.config(fg=self.accent_color)
            except Exception:
                pass

        for w in self.theme_widgets_btn_standard:
            try:
                w.config(bg=self.btn_bg, fg=self.btn_fg)
            except Exception:
                pass

        for w in self.theme_widgets_btn_accent:
            try:
                w.config(bg=self.btn_accent_bg, fg=self.btn_accent_fg)
            except Exception:
                pass

        for w in self.theme_widgets_entry:
            try:
                w.config(bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color)
            except Exception:
                pass

        if hasattr(self, "log_text"):
            self.log_text.config(bg=self.text_bg, fg=self.log_fg)

        if hasattr(self, "sys_info_lbl"):
            is_asus = self.detected_system.get("is_asus", False)
            self.sys_info_lbl.config(fg=self.success_color if is_asus else self.warning_color)

        if theme_name == "Hacker Mode (Matrix)":
            self._log("[SYSTEM] HACKER MODE INITIALIZED // ACCESS GRANTED // MATRIX THEME ACTIVE")
        else:
            self._log(f"[*] Theme applied: {theme_name}")

    @staticmethod
    def _open_url(url: str):
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            pass

    def _apply_detected_system(self):
        info = self.detected_system
        model = info.get("model", "")
        self.model_entry.delete(0, tk.END)
        if model:
            self.model_entry.insert(0, model)

        full_name = info.get("full_name", "")
        os_name = info.get("os_name", "Windows 11 64-bit")

        if "10" in os_name:
            self.os_combo.current(1)
        else:
            self.os_combo.current(0)

        if model:
            badge = f"Hardware Detected: {full_name} ({model})  |  {os_name}"
            self.sys_info_lbl.config(text=badge, fg=self.success_color)
            self._log(f"[+] {badge}")
        else:
            badge = f"Hardware: Not auto-detected as ASUS | {os_name} (Please enter model code manually)"
            self.sys_info_lbl.config(text=badge, fg=self.warning_color)
            self._log(f"[!] {badge}")

        self._log(f"[*] Initialized DeArmour. Default download folder: {self.downloader.download_dir}")

    def _browse_file(self):
        f = filedialog.askopenfilename(filetypes=[("ASUS Installer", "*.exe"), ("All Files", "*.*")])
        if f:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, f)
            if not self.output_entry.get():
                self.output_entry.insert(0, str(Path(f).parent / "Extracted_Drivers"))

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, d)
            if not self.output_entry.get():
                self.output_entry.insert(0, str(Path(d) / "Extracted_Drivers"))

    def _browse_output(self):
        d = filedialog.askdirectory()
        if d:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, d)

    def _log(self, text: str):
        if threading.current_thread() is threading.main_thread():
            self.log_text.insert(tk.END, text + "\n")
            self.log_text.see(tk.END)
        else:
            self.root.after(0, self._log, text)

    def _set_status(self, text: str):
        if threading.current_thread() is threading.main_thread():
            self.status_lbl.config(text=text)
        else:
            self.root.after(0, self._set_status, text)

    def _fetch_drivers(self):
        model = self.model_entry.get().strip().upper()
        if not model:
            messagebox.showerror("Error", "Please enter a valid ASUS model name (e.g. FA506NC, GA402RJ).")
            return

        is_win11 = "11" in self.os_combo.get()
        osid = 52 if is_win11 else 45

        self.fetch_btn.config(state=tk.DISABLED)
        self.prog.config(mode="indeterminate")
        self.prog.start(10)
        self._set_status(f"Querying ASUS Support API for model {model}...")
        self._log(f"[*] Querying ASUS Support REST API: model={model}, osid={osid}...")

        threading.Thread(target=self._worker_fetch_drivers, args=(model, osid), daemon=True).start()

    def _worker_fetch_drivers(self, model: str, osid: int):
        try:
            packages = self.downloader.fetch_driver_list(model, osid)
            self.fetched_packages = packages
            self.root.after(0, self._render_fetched_packages)
        except Exception as e:
            self.root.after(0, lambda err=str(e): self._log(f"[!] Error fetching drivers: {err}"))
            self.root.after(0, lambda err=str(e): messagebox.showerror("Fetch Failed", f"Could not retrieve drivers from ASUS:\n{err}"))
        finally:
            self.root.after(0, lambda: self.fetch_btn.config(state=tk.NORMAL))
            self.root.after(0, self.prog.stop)
            self.root.after(0, lambda: self.prog.config(mode="determinate", value=0))

    def _render_fetched_packages(self):
        # Clear existing items
        for item in self.driver_tree.get_children():
            self.driver_tree.delete(item)
        self.package_map.clear()

        if not self.fetched_packages:
            self._set_status("No driver packages found for this model.")
            self._log("[!] ASUS API returned 0 packages for the specified model/OS combination.")
            messagebox.showwarning("No Drivers", "No packages were returned by the ASUS Support API for this model.")
            return

        for pkg in self.fetched_packages:
            item_id = self.driver_tree.insert(
                "",
                tk.END,
                values=(pkg.category, pkg.title, pkg.version, pkg.release_date, pkg.file_size or "N/A"),
            )
            self.package_map[item_id] = pkg

        count = len(self.fetched_packages)
        self._set_status(f"Successfully retrieved {count} official driver package(s) from ASUS.")
        self._log(f"[+] Populated {count} official driver packages.")

        # By default, select essential drivers
        self._select_essential_drivers()

    def _on_tree_select(self, event=None):
        selected = self.driver_tree.selection()
        count = len(selected)
        self.sel_count_lbl.config(text=f"{count} driver(s) selected")
        has_sel = count > 0
        self.download_btn.config(state=tk.NORMAL if has_sel else tk.DISABLED)
        self.pipeline_btn.config(state=tk.NORMAL if has_sel else tk.DISABLED)

    def _select_all_drivers(self):
        self.driver_tree.selection_set(self.driver_tree.get_children())
        self._on_tree_select()

    def _clear_selection(self):
        self.driver_tree.selection_set([])
        self._on_tree_select()

    def _select_essential_drivers(self):
        essentials = {"chipset", "network", "networking", "wireless", "audio", "bluetooth", "pointing device"}
        to_select = []
        for item_id, pkg in self.package_map.items():
            if any(e in pkg.category.lower() or e in pkg.title.lower() for e in essentials):
                to_select.append(item_id)
        if to_select:
            self.driver_tree.selection_set(to_select)
        else:
            self._select_all_drivers()
        self._on_tree_select()

    def _start_download_selected(self):
        selected_ids = self.driver_tree.selection()
        if not selected_ids:
            return
        packages = [self.package_map[iid] for iid in selected_ids if iid in self.package_map]

        self._set_busy(True)
        threading.Thread(target=self._worker_download_only, args=(packages,), daemon=True).start()

    def _start_cloud_pipeline(self):
        selected_ids = self.driver_tree.selection()
        if not selected_ids:
            return
        packages = [self.package_map[iid] for iid in selected_ids if iid in self.package_map]

        out_dir = Path.home() / "Desktop" / "Extracted_Drivers"
        self._set_busy(True)
        threading.Thread(target=self._worker_cloud_pipeline, args=(packages, out_dir), daemon=True).start()

    def _worker_download_only(self, packages: List[AsusDriverPackage]):
        try:
            total = len(packages)
            self._log(f"\n[*] Starting download of {total} package(s)...")
            downloaded = []

            for idx, pkg in enumerate(packages, start=1):
                self.root.after(0, lambda i=idx, t=total, p=pkg: self._set_status(f"Downloading [{i}/{t}]: {p.title}"))
                self.root.after(0, lambda i=idx, t=total: self.prog.config(value=(i / t) * 100))

                self._log(f"--> [{idx}/{total}] Downloading {pkg.title} ({pkg.file_size or '...'})")
                dest = self.downloader.download_package(pkg)
                downloaded.append(dest)
                self._log(f"    Saved: {dest.name}")

            self._log(f"\n[+] Finished downloading {len(downloaded)} package(s) to {self.downloader.download_dir}")
            self.root.after(0, lambda: self._set_status("All selected downloads completed successfully."))
            self.root.after(0, lambda cnt=len(downloaded): messagebox.showinfo("Downloads Complete", f"Successfully downloaded {cnt} driver package(s)!"))
        except Exception as e:
            self._log(f"[!] Download failed: {e}")
            self.root.after(0, lambda err=str(e): messagebox.showerror("Download Error", f"An error occurred during download:\n{err}"))
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _worker_cloud_pipeline(self, packages: List[AsusDriverPackage], out_path: Path):
        try:
            total = len(packages)
            self._log(f"\n[*] Starting Cloud DeArmour Pipeline for {total} package(s)...")
            downloaded_paths = []

            # 1. Download
            for idx, pkg in enumerate(packages, start=1):
                self.root.after(0, lambda i=idx, t=total, p=pkg: self._set_status(f"Downloading [{i}/{t}]: {p.title}"))
                self._log(f"--> [{idx}/{total}] Downloading {pkg.title}...")
                dest = self.downloader.download_package(pkg)
                downloaded_paths.append(dest)

            # 2. Extract & Organize
            self.root.after(0, lambda: self._set_status("Carving archives and extracting bare-metal drivers (silent)..."))
            self.root.after(0, lambda: self.prog.config(mode="indeterminate"))
            self.root.after(0, lambda: self.prog.start(10))

            self._log("\n[*] Running DeArmour extraction engine on downloaded packages...")
            # Strictly process ONLY packages downloaded in this current session to avoid reprocessing stale files
            targets = [p for p in downloaded_paths if p.is_file() and p.suffix.lower() == ".exe"]
            if not targets:
                self._log("[!] No valid executable packages available for extraction.")
                self.root.after(0, lambda: messagebox.showwarning("No Targets", "No executable driver packages were downloaded to process."))
                return

            drivers = run_pipeline(targets, out_path)

            self._log("\n" + "=" * 60)
            self._log(f"[+] Success! {len(drivers)} driver package(s) unpacked and categorized into:")
            self._log(f"    {out_path}")
            self._log(f"[+] Deployment scripts: {out_path / 'INSTALL_ALL_DRIVERS.bat'}")

            self.root.after(0, lambda: self._set_status(f"Pipeline complete: {len(drivers)} drivers ready for deployment."))
            self.root.after(
                0,
                lambda cnt=len(drivers): messagebox.showinfo(
                    "DeArmour Complete",
                    f"Successfully downloaded and extracted {cnt} driver package(s)!\n\nOutput folder:\n{out_path}",
                ),
            )
        except Exception as e:
            self._log(f"[!] Pipeline error: {e}")
            self.root.after(0, lambda err=str(e): messagebox.showerror("Pipeline Error", f"An error occurred:\n{err}"))
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _start_local_extraction(self):
        inp = self.input_entry.get().strip()
        out = self.output_entry.get().strip()

        if not inp or not Path(inp).exists():
            messagebox.showerror("Error", "Please select a valid driver installer .exe or directory.")
            return

        if not out:
            out = str(Path(inp).parent / "Extracted_Drivers" if Path(inp).is_file() else Path(inp) / "Extracted_Drivers")
            self.output_entry.insert(0, out)

        self._set_busy(True)
        self.prog.config(mode="indeterminate")
        self.prog.start(10)
        self.log_text.delete(1.0, tk.END)
        self._log(f"[*] Local Extraction Started: {inp}")

        threading.Thread(target=self._worker_local_extraction, args=(Path(inp), Path(out)), daemon=True).start()

    def _worker_local_extraction(self, in_path: Path, out_path: Path):
        try:
            targets = collect_target_files(in_path)
            self._log(f"[*] Found installer target(s): {len(targets)}")

            drivers = run_pipeline(targets, out_path)
            self._log("\n" + "=" * 60)
            self._log(f"[+] Complete! Total driver packages unpacked: {len(drivers)}")
            self._log(f"[+] 1-Click deployment scripts generated: {out_path / 'INSTALL_ALL_DRIVERS.bat'}")
            self.root.after(0, lambda cnt=len(drivers): messagebox.showinfo("Success", f"Successfully extracted and organized {cnt} driver package(s)!"))
        except Exception as e:
            self._log(f"[!] Error: {e}")
            self.root.after(0, lambda err=str(e): messagebox.showerror("Error", f"An error occurred during extraction:\n{err}"))
        finally:
            self.root.after(0, lambda: self._set_busy(False))

    def _set_busy(self, is_busy: bool):
        state = tk.DISABLED if is_busy else tk.NORMAL
        self.fetch_btn.config(state=state)
        self.download_btn.config(state=state)
        self.pipeline_btn.config(state=state)
        self.local_extract_btn.config(state=state)
        if not is_busy:
            self.prog.stop()
            self.prog.config(mode="determinate", value=0)

    def _open_downloads(self):
        d = self.downloader.download_dir
        if d.exists():
            os.startfile(str(d))

    def _open_extracted(self):
        candidate = Path.home() / "Desktop" / "Extracted_Drivers"
        local_out = self.output_entry.get().strip()
        if local_out and Path(local_out).exists():
            os.startfile(local_out)
        elif candidate.exists():
            os.startfile(str(candidate))
        else:
            messagebox.showinfo("Info", "Output folder has not been created yet.")


def launch_gui():
    root = tk.Tk()
    DeArmourGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
