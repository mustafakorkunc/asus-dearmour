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


if __name__ == "__main__":
    unittest.main()
