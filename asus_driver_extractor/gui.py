"""
Graphical User Interface (GUI) for DeArmour.
Lightweight Tkinter GUI with file/folder selection, real-time logging,
and one-click output folder access.
"""

import io
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Safeguard for windowed executable (no console)
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

from asus_driver_extractor import __version__
from asus_driver_extractor.cli import collect_target_files, run_pipeline


class DeArmourGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"DeArmour v{__version__} - ASUS Driver Stripper")
        self.root.geometry("780x570")
        self.root.minsize(700, 500)

        # Theme styling (Modern Dark)
        self.bg_color = "#1e1e2e"
        self.card_bg = "#28283d"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.btn_bg = "#313244"
        self.success_color = "#a6e3a1"

        self.root.configure(bg=self.bg_color)
        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=10)
        header_frame.pack(fill=tk.X, padx=20)

        title_lbl = tk.Label(
            header_frame,
            text="⚔️ DeArmour",
            font=("Segoe UI", 18, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            header_frame,
            text="Strip bloated ASUS installer wrappers into pure, bare-metal INF drivers.",
            font=("Segoe UI", 10),
            bg=self.bg_color,
            fg="#a6adc8",
        )
        subtitle_lbl.pack(anchor="w")

        # Configuration Card
        cfg_frame = tk.Frame(self.root, bg=self.card_bg, padx=15, pady=15, relief=tk.FLAT)
        cfg_frame.pack(fill=tk.X, padx=20, pady=10)

        # Input Path
        tk.Label(cfg_frame, text="Driver Package (.exe) or Folder:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=4)
        self.input_entry = tk.Entry(cfg_frame, font=("Segoe UI", 9), bg="#181825", fg=self.fg_color, insertbackground="white")
        self.input_entry.grid(row=0, column=1, sticky="ew", padx=10, pady=4)
        
        btn_box = tk.Frame(cfg_frame, bg=self.card_bg)
        btn_box.grid(row=0, column=2, sticky="e")
        tk.Button(btn_box, text="File...", command=self._browse_file, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_box, text="Folder...", command=self._browse_dir, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

        # Output Path
        tk.Label(cfg_frame, text="Target Output Directory:", bg=self.card_bg, fg=self.fg_color, font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=4)
        self.output_entry = tk.Entry(cfg_frame, font=("Segoe UI", 9), bg="#181825", fg=self.fg_color, insertbackground="white")
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=4)
        tk.Button(cfg_frame, text="Browse...", command=self._browse_output, bg=self.btn_bg, fg=self.fg_color, relief=tk.FLAT).grid(row=1, column=2, sticky="ew", padx=2, pady=4)

        cfg_frame.columnconfigure(1, weight=1)

        # Action Buttons Frame
        act_frame = tk.Frame(self.root, bg=self.bg_color)
        act_frame.pack(fill=tk.X, padx=20, pady=5)

        self.start_btn = tk.Button(
            act_frame,
            text="⚡ Extract & Organize Drivers",
            command=self._start_extraction,
            bg="#b4befe",
            fg="#11111b",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=6,
        )
        self.start_btn.pack(side=tk.LEFT)

        self.open_out_btn = tk.Button(
            act_frame,
            text="📂 Open Output Folder",
            command=self._open_output,
            bg=self.btn_bg,
            fg=self.fg_color,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            padx=10,
            pady=6,
            state=tk.DISABLED,
        )
        self.open_out_btn.pack(side=tk.LEFT, padx=10)

        # Progress Bar
        self.prog = ttk.Progressbar(self.root, mode="indeterminate")
        self.prog.pack(fill=tk.X, padx=20, pady=5)

        # Log Text Box
        log_frame = tk.Frame(self.root, bg=self.bg_color)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.log_text = tk.Text(
            log_frame,
            bg="#11111b",
            fg="#a6adc8",
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=10,
            pady=10,
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

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

    def _start_extraction(self):
        inp = self.input_entry.get().strip()
        out = self.output_entry.get().strip()

        if not inp or not Path(inp).exists():
            messagebox.showerror("Error", "Please select a valid driver installer .exe or directory.")
            return

        if not out:
            out = str(Path(inp).parent / "Extracted_Drivers" if Path(inp).is_file() else Path(inp) / "Extracted_Drivers")
            self.output_entry.insert(0, out)

        self.start_btn.config(state=tk.DISABLED)
        self.open_out_btn.config(state=tk.DISABLED)
        self.prog.start(10)
        self.log_text.delete(1.0, tk.END)
        self._log(f"[*] Extraction Started: {inp}")

        threading.Thread(target=self._run_worker, args=(Path(inp), Path(out)), daemon=True).start()

    def _run_worker(self, in_path: Path, out_path: Path):
        try:
            targets = collect_target_files(in_path)
            self._log(f"[*] Found installer target(s): {len(targets)}")

            drivers = run_pipeline(targets, out_path)
            self._log("\n" + "=" * 60)
            self._log(f"[✔] Complete! Total driver packages unpacked: {len(drivers)}")
            self._log(f"[✔] 1-Click deployment scripts generated: {out_path / 'INSTALL_ALL_DRIVERS.bat'}")
            self.root.after(0, lambda: self.open_out_btn.config(state=tk.NORMAL))
            messagebox.showinfo("Success", f"Successfully extracted and organized {len(drivers)} driver package(s)!")
        except Exception as e:
            self._log(f"[✖] Error: {e}")
            messagebox.showerror("Error", f"An error occurred during extraction:\n{e}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, self.prog.stop)

    def _open_output(self):
        out = self.output_entry.get().strip()
        if out and Path(out).exists():
            os.startfile(out)


def launch_gui():
    root = tk.Tk()
    app = DeArmourGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
