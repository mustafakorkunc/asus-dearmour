"""
Graphical User Interface (GUI) for DeArmour.
Features ASUS Hardware Auto-Detection, Official ASUS Cloud Driver Downloader,
Pure INF/SYS Extraction Engine, and One-Click Automated Deployment Script Generation.

Special thanks and architectural attribution to:
- Seerge & the G-Helper project (https://github.com/seerge/g-helper)
  for pioneering the reverse engineering and discovery of the official ASUS Support REST API.
"""

import io
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional
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


class DeArmourGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"DeArmour v{__version__} - ASUS Driver Stripper & Cloud Downloader")
        self.root.geometry("880x670")
        self.root.minsize(800, 600)

        # Dark Theme Palette (Catppuccin Mocha Inspired)
        self.bg_color = "#1e1e2e"
        self.card_bg = "#28283d"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.btn_bg = "#313244"
        self.btn_hover = "#45475a"
        self.success_color = "#a6e3a1"
        self.warning_color = "#f9e2af"
        self.text_bg = "#11111b"

        self.root.configure(bg=self.bg_color)

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
        style.map("Treeview", background=[("selected", "#45475a")])

        # Progressbar styling
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.card_bg,
            background=self.accent_color,
            thickness=6,
        )

    def _build_ui(self):
        # 1. Header Frame
        header = tk.Frame(self.root, bg=self.bg_color, pady=10)
        header.pack(fill=tk.X, padx=20)

        title_box = tk.Frame(header, bg=self.bg_color)
        title_box.pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text="DeArmour",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        ).pack(side=tk.LEFT)

        tk.Label(
            title_box,
            text=f"v{__version__}",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg="#a6adc8",
            padx=8,
            pady=4,
        ).pack(side=tk.LEFT)

        tk.Label(
            header,
            text="Extract pure, bare-metal INF/SYS drivers from ASUS packages & download directly from ASUS servers.",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg="#a6adc8",
        ).pack(anchor="w", pady=(2, 0))

        # 2. Main Tabs (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=False, padx=20, pady=(5, 5))

        self.tab_cloud = tk.Frame(self.notebook, bg=self.card_bg, padx=15, pady=12)
        self.tab_local = tk.Frame(self.notebook, bg=self.card_bg, padx=15, pady=15)

        self.notebook.add(self.tab_cloud, text="  ASUS Cloud Downloader  ")
        self.notebook.add(self.tab_local, text="  Local File Extractor  ")

        self._build_cloud_tab()
        self._build_local_tab()

        # 3. Status & Progress Indicator
        status_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=6)
        status_frame.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg="#a6adc8",
            anchor="w",
        )
        self.status_lbl.pack(fill=tk.X)

        self.prog = ttk.Progressbar(self.root, style="Horizontal.TProgressbar", mode="determinate")
        self.prog.pack(fill=tk.X, padx=20, pady=(2, 6))

        # 4. Shared Console Log Frame
        log_frame = tk.Frame(self.root, bg=self.bg_color, padx=20)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.log_text = tk.Text(
            log_frame,
            bg=self.text_bg,
            fg="#a6adc8",
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=10,
            pady=8,
            height=7,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # 5. Bottom Action Bar & Footer
        footer_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=8)
        footer_frame.pack(fill=tk.X)

        btn_box = tk.Frame(footer_frame, bg=self.bg_color)
        btn_box.pack(side=tk.LEFT)

        self.open_downloads_btn = tk.Button(
            btn_box,
            text="Open Downloads Folder",
            command=self._open_downloads,
            bg=self.btn_bg,
            fg=self.fg_color,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=4,
        )
        self.open_downloads_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.open_extracted_btn = tk.Button(
            btn_box,
            text="Open Extracted Drivers Folder",
            command=self._open_extracted,
            bg=self.btn_bg,
            fg=self.fg_color,
            font=("Segoe UI", 8),
            relief=tk.FLAT,
            padx=10,
            pady=4,
        )
        self.open_extracted_btn.pack(side=tk.LEFT)

        tk.Label(
            footer_frame,
            text="DeArmour by Mustafa Korkunç  |  API discovery inspired by G-Helper (seerge/g-helper)",
            font=("Segoe UI", 8),
            bg=self.bg_color,
            fg="#6c7086",
        ).pack(side=tk.RIGHT)

    def _build_cloud_tab(self):
        # System Hardware Info Card
        sys_card = tk.Frame(self.tab_cloud, bg="#1e1e2e", padx=12, pady=8, relief=tk.FLAT)
        sys_card.pack(fill=tk.X, pady=(0, 10))

        self.sys_info_lbl = tk.Label(
            sys_card,
            text="Detecting system hardware...",
            font=("Segoe UI", 9, "bold"),
            bg="#1e1e2e",
            fg=self.success_color,
            anchor="w",
        )
        self.sys_info_lbl.pack(side=tk.LEFT)

        # Query Controls
        query_bar = tk.Frame(self.tab_cloud, bg=self.card_bg)
        query_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(query_bar, text="Model:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        self.model_entry = tk.Entry(query_bar, font=("Segoe UI", 9), bg="#181825", fg=self.fg_color, width=14, insertbackground="white")
        self.model_entry.pack(side=tk.LEFT, padx=6)

        tk.Label(query_bar, text="OS:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(6, 0))
        self.os_combo = ttk.Combobox(
            query_bar,
            values=["Windows 11 64-bit", "Windows 10 64-bit"],
            width=18,
            state="readonly",
        )
        self.os_combo.current(0)
        self.os_combo.pack(side=tk.LEFT, padx=6)

        self.fetch_btn = tk.Button(
            query_bar,
            text="Fetch Drivers from ASUS",
            command=self._fetch_drivers,
            bg=self.accent_color,
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=12,
            pady=3,
        )
        self.fetch_btn.pack(side=tk.LEFT, padx=8)

        # Driver Selection Treeview
        tree_container = tk.Frame(self.tab_cloud, bg=self.card_bg)
        tree_container.pack(fill=tk.BOTH, expand=True, pady=4)

        columns = ("Category", "Title", "Version", "Date", "Size")
        self.driver_tree = ttk.Treeview(
            tree_container,
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
        tree_scroll = tk.Scrollbar(tree_container, command=self.driver_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.driver_tree.config(yscrollcommand=tree_scroll.set)

        self.driver_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Quick Selection Bar & Count
        sel_bar = tk.Frame(self.tab_cloud, bg=self.card_bg, pady=4)
        sel_bar.pack(fill=tk.X)

        tk.Button(sel_bar, text="Select All", command=self._select_all_drivers, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT, font=("Segoe UI", 8), padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(sel_bar, text="Clear", command=self._clear_selection, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT, font=("Segoe UI", 8), padx=8).pack(side=tk.LEFT, padx=2)
        tk.Button(sel_bar, text="Select Essentials", command=self._select_essential_drivers, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT, font=("Segoe UI", 8), padx=8).pack(side=tk.LEFT, padx=2)

        self.sel_count_lbl = tk.Label(
            sel_bar,
            text="0 drivers selected",
            bg=self.card_bg,
            fg="#a6adc8",
            font=("Segoe UI", 8),
        )
        self.sel_count_lbl.pack(side=tk.RIGHT)

        # Action Buttons (Download & Extract)
        act_box = tk.Frame(self.tab_cloud, bg=self.card_bg, pady=6)
        act_box.pack(fill=tk.X)

        self.download_btn = tk.Button(
            act_box,
            text="Download Selected",
            command=self._start_download_selected,
            bg=self.btn_bg,
            fg=self.fg_color,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=5,
            state=tk.DISABLED,
        )
        self.download_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.pipeline_btn = tk.Button(
            act_box,
            text="Download & DeArmour (Full Pipeline)",
            command=self._start_cloud_pipeline,
            bg="#b4befe",
            fg="#11111b",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=14,
            pady=5,
            state=tk.DISABLED,
        )
        self.pipeline_btn.pack(side=tk.LEFT)

    def _build_local_tab(self):
        tk.Label(
            self.tab_local,
            text="Select an ASUS driver installer .exe or folder containing multiple packages to strip into bare-metal INF/SYS drivers.",
            bg=self.card_bg,
            fg="#a6adc8",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 12))

        # Input Path
        tk.Label(self.tab_local, text="Driver Package (.exe) or Directory:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(2, 2))
        inp_box = tk.Frame(self.tab_local, bg=self.card_bg)
        inp_box.pack(fill=tk.X, pady=(0, 8))

        self.input_entry = tk.Entry(inp_box, font=("Segoe UI", 9), bg="#181825", fg=self.fg_color, insertbackground="white")
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        tk.Button(inp_box, text="File...", command=self._browse_file, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(inp_box, text="Folder...", command=self._browse_dir, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).pack(side=tk.LEFT)

        # Output Path
        tk.Label(self.tab_local, text="Target Output Directory:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(4, 2))
        out_box = tk.Frame(self.tab_local, bg=self.card_bg)
        out_box.pack(fill=tk.X, pady=(0, 14))

        self.output_entry = tk.Entry(out_box, font=("Segoe UI", 9), bg="#181825", fg=self.fg_color, insertbackground="white")
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        tk.Button(out_box, text="Browse...", command=self._browse_output, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).pack(side=tk.LEFT)

        # Start Extraction Button
        self.local_extract_btn = tk.Button(
            self.tab_local,
            text="Extract & DeArmour Local Drivers",
            command=self._start_local_extraction,
            bg="#b4befe",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=7,
        )
        self.local_extract_btn.pack(anchor="w")

    def _apply_detected_system(self):
        info = self.detected_system
        model = info.get("model", "FA506NC")
        self.model_entry.delete(0, tk.END)
        self.model_entry.insert(0, model)

        is_asus = info.get("is_asus", True)
        full_name = info.get("full_name", "ASUS Device")
        os_name = info.get("os_name", "Windows 11 64-bit")

        if "10" in os_name:
            self.os_combo.current(1)
        else:
            self.os_combo.current(0)

        badge = f"Hardware Detected: {full_name} ({model})  |  {os_name}"
        self.sys_info_lbl.config(text=badge)
        self._log(f"[+] {badge}")
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
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _set_status(self, text: str):
        self.status_lbl.config(text=text)

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
            self.root.after(0, lambda: self._log(f"[!] Error fetching drivers: {e}"))
            self.root.after(0, lambda: messagebox.showerror("Fetch Failed", f"Could not retrieve drivers from ASUS:\n{e}"))
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
            messagebox.showinfo("Downloads Complete", f"Successfully downloaded {len(downloaded)} driver package(s)!")
        except Exception as e:
            self._log(f"[!] Download failed: {e}")
            messagebox.showerror("Download Error", f"An error occurred during download:\n{e}")
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
            targets = collect_target_files(self.downloader.download_dir)
            drivers = run_pipeline(targets, out_path)

            self._log("\n" + "=" * 60)
            self._log(f"[+] Success! {len(drivers)} driver package(s) unpacked and categorized into:")
            self._log(f"    {out_path}")
            self._log(f"[+] Deployment scripts: {out_path / 'INSTALL_ALL_DRIVERS.bat'}")

            self.root.after(0, lambda: self._set_status(f"Pipeline complete: {len(drivers)} drivers ready for deployment."))
            messagebox.showinfo(
                "DeArmour Complete",
                f"Successfully downloaded and extracted {len(drivers)} driver package(s)!\n\nOutput folder:\n{out_path}",
            )
        except Exception as e:
            self._log(f"[!] Pipeline error: {e}")
            messagebox.showerror("Pipeline Error", f"An error occurred:\n{e}")
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
            messagebox.showinfo("Success", f"Successfully extracted and organized {len(drivers)} driver package(s)!")
        except Exception as e:
            self._log(f"[!] Error: {e}")
            messagebox.showerror("Error", f"An error occurred during extraction:\n{e}")
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
    app = DeArmourGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
