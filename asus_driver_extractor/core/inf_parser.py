"""
Windows Setup Information (.inf) Parser & Driver Analyzer.
Extracts driver metadata, hardware IDs, device names, and required file dependencies.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class DriverMetadata:
    """Metadata extracted from a Windows INF file."""
    inf_path: Path
    inf_name: str
    provider: str = "Unknown"
    driver_class: str = "Unknown"
    category: str = "Other"
    driver_date: Optional[str] = None
    driver_version: Optional[str] = None
    catalog_file: Optional[str] = None
    device_names: List[str] = field(default_factory=list)
    hardware_ids: List[str] = field(default_factory=list)
    associated_files: List[str] = field(default_factory=list)
    architectures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, any]:
        return {
            "inf_name": self.inf_name,
            "provider": self.provider,
            "driver_class": self.driver_class,
            "category": self.category,
            "driver_date": self.driver_date,
            "driver_version": self.driver_version,
            "catalog_file": self.catalog_file,
            "device_names": self.device_names,
            "hardware_ids": self.hardware_ids,
            "associated_files": self.associated_files,
            "architectures": self.architectures,
        }


class InfParser:
    """Parses .inf files and categorizes Windows drivers."""

    WIFI_KEYWORDS = ("wlan", "wifi", "wireless", "802.11", "wi-fi", "8852", "ax200", "ax210", "mt7921")

    CLASS_TO_CATEGORY: Dict[str, str] = {
        "net": "Network_Ethernet",
        "bluetooth": "Bluetooth",
        "media": "Audio",
        "display": "Display_Graphics",
        "system": "Chipset_System",
        "mouse": "Input_Touchpad",
        "keyboard": "Input_Keyboard",
        "hidclass": "Input_HID",
        "biometric": "Biometrics",
        "camera": "Camera",
        "image": "Camera",
        "hdc": "Storage",
        "scsiadapter": "Storage",
        "smartcardreader": "CardReader",
    }

    @staticmethod
    def read_file_safely(file_path: Path) -> str:
        """Attempts reading text with robust BOM and encoding detection."""
        raw = file_path.read_bytes()
        if raw.startswith(b"\xff\xfe"):
            return raw.decode("utf-16-le", errors="replace")
        elif raw.startswith(b"\xfe\xff"):
            return raw.decode("utf-16-be", errors="replace")
        elif raw.startswith(b"\xef\xbb\xbf"):
            return raw.decode("utf-8-sig", errors="replace")

        # Check for UTF-16 without BOM (null bytes between ASCII)
        if b"\x00" in raw[:100]:
            return raw.decode("utf-16-le", errors="replace")

        # Try standard UTF-8 first
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            pass

        # Fallback to ANSI encodings
        for enc in ["cp1254", "cp1252", "latin1"]:
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                pass

        return raw.decode("utf-8", errors="replace")

    @classmethod
    def parse_inf(cls, inf_path: Path) -> DriverMetadata:
        """Parses an INF file and returns a structured DriverMetadata object."""
        inf_path = Path(inf_path)
        content = cls.read_file_safely(inf_path)
        sections = cls._split_sections(content)
        strings = cls._parse_strings(sections.get("strings", []))

        meta = DriverMetadata(
            inf_path=inf_path,
            inf_name=inf_path.name
        )

        # Parse [Version] section
        version_lines = sections.get("version", [])
        for line in version_lines:
            key, val = cls._parse_key_val(line)
            if not key:
                continue
            key_lower = key.lower()
            val = cls._resolve_string(val, strings)

            if key_lower == "provider":
                meta.provider = val.strip('"')
            elif key_lower == "class":
                meta.driver_class = val.strip('"')
            elif key_lower == "catalogfile":
                meta.catalog_file = val.strip('"')
            elif key_lower == "driverver":
                date_ver = [x.strip() for x in val.split(",")]
                if date_ver:
                    meta.driver_date = date_ver[0].strip('"')
                if len(date_ver) > 1:
                    meta.driver_version = date_ver[1].strip('"')

        # Determine Category
        meta.category = cls._categorize(meta.driver_class, content, strings)

        # Parse Associated Files from [SourceDisksFiles] and [CopyFiles]
        meta.associated_files = cls._find_associated_files(sections)

        # Parse Devices and Hardware IDs
        meta.device_names, meta.hardware_ids, meta.architectures = cls._parse_devices(sections, strings)

        return meta

    @classmethod
    def _categorize(cls, driver_class: str, content: str, strings: Dict[str, str]) -> str:
        """Determines the clean category for the driver."""
        cls_lower = driver_class.lower()
        content_lower = content.lower()

        # Check for Wi-Fi vs Ethernet if class is Net
        if cls_lower == "net":
            if any(kw in content_lower for kw in InfParser.WIFI_KEYWORDS):
                return "Network_Wireless"
            return "Network_Ethernet"

        # Check if Bluetooth is in device descriptions even if class is generic
        if "bluetooth" in content_lower:
            return "Bluetooth"

        # Check audio
        if any(kw in content_lower for kw in ["realtek audio", "high definition audio", "sound", "audio endpoint"]):
            if cls_lower in ["media", "softwarecomponent", "system"]:
                return "Audio"

        # Touchpad check
        if any(kw in content_lower for kw in ["touchpad", "precision touchpad", "asus precision"]):
            return "Input_Touchpad"

        return cls.CLASS_TO_CATEGORY.get(cls_lower, "Other")

    @classmethod
    def _split_sections(cls, content: str) -> Dict[str, List[str]]:
        """Splits an INF file into case-insensitive sections."""
        sections: Dict[str, List[str]] = {}
        current_section = None

        for raw_line in content.splitlines():
            line = raw_line.strip()
            # Strip comments
            if ";" in line:
                line = line.split(";", 1)[0].strip()
            if not line:
                continue

            sec_match = re.match(r"^\[([a-zA-Z0-9_\-.]+)\]", line)
            if sec_match:
                current_section = sec_match.group(1).lower()
                if current_section not in sections:
                    sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)

        return sections

    @classmethod
    def _parse_strings(cls, string_lines: List[str]) -> Dict[str, str]:
        """Builds a string token lookup dictionary from [Strings] section."""
        strings: Dict[str, str] = {}
        for line in string_lines:
            key, val = cls._parse_key_val(line)
            if key and val:
                strings[key.lower()] = val.strip().strip('"')
        return strings

    @classmethod
    def _resolve_string(cls, val: str, strings: Dict[str, str]) -> str:
        """Replaces %StringToken% with actual string value."""
        if not val:
            return val
        token_match = re.search(r"%([a-zA-Z0-9_\-]+)%", val)
        if token_match:
            tok = token_match.group(1).lower()
            if tok in strings:
                return strings[tok]
        return val

    @classmethod
    def _parse_key_val(cls, line: str):
        if "=" in line:
            parts = line.split("=", 1)
            return parts[0].strip(), parts[1].strip()
        return None, None

    @classmethod
    def _find_associated_files(cls, sections: Dict[str, List[str]]) -> List[str]:
        """Finds all filenames referenced in [SourceDisksFiles] or copy sections."""
        files: Set[str] = set()

        for sec_name, lines in sections.items():
            if "sourcedisksfiles" in sec_name:
                for line in lines:
                    filename = line.split("=")[0].strip().strip('"')
                    if filename:
                        files.add(filename)
            elif "copyfiles" in sec_name or "files" in sec_name:
                for line in lines:
                    parts = line.split(",")
                    for part in parts:
                        clean = part.strip().strip('"')
                        if clean and "." in clean:
                            files.add(clean)

        return sorted(list(files))

    @classmethod
    def _parse_devices(cls, sections: Dict[str, List[str]], strings: Dict[str, str]):
        device_names: Set[str] = set()
        hardware_ids: Set[str] = set()
        architectures: Set[str] = set()

        # Inspect [Manufacturer] section
        mfg_lines = sections.get("manufacturer", [])
        for line in mfg_lines:
            _, val = cls._parse_key_val(line)
            if val:
                for part in val.split(",")[1:]:
                    part_clean = part.strip().strip('"')
                    if part_clean.lower().startswith("nt"):
                        architectures.add(part_clean)

        # Inspect model sections
        for sec_name, lines in sections.items():
            if any(sec_name.startswith(m) for m in ["mfg", "models", "realtek", "nvidia", "amd", "intel"]) or "nt" in sec_name:
                for line in lines:
                    key, val = cls._parse_key_val(line)
                    if key and val:
                        resolved_desc = cls._resolve_string(key, strings)
                        if resolved_desc and len(resolved_desc) > 3 and not resolved_desc.startswith("%"):
                            device_names.add(resolved_desc)

                        parts = [p.strip().strip('"') for p in val.split(",")]
                        for p in parts:
                            if any(p.upper().startswith(prefix) for prefix in ["PCI\\", "USB\\", "ACPI\\", "HDAUDIO\\"]):
                                hardware_ids.add(p)

        return sorted(list(device_names))[:10], sorted(list(hardware_ids))[:10], sorted(list(architectures))
