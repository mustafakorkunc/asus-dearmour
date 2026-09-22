"""
Archive & Binary Stream Extractor Engine.
Carves embedded archives out of ASUS PE executables and recursively unpacks them.
"""

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any


class ExtractionError(Exception):
    """Raised when an extraction operation fails."""
    pass


# Windows flag to suppress flashing black command prompt windows
WIN_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0



class ArchiveExtractor:
    """
    Handles carving embedded archives out of PE files and unpacking
    all nested archive formats recursively.
    """

    MAGIC_SIGNATURES: Dict[str, bytes] = {
        "7z": b"7z\xbc\xaf\x27\x1c",
        "zip": b"PK\x03\x04",
        "cab": b"MSCF",
        "rar": b"Rar!\x1a\x07",
    }

    def __init__(self, temp_base_dir: Optional[Path] = None):
        self.temp_base_dir = temp_base_dir or Path(tempfile.gettempdir())
        self.tar_exe = self._find_system_tool("tar.exe")
        self.expand_exe = self._find_system_tool("expand.exe")
        self.seven_zip = self._find_seven_zip()

    @staticmethod
    def _find_system_tool(tool_name: str) -> Optional[str]:
        # Use hardcoded path instead of os.environ.get("SystemRoot") to prevent
        # execution of malicious binaries if the environment variable is compromised.
        system32 = Path(r"C:\Windows\System32") / tool_name
        if system32.is_file():
            return str(system32)
        shutil_path = shutil.which(tool_name)
        return shutil_path if shutil_path else None

    @staticmethod
    def _find_seven_zip() -> Optional[str]:
        candidates = [
            shutil.which("7z"),
            shutil.which("7za"),
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]
        for c in candidates:
            if c and Path(c).is_file():
                return str(c)
        return None

    def carve_embedded_archives(self, file_path: Path, output_dir: Path) -> List[Tuple[str, Path]]:
        """
        Scans a binary file for embedded archive signatures (7z, ZIP, CAB, RAR)
        and carves out matching stream slices using memory mapping for efficiency.
        """
        carved_files: List[Tuple[str, Path]] = []
        file_path = Path(file_path).resolve()
        if not file_path.is_file():
            return []

        file_size = file_path.stat().st_size
        if file_size == 0:
            return []

        output_dir.mkdir(parents=True, exist_ok=True)

        with open(file_path, "rb") as f:
            mm = None
            try:
                import mmap
                mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            except (ValueError, OSError):
                mm = None

            try:
                data = mm if mm is not None else f.read()

                for arch_type, signature in self.MAGIC_SIGNATURES.items():
                    pos = 0
                    idx = 0
                    while True:
                        offset = data.find(signature, pos)
                        if offset == -1:
                            break

                        slice_path = output_dir / f"carved_{idx}.{arch_type}"
                        with open(slice_path, "wb") as out:
                            chunk_size = 1024 * 1024  # 1 MB chunk streaming
                            cur = offset
                            while cur < file_size:
                                end = min(cur + chunk_size, file_size)
                                out.write(data[cur:end])
                                cur = end

                        # Verify if the slice can be read
                        if self._verify_archive(slice_path, arch_type):
                            carved_files.append((arch_type, slice_path))
                            idx += 1
                        else:
                            try:
                                slice_path.unlink()
                            except Exception:
                                pass

                        pos = offset + len(signature)
            finally:
                if mm is not None:
                    mm.close()

        return carved_files

    def _verify_archive(self, file_path: Path, arch_type: str) -> bool:
        """Quick check to see if carved archive is structurally valid."""
        try:
            if arch_type == "zip":
                return zipfile.is_zipfile(file_path)
            elif arch_type == "7z" and self.tar_exe:
                res = subprocess.run(
                    [self.tar_exe, "-tf", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=WIN_NO_WINDOW,
                )
                return res.returncode == 0
            elif arch_type == "7z" and self.seven_zip:
                res = subprocess.run(
                    [self.seven_zip, "t", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=WIN_NO_WINDOW,
                )
                return res.returncode == 0
            elif arch_type == "rar":
                if self.seven_zip:
                    res = subprocess.run(
                        [self.seven_zip, "t", str(file_path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        creationflags=WIN_NO_WINDOW,
                    )
                    return res.returncode == 0
                return False
            elif arch_type == "cab" and self.expand_exe:
                res = subprocess.run(
                    [self.expand_exe, "-D", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=WIN_NO_WINDOW,
                )
                return res.returncode == 0
        except Exception:
            return False
        return False

    @staticmethod
    def _safe_extract_zip(zf: zipfile.ZipFile, dest_dir: Path) -> bool:
        """
        Safely extracts all members from a ZipFile, preventing directory traversal
        and Zip Slip attacks (e.g. ../, /etc/passwd, C:\\Windows).
        """
        import re
        dest_dir_resolved = dest_dir.resolve()
        for member in zf.infolist():
            raw_name = member.filename
            # Normalize path separators
            norm_name = raw_name.replace("\\", "/").strip()
            # Disallow absolute paths or Windows drive letters
            if norm_name.startswith("/") or re.match(r"^[a-zA-Z]:", norm_name):
                raise ExtractionError(f"Unsafe path detected in archive: {raw_name}")

            target_path = (dest_dir / norm_name).resolve()
            # Ensure resolved target is within destination directory
            if not (target_path == dest_dir_resolved or dest_dir_resolved in target_path.parents):
                raise ExtractionError(f"Path traversal detected in archive: {raw_name}")

            if member.is_dir() or norm_name.endswith("/"):
                target_path.mkdir(parents=True, exist_ok=True)
            else:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        return True

    def unpack_archive(self, archive_path: Path, dest_dir: Path) -> bool:
        """Unpacks a single archive file into dest_dir using the best available tool."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        suffix = archive_path.suffix.lower()

        # 1. Standard ZIP
        if suffix == ".zip" or zipfile.is_zipfile(archive_path):
            try:
                with zipfile.ZipFile(archive_path, "r") as zf:
                    return self._safe_extract_zip(zf, dest_dir)
            except ExtractionError:
                raise
            except Exception:
                pass

        # 2. 7-Zip / Tar using system tar.exe (Windows 10/11 built-in)
        if self.tar_exe and (suffix in [".7z", ".tar", ".gz", ".xz"] or suffix == ""):
            try:
                res = subprocess.run(
                    [self.tar_exe, "-xf", str(archive_path), "-C", str(dest_dir)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=WIN_NO_WINDOW,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        # 3. 7z.exe if installed
        if self.seven_zip:
            try:
                res = subprocess.run(
                    [self.seven_zip, "x", f"-o{dest_dir}", "-y", str(archive_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=WIN_NO_WINDOW,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        # 4. Microsoft CAB files via expand.exe
        if suffix == ".cab" and self.expand_exe:
            try:
                res = subprocess.run(
                    [self.expand_exe, "-F:*", str(archive_path), str(dest_dir)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=WIN_NO_WINDOW,
                )
                if res.returncode == 0:
                    return True
            except Exception:
                pass

        return False

    def unpack_executable(self, exe_path: Path, staging_dir: Path) -> List[Path]:
        """
        Primary entry point: Unpacks an ASUS installer .exe and all nested archives,
        returning a flat list of all unpacked files.
        """
        exe_path = Path(exe_path).resolve()
        if not exe_path.is_file():
            raise FileNotFoundError(f"File not found: {exe_path}")

        staging_dir.mkdir(parents=True, exist_ok=True)
        carve_dir = staging_dir / "_carved"
        carve_dir.mkdir(parents=True, exist_ok=True)

        try:
            extracted_any = False

            # 1. Carve embedded archive streams first (e.g. ASUS SetupLdr with appended 7z/CAB/ZIP)
            carved = self.carve_embedded_archives(exe_path, carve_dir)
            for _, carved_path in carved:
                if self.unpack_archive(carved_path, staging_dir):
                    extracted_any = True

            # 2. If carving didn't find archives, try direct extraction (e.g. pure 7z/ZIP SFX)
            if not extracted_any:
                if self.unpack_archive(exe_path, staging_dir):
                    extracted_any = True

            # 3. Fallback: Check if 7z.exe can handle the installer directly
            if not extracted_any and self.seven_zip:
                res = subprocess.run(
                    [self.seven_zip, "x", f"-o{staging_dir}", "-y", str(exe_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    creationflags=WIN_NO_WINDOW,
                )
                if res.returncode == 0:
                    extracted_any = True

            # Recursive pass: find any archives nested inside the extracted folder
            self._unpack_nested_archives(staging_dir)

            return [p for p in staging_dir.rglob("*") if p.is_file()]
        finally:
            # Cleanup intermediate carve folder safely
            if carve_dir.is_dir():
                shutil.rmtree(carve_dir, ignore_errors=True)

    def _unpack_nested_archives(self, directory: Path, max_depth: int = 5):
        """Recursively scans and unpacks any archives found inside unpacked contents."""
        archive_exts = {".7z", ".zip", ".cab", ".tar", ".gz", ".xz"}
        if self.seven_zip:
            archive_exts.add(".rar")

        for depth in range(max_depth):
            nested_archives = [
                p for p in directory.rglob("*")
                if p.is_file() and p.suffix.lower() in archive_exts
            ]
            if not nested_archives:
                break

            unpacked_any_in_pass = False
            for arch in nested_archives:
                # Sub-folder for the nested archive
                target_sub = arch.parent / arch.stem
                if self.unpack_archive(arch, target_sub):
                    unpacked_any_in_pass = True
                    try:
                        arch.unlink()  # Remove archive file once extracted
                    except Exception:
                        pass

            if not unpacked_any_in_pass:
                break
