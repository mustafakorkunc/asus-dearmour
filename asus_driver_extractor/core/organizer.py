"""
Driver Organizer & Package Bundler.
Discovers extracted INF drivers, categorizes them, bundles their payload files,
and writes per-driver manifests and installation scripts.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Set
from asus_driver_extractor.core.inf_parser import InfParser, DriverMetadata


class DriverOrganizer:
    """Organizes extracted driver components into categorized, deployable bundles."""

    # Unnecessary bloat files and PE sections to filter out from driver payloads
    EXCLUDED_NAMES = {
        "install.exe", "setup.exe", "setuphdr.exe", "setupldr.exe",
        "installstep.txt", "asusetup.exe", "asusoptimization.exe",
        "asussoftwaremanager.exe", "issetup.dll", "install.tmp",
        ".text", ".rsrc", ".data", ".rdata", ".pdata", ".bss",
        ".didata", ".edata", ".idata", ".itext", ".tls", ".reloc",
        "certificate", "[0]"
    }

    def __init__(self, output_root: Path):
        self.output_root = Path(output_root).resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)

    def organize_extracted_pool(self, staging_dir: Path) -> List[DriverMetadata]:
        """
        Scans staging_dir for INF files, categorizes each driver, copies
        all payload dependencies, and writes per-driver installation scripts.
        """
        staging_dir = Path(staging_dir).resolve()
        inf_files = list(staging_dir.rglob("*.inf"))
        organized_drivers: List[DriverMetadata] = []
        processed_folders: Set[Path] = set()
        folder_to_dest: Dict[Path, Path] = {}

        for inf_path in inf_files:
            try:
                meta = InfParser.parse_inf(inf_path)
            except Exception:
                # Do not let one malformed INF abort the entire extraction pool
                continue

            driver_dir = inf_path.parent
            folder_key = driver_dir

            # If folder already processed, we still document this INF and create its manifest/installer
            if folder_key in processed_folders:
                dest_folder = folder_to_dest.get(folder_key)
                if dest_folder and dest_folder.is_dir():
                    manifest_file = dest_folder / f"driver_manifest_{inf_path.stem}.json"
                    try:
                        with open(manifest_file, "w", encoding="utf-8") as f:
                            json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                    self._write_install_script(dest_folder, meta, filename=f"install_{inf_path.stem}.bat")
                    self._write_uninstall_script(dest_folder, meta, filename=f"uninstall_{inf_path.stem}.bat")
                organized_drivers.append(meta)
                continue

            # Determine clean destination folder name
            provider_prefix = meta.provider.replace(" ", "_") if meta.provider != "Unknown" else "Driver"
            version_str = f"_v{meta.driver_version}" if meta.driver_version else ""
            clean_name = f"{provider_prefix}_{inf_path.stem}{version_str}"
            clean_name = "".join(c for c in clean_name if c.isalnum() or c in ("_", "-")).rstrip(".")

            dest_folder = self.output_root / meta.category / clean_name
            dest_folder.mkdir(parents=True, exist_ok=True)
            folder_to_dest[folder_key] = dest_folder
            processed_folders.add(folder_key)

            # Copy driver payload files (everything in that directory except installer bloat)
            for item in driver_dir.iterdir():
                if item.name.lower() in self.EXCLUDED_NAMES or item.name.startswith("Setup_"):
                    continue
                target = dest_folder / item.name
                if item.is_file():
                    shutil.copy2(item, target)
                elif item.is_dir() and not item.name.startswith("_"):
                    shutil.copytree(item, target, dirs_exist_ok=True)

            # Generate driver manifest JSON
            manifest_file = dest_folder / "driver_manifest.json"
            try:
                with open(manifest_file, "w", encoding="utf-8") as f:
                    json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            # Generate standalone install.bat
            self._write_install_script(dest_folder, meta)

            # Generate standalone uninstall.bat
            self._write_uninstall_script(dest_folder, meta)

            organized_drivers.append(meta)

        return organized_drivers

    @staticmethod
    def _write_install_script(folder: Path, meta: DriverMetadata, filename: str = "install.bat"):
        script_path = folder / filename
        content = f"""@echo off
chcp 65001 >nul
title Driver Installation - {meta.inf_name}
cd /d "%~dp0"

:: Check for Administrator Elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ========================================================
    echo   ADMINISTRATOR PRIVILEGES REQUIRED...
    echo   Requesting elevation, please click "Yes" in UAC prompt.
    echo ========================================================
    powershell -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   Installing Driver: {meta.inf_name}
echo   Provider: {meta.provider}
echo   Version: {meta.driver_version or 'Unknown'} ({meta.driver_date or ''})
echo ========================================================
echo.

pnputil /add-driver "%~dp0{meta.inf_name}" /install
set ERR=%errorlevel%

echo.
if %ERR% equ 0 (
    echo [OK] Driver installed successfully!
) else if %ERR% equ 3010 (
    echo [OK] Driver installed successfully (System reboot required).
) else (
    echo [ERROR] Driver installation failed with error code: %ERR%
)
echo.
pause
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _write_uninstall_script(folder: Path, meta: DriverMetadata, filename: str = "uninstall.bat"):
        script_path = folder / filename
        content = f"""@echo off
chcp 65001 >nul
title Driver Removal - {meta.inf_name}
cd /d "%~dp0"

echo ========================================================
echo   DeArmour - Driver Removal Helper
echo   Target Driver: {meta.inf_name}
echo ========================================================
echo.

:: Check for Administrator Elevation
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] ADMINISTRATOR PRIVILEGES REQUIRED.
    echo     Please right-click this script and select "Run as administrator".
    pause
    exit /b 1
)

echo [*] Searching Windows Driver Store for published name matching: {meta.inf_name}...
set OEM_NAME=
for /f "usebackq tokens=*" %%o in (`powershell -NoProfile -Command "Get-WindowsDriver -Online | Where-Object {{$_.OriginalFileName -like '*{meta.inf_name}'}} | Select-Object -ExpandProperty Driver -First 1" 2^>nul`) do set OEM_NAME=%%o

if defined OEM_NAME (
    echo [+] Located published package identifier: %OEM_NAME%
    echo [*] Removing %OEM_NAME% from Windows Driver Store...
    pnputil /delete-driver "%OEM_NAME%" /uninstall /force
) else (
    echo [!] Published oemXX.inf identifier not automatically resolved.
    echo [*] Attempting direct Driver Store removal for "{meta.inf_name}"...
    pnputil /delete-driver "{meta.inf_name}" /uninstall /force
    echo.
    echo [INFO] In Windows 10/11, staged drivers are assigned published 'oemXX.inf' names.
    echo        If removal above did not find the package, run 'pnputil /enum-drivers'
    echo        to find the specific oemXX.inf name assigned to this device.
)

echo.
echo [*] Operation completed. Exit code: %errorlevel%
pause
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
