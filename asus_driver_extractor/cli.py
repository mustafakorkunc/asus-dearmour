"""
Command Line Interface (CLI) for DeArmour.
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
        if sys.stdout is not None:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr is not None:
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
        return [p for p in exes if p.stat().st_size > 100_000]
    return []


def run_pipeline(targets: List[Path], output_dir: Path) -> List[DriverMetadata]:
    """Executes the extraction and categorization pipeline on all targets."""
    extractor = ArchiveExtractor()
    organizer = DriverOrganizer(output_dir)
    all_drivers: List[DriverMetadata] = []

    print(f"{Colors.BOLD}[*] Output Directory:{Colors.RESET} {output_dir}")
    print(f"{Colors.BOLD}[*] Target Installer(s):{Colors.RESET} {len(targets)}\n")

    for i, target_exe in enumerate(targets, 1):
        print(f"{Colors.YELLOW}[{i}/{len(targets)}] Extracting:{Colors.RESET} {target_exe.name} ({target_exe.stat().st_size / 1_000_000:.1f} MB)")
        start_time = time.time()

        with tempfile.TemporaryDirectory(prefix="dearmour_stage_") as temp_stage:
            stage_path = Path(temp_stage)
            try:
                # 1. Carve and unpack binary
                unpacked = extractor.unpack_executable(target_exe, stage_path)
                # 2. Organize drivers
                drivers = organizer.organize_extracted_pool(stage_path)
                elapsed = time.time() - start_time

                if drivers:
                    for d in drivers:
                        print(f"    {Colors.GREEN}✔ Found Driver:{Colors.RESET} [{d.category}] {d.inf_name} - {d.provider} ({d.driver_version or 'N/A'})")
                    all_drivers.extend(drivers)
                else:
                    print(f"    {Colors.YELLOW}⚠ No INF driver found ({elapsed:.1f}s){Colors.RESET}")

            except Exception as e:
                print(f"    {Colors.RED}✖ Error encountered:{Colors.RESET} {e}")

    # Generate master installer scripts
    if all_drivers:
        MasterScriptGenerator.generate_scripts(output_dir, all_drivers)
        print(f"\n{Colors.GREEN}{Colors.BOLD}✔ Master deployment scripts successfully generated:{Colors.RESET}")
        print(f"    - {output_dir / 'INSTALL_ALL_DRIVERS.bat'}")
        print(f"    - {output_dir / 'INSTALL_ALL_DRIVERS.ps1'}")
        print(f"    - {output_dir / 'drivers_catalog.json'}")

    return all_drivers


def print_summary(drivers: List[DriverMetadata], output_dir: Path):
    """Prints a structured summary table of all extracted drivers."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}========================================================================{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}                   EXTRACTED DRIVERS SUMMARY                             {Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}========================================================================{Colors.RESET}")
    print(f"{'Category':<20} | {'Driver Name':<25} | {'Provider':<15} | {'Version':<15}")
    print("-" * 80)

    for d in sorted(drivers, key=lambda x: (x.category, x.inf_name)):
        cat = d.category[:18]
        name = d.inf_name[:23]
        prov = d.provider[:13]
        ver = (d.driver_version or "N/A")[:14]
        print(f"{cat:<20} | {name:<25} | {prov:<15} | {ver:<15}")

    print("-" * 80)
    print(f"{Colors.BOLD}Total Driver Packages:{Colors.RESET} {len(drivers)}")
    print(f"{Colors.BOLD}Output Location:{Colors.RESET} {output_dir.resolve()}\n")


def main():
    parser = argparse.ArgumentParser(
        description="DeArmour - Strip bloated ASUS installer wrappers into pure, bare-metal INF drivers."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=None,
        help="Path to an ASUS driver .exe or directory containing driver installers."
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Target directory to store extracted drivers. (Default: ./Extracted_Drivers)"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively scan subdirectories for driver .exe files."
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the graphical user interface (GUI)."
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"DeArmour v{__version__}"
    )

    args = parser.parse_args()

    if args.gui or (args.input is None and len(sys.argv) == 1):
        try:
            from asus_driver_extractor.gui import launch_gui
            launch_gui()
            return
        except ImportError as e:
            print(f"{Colors.RED}Failed to launch GUI: {e}{Colors.RESET}")
            sys.exit(1)

    print_banner()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"{Colors.RED}[ERROR] Target path does not exist: {input_path}{Colors.RESET}")
        sys.exit(1)

    targets = collect_target_files(input_path, recursive=args.recursive)
    if not targets:
        print(f"{Colors.YELLOW}[!] No executable driver installers found in the specified path.{Colors.RESET}")
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
        print(f"{Colors.YELLOW}[!] No driver packages could be extracted.{Colors.RESET}")


if __name__ == "__main__":
    main()
