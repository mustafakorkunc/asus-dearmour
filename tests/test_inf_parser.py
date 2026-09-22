"""
Unit tests for Windows INF Parser and Driver Analyzer.
"""

import unittest
from pathlib import Path
import tempfile
from asus_driver_extractor.core.inf_parser import InfParser


class TestInfParser(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inf_parser_network(self):
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
ClassGUID={4d36e972-e325-11ce-bfc1-08002be10318}
Provider=%Realtek%
CatalogFile=rt68cx21x64.cat
DriverVer=07/17/2023,1168.015.0717.2023

[Manufacturer]
%Realtek% = Realtek, NTamd64.10.0

[Realtek.NTamd64.10.0]
%Realtek.DeviceDesc% = Realtek.ndi, PCI\\VEN_10EC&DEV_8168&SUBSYS_12341043

[SourceDisksFiles]
rt68cx21x64.sys = 1
rt68cx21x64.cat = 1

[Strings]
Realtek = "Realtek Semiconductor Corp."
Realtek.DeviceDesc = "Realtek Gaming GbE Family Controller"
"""
        inf_file = self.tmp_path / "test_net.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)

        self.assertEqual(meta.provider, "Realtek Semiconductor Corp.")
        self.assertEqual(meta.driver_class, "Net")
        self.assertEqual(meta.category, "Network_Ethernet")
        self.assertEqual(meta.driver_version, "1168.015.0717.2023")
        self.assertEqual(meta.driver_date, "07/17/2023")
        self.assertEqual(meta.catalog_file, "rt68cx21x64.cat")
        self.assertIn("rt68cx21x64.sys", meta.associated_files)
        self.assertTrue(any("PCI\\VEN_10EC" in hw for hw in meta.hardware_ids))

    def test_inf_parser_wireless_detection(self):
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider=%Company%
DriverVer=09/30/2025,6001.15.160.101

[Strings]
Company = "Realtek"
Device = "Realtek 8852BE Wireless LAN WiFi 6 PCI-E NIC"
"""
        inf_file = self.tmp_path / "test_wifi.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)

        self.assertEqual(meta.category, "Network_Wireless")
        self.assertEqual(meta.driver_version, "6001.15.160.101")

    def test_inf_parser_bluetooth(self):
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Bluetooth
Provider=%RTK%
DriverVer=02/07/2025,18.4028.2506.2301

[Strings]
RTK = "Realtek"
"""
        inf_file = self.tmp_path / "test_bt.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)

        self.assertEqual(meta.category, "Bluetooth")
        self.assertEqual(meta.driver_version, "18.4028.2506.2301")

    def test_inf_parser_quoted_semicolon_not_stripped(self):
        """Test that semicolons inside quoted string values are preserved and not stripped as comments."""
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="ACME; Networks Inc." ; EOL comment
DriverVer=01/01/2026,1.0.0
"""
        inf_file = self.tmp_path / "quoted_semicolon.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)
        self.assertEqual(meta.provider, "ACME; Networks Inc.")

    def test_inf_parser_line_continuation(self):
        """Test that lines ending with trailing backslash are joined properly."""
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="Test"
DriverVer=01/01/2026, \
          2.0.0.1
"""
        inf_file = self.tmp_path / "continuation.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)
        self.assertEqual(meta.driver_version, "2.0.0.1")

    def test_inf_parser_decorated_strings(self):
        """Test that decorated [Strings.0409] sections are collected and resolved."""
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider=%VendorName%
DriverVer=01/01/2026,3.0.0.1

[Strings.0409]
VendorName = "Realtek Corp Decorated"
"""
        inf_file = self.tmp_path / "decorated_strings.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)
        self.assertEqual(meta.provider, "Realtek Corp Decorated")

    def test_inf_parser_malformed_input_recovery(self):
        """Test that completely malformed input recovers gracefully without crashing."""
        inf_file = self.tmp_path / "malformed.inf"
        inf_file.write_text("random broken bytes !!! === ;;; [[[ [[not_a_valid_inf", encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)
        self.assertEqual(meta.inf_name, "malformed.inf")
        self.assertEqual(meta.provider, "Unknown")
        self.assertEqual(meta.category, "Other")

    def test_inf_associated_files_sanitization(self):
        """Test that path prefixes are stripped from associated files and duplicates ignored."""
        sample_inf = """
[Version]
Signature="$WINDOWS NT$"
Class=Net

[SourceDisksFiles]
x64\\my_driver.sys = 1
x86\\other_helper.dll = 1
malformed_line_without_equals

[CopyFiles]
x64\\my_driver.sys, sub\\extra.dat
"""
        inf_file = self.tmp_path / "assoc_files.inf"
        inf_file.write_text(sample_inf, encoding="utf-8")

        meta = InfParser.parse_inf(inf_file)
        self.assertIn("my_driver.sys", meta.associated_files)
        self.assertIn("other_helper.dll", meta.associated_files)
        self.assertIn("extra.dat", meta.associated_files)
        self.assertNotIn("malformed_line_without_equals", meta.associated_files)


if __name__ == "__main__":
    unittest.main()
