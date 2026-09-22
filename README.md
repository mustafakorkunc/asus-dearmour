# DeArmour

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078d7.svg)](https://microsoft.com/windows)
[![Release: Standalone EXE](https://img.shields.io/badge/release-v1.1.0-success.svg)](https://github.com/mustafakorkunc/asus-dearmour/releases)

DeArmour is a lightweight, high-performance Windows driver utility designed to strip bloated ASUS installer wrappers (SetupLdr, Inno Setup, AsusSetup) into pure, bare-metal INF/SYS/CAT driver repositories. It features automatic hardware detection, direct cloud driver downloading from official ASUS servers, and 1-click batch deployment scripts with zero background telemetry services.

<p align="center">
  <img src="assets/dearmour-ui.png" alt="DeArmour v1.1.0 User Interface" width="760" />
</p>

---

## Key Capabilities

- **ASUS Cloud Downloader & Hardware Auto-Detection**  
  Instantly identifies your ASUS laptop model (e.g. `FA506NC`, `GA402RJ`, `G513QY`) and Windows version via low-overhead system registry queries. Fetches official driver packages directly from the ASUS Support REST API with selective package downloading.

- **Universal Binary Stream Carving**  
  Scans PE installer executables at the byte level to locate and carve embedded archive streams (`7z`, `ZIP`, `CAB`, `RAR`), completely bypassing proprietary wrapper layers and unpacker stubs.

- **Pure Driver Stripping (Zero Telemetry)**  
  Isolates and extracts only signed, bare-metal `.inf`, `.sys`, and `.cat` driver components while permanently discarding telemetry daemons, bloated setup wizards, and background services (`AsusAppService`, `ASUSOptimization`).

- **Silent Extraction Engine**  
  All background extraction processes run quietly with native Windows `CREATE_NO_WINDOW` flags, eliminating annoying command-prompt window flashes during unpacking.

- **Automated 1-Click Deployment**  
  Generates native Windows `pnputil` scripts (`INSTALL_ALL_DRIVERS.bat` and `INSTALL_ALL_DRIVERS.ps1`) alongside a machine-readable `drivers_catalog.json` for automated, zero-wizard driver installation.

- **Dual-Mode Workflow**  
  Includes both a modern dark-mode graphical user interface (GUI) and a full-featured command-line interface (CLI) for sysadmins and power users.

---

## Output Architecture

When DeArmour processes your driver packages, it creates a clean, standardized hardware repository:

```text
Extracted_Drivers/
├── INSTALL_ALL_DRIVERS.bat       # 1-Click Master Installer (Automated pnputil)
├── INSTALL_ALL_DRIVERS.ps1       # PowerShell deployment script with progress
├── drivers_catalog.json          # Machine-readable inventory of all drivers
│
├── Network_Wireless/
│   └── Realtek_netrtwlane601_v6001.15.163/
│       ├── netrtwlane601.inf
│       ├── netrtwlane601.sys
│       ├── netrtwlane601.cat
│       ├── install.bat
│       └── driver_manifest.json
│
├── Network_Ethernet/
│   └── Realtek_rt68cx21x64_v1168.015/
│       ├── rt68cx21x64.inf
│       ├── *.sys / *.cat
│       └── install.bat
│
├── Chipset/
│   └── AMD_amdfendr_v1.2.0.124/
│       └── ...
│
└── Bluetooth/
    └── Realtek_rtkbtfilter_v18.4038.2509/
        └── ...
```

---

## Quick Start

### Graphical User Interface (GUI)

The simplest way to use DeArmour is via the standalone Windows executable:

1. Download **`DeArmour-v1.1.0-win64.exe`** from [Releases](https://github.com/mustafakorkunc/asus-dearmour/releases).
2. Run the executable (no Python installation or dependencies required).
3. Under the **ASUS Cloud Downloader** tab:
   - Verify your auto-detected model.
   - Click **Fetch Drivers from ASUS**.
   - Select your desired drivers and click **Download & DeArmour (Full Pipeline)**.

### Command Line Interface (CLI)

#### 1. Hardware Detection
```bash
dearmour --detect
```
```text
Hardware Detection:
  Manufacturer:  ASUSTeK COMPUTER INC.
  Product Name:  ASUS TUF Gaming A15 FA506NC
  Model Code:    FA506NC
  Operating Sys: Windows 11 64-bit (ASUS OSID: 52)
```

#### 2. Query Driver Catalog
```bash
# Query drivers for the auto-detected system
dearmour --fetch

# Query drivers for any specific model
dearmour --fetch GA402RJ
```

#### 3. Extract Local Driver Packages
```bash
# Extract a single driver installer
dearmour "C:\Downloads\WLAN_Realtek_FA506NC.exe" -o "C:\CleanDrivers"

# Batch extract all drivers in a folder recursively
dearmour "C:\Downloads\AsusDrivers" -o "C:\CleanDrivers" -r
```

---

## Installation (Source Code)

For developers and Python environments (Python 3.8 - 3.14):

```bash
git clone https://github.com/mustafakorkunc/asus-dearmour.git
cd asus-dearmour
pip install -e .
```

To run the unit test suite:

```bash
pip install pytest
pytest tests/ -v
```

---

## Special Thanks & Acknowledgements

- **[Seerge](https://github.com/seerge) and the [G-Helper](https://github.com/seerge/g-helper) Project**  
  Special thanks and highest respect to Seerge and the G-Helper community for pioneering the reverse engineering and discovery of the official ASUS Support REST API endpoints. G-Helper set the gold standard for lightweight, bloat-free ASUS laptop utilities and served as the direct inspiration for DeArmour's cloud driver synchronization capabilities.

- **[Google Jules](https://jules.google.com)**  
  Contributed extensive unit testing suites (expanding test coverage to 20+ tests) and C-level tuple optimizations for string parsing routines.

- **Antigravity AI**  
  Pair programming, core engine architecture, and GUI implementation.

---

## Author & License

Created by **[Mustafa Korkunç](https://github.com/mustafakorkunc)**.

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for complete terms.
