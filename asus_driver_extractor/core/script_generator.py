"""
Deployment Script Generator.
Generates master automated installation batch and PowerShell scripts
with built-in administrator elevation checks.
"""

import json
from pathlib import Path
from typing import List
from asus_driver_extractor.core.inf_parser import DriverMetadata


class MasterScriptGenerator:
    """Creates master one-click installer scripts for the entire driver repository."""

    @classmethod
    def generate_scripts(cls, output_root: Path, drivers: List[DriverMetadata]):
        output_root = Path(output_root).resolve()
        cls._generate_master_bat(output_root, drivers)
        cls._generate_master_ps1(output_root, drivers)
        cls._generate_master_catalog(output_root, drivers)

    @classmethod
    def _generate_master_bat(cls, output_root: Path, drivers: List[DriverMetadata]):
        bat_file = output_root / "INSTALL_ALL_DRIVERS.bat"
        content = r"""@echo off
chcp 65001 >nul
title DeArmour - Batch Driver Installer
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
echo   DeArmour - BATCH DRIVER DEPLOYMENT
echo   Target: Windows Driver Store (pnputil)
echo ========================================================
echo.

setlocal enabledelayedexpansion

echo [*] Scanning and injecting drivers into Windows Driver Store...
echo.

pnputil /add-driver "%~dp0*.inf" /subdirs /install
set ERR=%errorlevel%

echo.
echo ========================================================
if %ERR% equ 0 (
    echo   [SUCCESS] All drivers installed successfully!
) else if %ERR% equ 3010 (
    echo   [SUCCESS] Drivers installed! Please reboot your computer.
) else (
    echo   [INFO] Process completed with return code: %ERR%
)
echo ========================================================
echo.
pause
"""
        with open(bat_file, "w", encoding="utf-8") as f:
            f.write(content)

    @classmethod
    def _generate_master_ps1(cls, output_root: Path, drivers: List[DriverMetadata]):
        ps1_file = output_root / "INSTALL_ALL_DRIVERS.ps1"
        content = r"""# DeArmour Batch Driver Deployment (PowerShell)
# Must be executed with Administrator privileges.

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] This operation requires Administrator privileges. Relaunching as admin..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  DeArmour - BATCH DRIVER DEPLOYMENT (PowerShell)       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$infFiles = Get-ChildItem -Path $PSScriptRoot -Filter "*.inf" -Recurse
Write-Host "[*] Total discovered INF driver packages: $($infFiles.Count)" -ForegroundColor Green

foreach ($inf in $infFiles) {
    Write-Host "[+] Installing: $($inf.Name) ($($inf.Directory.Name))..." -ForegroundColor White
    $res = Start-Process pnputil -ArgumentList "/add-driver `"$($inf.FullName)`" /install" -Wait -PassThru -NoNewWindow
    if ($res.ExitCode -eq 0 -or $res.ExitCode -eq 3010) {
        Write-Host "    -> Success (ExitCode: $($res.ExitCode))" -ForegroundColor Green
    } else {
        Write-Host "    -> Warning / Info (ExitCode: $($res.ExitCode))" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ALL DRIVER DEPLOYMENTS COMPLETED!                     " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Read-Host "Press Enter to exit"
"""
        with open(ps1_file, "w", encoding="utf-8") as f:
            f.write(content)

    @classmethod
    def _generate_master_catalog(cls, output_root: Path, drivers: List[DriverMetadata]):
        catalog_file = output_root / "drivers_catalog.json"
        catalog_data = {
            "total_drivers": len(drivers),
            "categories": sorted(list({d.category for d in drivers})),
            "drivers": [d.to_dict() for d in drivers],
        }
        with open(catalog_file, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2, ensure_ascii=False)
