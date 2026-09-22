"""
ASUS Official Driver Downloader & Hardware Auto-Detection Engine.
Queries official ASUS Support REST endpoints to fetch direct CDN download URLs.

Special thanks and architectural attribution to:
- Seerge & the G-Helper project (https://github.com/seerge/g-helper)
  for pioneering the reverse engineering and discovery of the official ASUS Support REST API.
"""

from dataclasses import dataclass
import json
import os
import platform
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable


@dataclass
class AsusDriverPackage:
    """Represents a remote driver package available on ASUS servers."""
    title: str
    category: str
    version: str
    release_date: str
    download_url: str
    file_size: Optional[str] = None
    description: Optional[str] = None

    @property
    def filename(self) -> str:
        parsed = urllib.parse.urlparse(self.download_url)
        name = Path(parsed.path).name
        return name if name else f"{self.title.replace(' ', '_')}.exe"


class AsusDownloader:
    """
    Interface for discovering local ASUS hardware, querying official ASUS driver catalogs,
    and downloading official packages.
    """

    API_BASE = "https://rog.asus.com/support/webapi/product/GetPDDrivers"

    def __init__(self, download_dir: Optional[Path] = None):
        self.download_dir = Path(download_dir) if download_dir else Path.home() / "Downloads" / "AsusDrivers"
        self.download_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def detect_local_system() -> Dict[str, Any]:
        """
        Fast, zero-dependency detection of ASUS laptop model and Windows OS version
        via the Windows Registry.
        """
        info = {
            "model": "FA506NC",
            "full_name": "ASUS Laptop",
            "manufacturer": "ASUSTeK COMPUTER INC.",
            "os_name": "Windows 11 64-bit",
            "osid": 52,
            "is_asus": True,
        }

        # 1. Determine OS build and ASUS OS ID
        try:
            win_ver = sys.getwindowsversion()
            is_win11 = win_ver.build >= 22000
            info["os_name"] = "Windows 11 64-bit" if is_win11 else "Windows 10 64-bit"
            info["osid"] = 52 if is_win11 else 45
        except Exception:
            pass

        # 2. Read BIOS/Baseboard hardware model from Windows Registry
        if os.name == "nt":
            try:
                import winreg
                key_path = r"HARDWARE\DESCRIPTION\System\BIOS"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    try:
                        baseboard, _ = winreg.QueryValueEx(key, "BaseBoardProduct")
                    except FileNotFoundError:
                        baseboard = ""

                    try:
                        product_name, _ = winreg.QueryValueEx(key, "SystemProductName")
                    except FileNotFoundError:
                        product_name = ""

                    try:
                        mfg, _ = winreg.QueryValueEx(key, "SystemManufacturer")
                    except FileNotFoundError:
                        mfg = ""

                    if mfg:
                        info["manufacturer"] = mfg
                        info["is_asus"] = "asus" in mfg.lower()

                    if product_name:
                        info["full_name"] = product_name

                    # Best candidate for model is BaseBoardProduct (e.g. FA506NC, GA402RJ)
                    candidate = baseboard.strip() if baseboard else product_name.strip()
                    if candidate:
                        # Extract core model code (e.g., 'FA506NC_FA506NC' -> 'FA506NC')
                        parts = re.findall(r"[A-Za-z0-9]{4,10}", candidate)
                        if parts:
                            info["model"] = parts[0].upper()
                        else:
                            info["model"] = candidate.split()[0].upper()
            except Exception:
                pass

        return info

    def search_model(self, model_name: str) -> List[Dict[str, str]]:
        """Searches model stubs."""
        clean = model_name.strip().upper()
        return [{"model": clean, "status": "ASUS Support API Ready"}]

    def fetch_driver_list(self, model_name: str, osid: int = 52) -> List[AsusDriverPackage]:
        """
        Retrieves the catalog of official driver installer packages for the specified model
        directly from the ASUS Support REST API.
        """
        clean_model = model_name.strip().upper()
        if not clean_model:
            return []

        # Construct primary URL
        urls = [
            f"{self.API_BASE}?website=global&model={clean_model}&cpu={clean_model}&osid={osid}",
            f"{self.API_BASE}?website=global&model={clean_model}&osid={osid}",
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
        }

        data = None
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12) as response:
                    raw = response.read().decode("utf-8")
                    parsed = json.loads(raw)
                    if parsed.get("Result", {}).get("Count", 0) > 0:
                        data = parsed
                        break
            except Exception:
                continue

        if not data:
            return []

        packages: List[AsusDriverPackage] = []
        categories = data.get("Result", {}).get("Obj", [])

        for cat in categories:
            cat_name = cat.get("Name", "Other").strip()
            files = cat.get("Files", [])

            for f in files:
                title = f.get("Title", "").strip()
                version = f.get("Version", "").strip()
                release_date = f.get("ReleaseDate", "").strip()
                file_size = f.get("FileSize", "").strip()
                desc = f.get("Description", "").strip()

                download_urls = f.get("DownloadUrl", {})
                global_url = download_urls.get("Global", "").strip()

                # Filter out Microsoft Store links, empty URLs, or non-executable packages
                if not global_url or not global_url.startswith("http"):
                    continue

                lower_url = global_url.lower()
                is_package = any(ext in lower_url for ext in [".exe", ".zip", ".7z", ".cab"])
                if not is_package:
                    continue

                pkg = AsusDriverPackage(
                    title=title or Path(urllib.parse.urlparse(global_url).path).name,
                    category=cat_name,
                    version=version,
                    release_date=release_date,
                    download_url=global_url,
                    file_size=file_size,
                    description=desc,
                )
                packages.append(pkg)

        return packages

    def download_package(
        self,
        package: AsusDriverPackage,
        target_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Streams and downloads an official driver package from ASUS servers into target_dir.
        Optionally reports progress via callback(bytes_written, total_bytes).
        """
        dest_dir = Path(target_dir) if target_dir else self.download_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        filename = package.filename
        target_path = dest_dir / filename

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        req = urllib.request.Request(package.download_url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("content-length", 0))
            bytes_written = 0
            chunk_size = 64 * 1024  # 64 KB chunks

            with open(target_path, "wb") as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    bytes_written += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_written, total_size)

        return target_path
