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
title ASUS Çıkarılmış Sürücüleri Toplu Kurulum Aracı
cd /d "%~dp0"

:: Yönetici Yetkisi Kontrolü
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ========================================================
    echo   YÖNETİCİ HAKLARI GEREKİYOR...
    echo   Yönetici onayı penceresi açılıyor, lütfen "Evet" deyin.
    echo ========================================================
    powershell -Command "Start-Process cmd -ArgumentList '/c `\"%~f0`\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   ASUS AYIKLANMIŞ SÜRÜCÜLER TOPLU KURULUM
echo   Hedef: Windows Sürücü Deposu (pnputil)
echo ========================================================
echo.

setlocal enabledelayedexpansion
set SUCCESS_COUNT=0
set FAIL_COUNT=0

echo [*] Sürücüler taranıyor ve sisteme yükleniyor...
echo.

pnputil /add-driver "%~dp0*.inf" /subdirs /install
set ERR=%errorlevel%

echo.
echo ========================================================
if %ERR% equ 0 (
    echo   [BAŞARILI] Bütün sürücüler sorunsuz yüklendi!
) else if %ERR% equ 3010 (
    echo   [BAŞARILI] Sürücüler yüklendi! Lütfen bilgisayarınızı yeniden başlatın.
) else (
    echo   [BİLGİ] İşlem tamamlandı. Sonuç kodu: %ERR%
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
        content = r"""# Toplu Sürücü Kurulum Betiği (PowerShell)
# Administrator yetkisi ile çalıştırılmalıdır.

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[!] Bu işlem Yönetici yetkisi gerektirir. Yönetici olarak yeniden başlatılıyor..." -ForegroundColor Yellow
    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ASUS AYIKLANMIŞ SÜRÜCÜLER TOPLU KURULUM (PowerShell)   " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$infFiles = Get-ChildItem -Path $PSScriptRoot -Filter "*.inf" -Recurse
Write-Host "[*] Bulunan toplam INF sürücü paketi: $($infFiles.Count)" -ForegroundColor Green

foreach ($inf in $infFiles) {
    Write-Host "[+] Kuruluyor: $($inf.Name) ($($inf.Directory.Name))..." -ForegroundColor White
    $res = Start-Process pnputil -ArgumentList "/add-driver `"$($inf.FullName)`" /install" -Wait -PassThru -NoNewWindow
    if ($res.ExitCode -eq 0 -or $res.ExitCode -eq 3010) {
        Write-Host "    -> Başarılı (Kod: $($res.ExitCode))" -ForegroundColor Green
    } else {
        Write-Host "    -> Uyarı / Hata (Kod: $($res.ExitCode))" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  TÜM SÜRÜCÜ KURULUMLARI TAMAMLANDI!                    " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Read-Host "Devam etmek için Enter tuşuna basın"
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
