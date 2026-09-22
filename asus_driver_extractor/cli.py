"""
Command Line Interface (CLI) for AsusDriverExtractor.
Supports single-file extraction, batch directory scanning, rich terminal reporting,
and automated script generation.
"""

import argparse
import sys
import tempfile
import time
from pathlib import Path
from typing import List

from asus_driver_extractor import __version__
from asus_driver_extractor.core.extractor import ArchiveExtractor
from asus_driver_extractor.core.organizer import DriverOrganizer
from asus_driver_extractor.core.script_generator import MasterScriptGenerator
from asus_driver_extractor.core.inf_parser import DriverMetadata


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Colors:
    """ANSI color fallbacks."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner():
    banner = rf"""{Colors.CYAN}{Colors.BOLD}
   ___       ___                              
  / _ \___  / _ | ______ _  ___  __ _____ 
 / // / -_)/ __ |/ __/  ' \/ _ \/ // / __/
/____/\__//_/ |_/_/ /_/_/_/\___/\_,_/_/   
           v{__version__} | Pure Bare-Metal Driver Extractor
           https://github.com/mustafakorkunc/asus-dearmour
{Colors.RESET}"""
    print(banner)


def collect_target_files(input_path: Path, recursive: bool = False) -> List[Path]:
    """Finds all .exe driver installers in the specified path."""
    input_path = Path(input_path).resolve()
    if input_path.is_file() and input_path.suffix.lower() == ".exe":
        return [input_path]
    elif input_path.is_dir():
        pattern = "**/*.exe" if recursive else "*.exe"
        exes = [p for p in input_path.glob(pattern) if p.is_file()]
        # Exclude already extracted tools or small helpers
        return [p for p in exes if p.stat().st_size > 100_000]
    return []


def run_pipeline(targets: List[Path], output_dir: Path) -> List[DriverMetadata]:
    """Executes the extraction and categorization pipeline on all targets."""
    extractor = ArchiveExtractor()
    organizer = DriverOrganizer(output_dir)
    all_drivers: List[DriverMetadata] = []

    print(f"{Colors.BOLD}[*] Hedef Dizin:{Colors.RESET} {output_dir}")
    print(f"{Colors.BOLD}[*] İşlenecek EXE Sayısı:{Colors.RESET} {len(targets)}\n")

    for i, target_exe in enumerate(targets, 1):
        print(f"{Colors.YELLOW}[{i}/{len(targets)}] Ayrıştırılıyor:{Colors.RESET} {target_exe.name} ({target_exe.stat().st_size / 1_000_000:.1f} MB)")
        start_time = time.time()

        with tempfile.TemporaryDirectory(prefix="ade_stage_") as temp_stage:
            stage_path = Path(temp_stage)
            try:
                # 1. Carve and unpack binary
                unpacked = extractor.unpack_executable(target_exe, stage_path)
                # 2. Organize drivers
                drivers = organizer.organize_extracted_pool(stage_path)
                elapsed = time.time() - start_time

                if drivers:
                    for d in drivers:
                        print(f"    {Colors.GREEN}✔ Bulunan Sürücü:{Colors.RESET} [{d.category}] {d.inf_name} - {d.provider} ({d.driver_version or 'N/A'})")
                    all_drivers.extend(drivers)
                else:
                    print(f"    {Colors.YELLOW}⚠ INF sürücüsü bulunamadı ({elapsed:.1f}s){Colors.RESET}")

            except Exception as e:
                print(f"    {Colors.RED}✖ Hata oluştu:{Colors.RESET} {e}")

    # Generate master installer scripts
    if all_drivers:
        MasterScriptGenerator.generate_scripts(output_dir, all_drivers)
        print(f"\n{Colors.GREEN}{Colors.BOLD}✔ Toplu kurulum betikleri oluşturuldu:{Colors.RESET}")
        print(f"    - {output_dir / 'INSTALL_ALL_DRIVERS.bat'}")
        print(f"    - {output_dir / 'INSTALL_ALL_DRIVERS.ps1'}")
        print(f"    - {output_dir / 'drivers_catalog.json'}")

    return all_drivers


def print_summary(drivers: List[DriverMetadata], output_dir: Path):
    """Prints a beautiful summary table of all extracted drivers."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}========================================================================{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}                   AYIKLANAN SÜRÜCÜLER ÖZETİ                             {Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}========================================================================{Colors.RESET}")
    print(f"{'Kategori':<20} | {'Sürücü Adı':<25} | {'Sağlayıcı':<15} | {'Sürüm':<15}")
    print("-" * 80)

    for d in sorted(drivers, key=lambda x: (x.category, x.inf_name)):
        cat = d.category[:18]
        name = d.inf_name[:23]
        prov = d.provider[:13]
        ver = (d.driver_version or "N/A")[:14]
        print(f"{cat:<20} | {name:<25} | {prov:<15} | {ver:<15}")

    print("-" * 80)
    print(f"{Colors.BOLD}Toplam Sürücü Paketi:{Colors.RESET} {len(drivers)}")
    print(f"{Colors.BOLD}Çıktı Konumu:{Colors.RESET} {output_dir.resolve()}\n")


def main():
    parser = argparse.ArgumentParser(
        description="AsusDriverExtractor (ADE) - ASUS Sürücülerini INF/SYS olarak ayıklama ve paketleme aracı."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="ASUS sürücü .exe dosyası veya birden fazla .exe içeren klasör yolu."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Çıkarılan sürücülerin kaydedileceği hedef klasör. (Varsayılan: ./Extracted_Drivers)"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Alt klasörlerdeki .exe dosyalarını da tara."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Grafik arayüzünü (GUI) başlat."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"AsusDriverExtractor v{__version__}"
    )

    args = parser.parse_args()

    if args.gui or (args.input is None and len(sys.argv) == 1):
        # Launch GUI
        try:
            from asus_driver_extractor.gui import launch_gui
            launch_gui()
            return
        except ImportError as e:
            print(f"{Colors.RED}GUI başlatılamadı: {e}{Colors.RESET}")
            sys.exit(1)

    print_banner()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"{Colors.RED}[HATA] Belirtilen yol bulunamadı: {input_path}{Colors.RESET}")
        sys.exit(1)

    targets = collect_target_files(input_path, recursive=args.recursive)
    if not targets:
        print(f"{Colors.YELLOW}[!] Belirtilen yolda işlenebilecek .exe dosyası bulunamadı.{Colors.RESET}")
        sys.exit(0)

    # Output directory
    if args.output:
        out_dir = Path(args.output)
    elif input_path.is_dir():
        out_dir = input_path / "Extracted_Drivers"
    else:
        out_dir = input_path.parent / "Extracted_Drivers"

    out_dir.mkdir(parents=True, exist_ok=True)

    drivers = run_pipeline(targets, out_dir)
    if drivers:
        print_summary(drivers, out_dir)
    else:
        print(f"{Colors.YELLOW}[!] Hiçbir sürücü paketi çıkarılamadı.{Colors.RESET}")


if __name__ == "__main__":
    main()
