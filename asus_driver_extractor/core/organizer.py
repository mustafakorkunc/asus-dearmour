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

        for inf_path in inf_files:
            driver_dir = inf_path.parent
            meta = InfParser.parse_inf(inf_path)

            # Avoid double-processing the exact same directory if it has multiple INFs
            folder_key = driver_dir
            if folder_key in processed_folders:
                organized_drivers.append(meta)
                continue
            processed_folders.add(folder_key)

            # Determine clean destination folder name
            provider_prefix = meta.provider.replace(" ", "_") if meta.provider != "Unknown" else "Driver"
            version_str = f"_v{meta.driver_version}" if meta.driver_version else ""
            clean_name = f"{provider_prefix}_{inf_path.stem}{version_str}"
            clean_name = "".join(c for c in clean_name if c.isalnum() or c in ("_", "-")).rstrip(".")

            dest_folder = self.output_root / meta.category / clean_name
            dest_folder.mkdir(parents=True, exist_ok=True)

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
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(meta.to_dict(), f, indent=2, ensure_ascii=False)

            # Generate standalone install.bat
            self._write_install_script(dest_folder, meta)

            # Generate standalone uninstall.bat
            self._write_uninstall_script(dest_folder, meta)

            organized_drivers.append(meta)

        return organized_drivers

    @staticmethod
    def _write_install_script(folder: Path, meta: DriverMetadata):
        script_path = folder / "install.bat"
        content = f"""@echo off
chcp 65001 >nul
title Driver Installation - {meta.inf_name}
cd /d "%~dp0"

echo ========================================================
echo   Installing Driver: {meta.inf_name}
echo   Provider: {meta.provider}
echo   Version: {meta.driver_version or 'Unknown'} ({meta.driver_date or ''})
echo ========================================================
echo.

pnputil /add-driver "{meta.inf_name}" /install
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
    def _write_uninstall_script(folder: Path, meta: DriverMetadata):
        script_path = folder / "uninstall.bat"
        content = f"""@echo off
chcp 65001 >nul
title Driver Removal - {meta.inf_name}
cd /d "%~dp0"

echo [*] Removing driver package {meta.inf_name} from Windows Driver Store...
pnputil /delete-driver {meta.inf_name} /uninstall /force
echo [*] Operation completed. Exit code: %errorlevel%
pause
"""
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(content)
