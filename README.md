# ⚔️ DeArmour (ASUS Driver Stripper)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d7.svg)](https://microsoft.com/windows)
[![Release: Standalone EXE](https://img.shields.io/badge/download-Single%20EXE%20%7C%20ZIP-success.svg)](https://github.com/mustafakorkunc/asus-dearmour/releases)

> **Strip bloated ASUS driver installer wrappers into pure, bare-metal INF/SYS/CAT driver repositories with zero telemetry and 1-click batch deployment.**

---

## 🎯 Problem & Motivation

When you download hardware drivers from ASUS (for TUF, ROG, ZenBook, or Vivobook laptops), they come bundled as large `.exe` files wrapped inside **SetupLdr**, **Inno Setup**, or **AsusSetup** installers. 

These installers often:
- ❌ Install background telemetry services (`AsusAppService`, `ASUSOptimization`, `ASUSSystemAnalysis`) that constantly consume CPU & RAM.
- ❌ Fail or hang when attempting silent installations during automated or clean OS deployments.
- ❌ Hide the actual, official WHQL-certified `.inf`, `.sys`, and `.cat` driver files deep inside nested binary overlays.

**DeArmour** solves this by:
1. **Binary Carving:** Scanning PE executables for embedded archives (`7z`, `ZIP`, `CAB`, `RAR`) using byte-level stream carving.
2. **Recursive Unpacking:** Stripping away the wrapper layers until pure device drivers are uncovered.
3. **INF Intelligence:** Parsing Windows Setup Information (`.inf`) files to extract version, provider, dates, device descriptions, and hardware IDs.
4. **Clean Categorization:** Organizing drivers by hardware class (`Network/Ethernet`, `Network/Wireless`, `Bluetooth`, `Audio`, `Display`, `Chipset`, etc.).
5. **Instant Deployment:** Auto-generating native Windows `pnputil` scripts (`INSTALL_ALL_DRIVERS.bat` and `.ps1`) to inject all drivers into Windows in seconds without opening a single installer wizard!

---

## ✨ Features

- ⚡ **Zero Heavy Dependencies:** Uses built-in Windows utilities (`tar.exe`, `expand.exe`, `pnputil`) and Python standard library.
- 🔍 **Universal Stream Carving:** Unpacks nested archives, 7z SFX, and ASUS SetupLdr binary overlays.
- 🏷️ **Smart Categorization:** Automatically groups drivers into `Network_Ethernet`, `Network_Wireless`, `Bluetooth`, `Audio`, `Display_Graphics`, `Chipset_System`, `Input_Touchpad`, etc.
- 📜 **Driver Manifests:** Generates `driver_manifest.json` for every driver with full hardware ID and version details.
- 🛠️ **1-Click Installers:** Auto-generates standalone `install.bat` inside each driver folder, plus a master `INSTALL_ALL_DRIVERS.bat` with automatic Administrator elevation.
- 💻 **Dual Mode:** Powerful CLI for scripting and an intuitive Tkinter GUI for everyday users.

---

## 📂 Output Folder Structure

After running ADE on your ASUS downloads, you get a clean, standardized repository:

```text
📁 Extracted_Drivers/
├── 📄 INSTALL_ALL_DRIVERS.bat       <-- 1-Click Master Installer (Runs pnputil)
├── 📄 INSTALL_ALL_DRIVERS.ps1       <-- PowerShell Equivalent with progress reporting
├── 📄 drivers_catalog.json          <-- Machine-readable JSON summary of all drivers
│
├── 📁 Network_Ethernet/
│   └── 📁 Realtek_rt68cx21x64_v1168.015/
│       ├── 📄 rt68cx21x64.inf
│       ├── 📄 rt68cx21x64.sys
│       ├── 📄 rt68cx21x64.cat
│       ├── 📄 install.bat
│       ├── 📄 uninstall.bat
│       └── 📄 driver_manifest.json
│
├── 📁 Network_Wireless/
│   └── 📁 Realtek_netrtwlane601_v6001.15.163/
│       ├── 📄 netrtwlane601.inf
│       ├── 📄 *.sys / *.cat
│       └── 📄 install.bat
│
└── 📁 Bluetooth/
    └── 📁 Realtek_rtkbtfilter_v18.4038.2509/
        ├── 📄 rtkbtfilter.inf
        ├── 📄 *.sys / *.cat
        └── 📄 install.bat
```

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/mustcoffi/asus-driver-extractor.git
cd asus-driver-extractor
pip install -e .
```

Or run directly without installation:

```bash
python -m asus_driver_extractor [OPTIONS]
```

### 2. CLI Usage

#### Extract a Single ASUS Driver `.exe`:
```bash
asus-unpack "C:\Downloads\LAN_ROG_Realtek_B_V1168.exe" -o "C:\CleanDrivers"
```

#### Batch Extract an Entire Folder of ASUS Drivers:
```bash
asus-unpack "C:\Users\Username\Downloads" -o "C:\Drivers\TUF_A15"
```

#### Recursive Subdirectory Scan:
```bash
asus-unpack "D:\ASUS_Backup" --recursive -o "D:\Clean_Repository"
```

### 3. GUI Mode

Launch the graphical interface:

```bash
ade-gui
```
*(Or simply run `asus-unpack` without arguments)*

---

## 🔮 Upcoming Roadmap: Direct ASUS API Downloader

In the next release, ADE will feature a direct cloud downloader:
- Enter your laptop model (e.g. `FA506NC`, `GA402RJ`, `G513QY`).
- ADE automatically queries the official ASUS Support API, fetches the latest driver catalog for Windows 11/10, downloads the packages, and extracts bare-metal INF files directly!

---

## 🧪 Testing

Run test suite via `pytest`:

```bash
pip install pytest
pytest tests/ -v
```

---

## 📄 License & Credits

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

Crafted by **[Mustafa Korkunç](https://github.com/mustafakorkunc)** in collaboration with **Antigravity AI** pair programming. Performance optimizations and expanded unit test coverage contributed in collaboration with **Google Jules**.

