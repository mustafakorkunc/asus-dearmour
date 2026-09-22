"""
Unit tests for AsusDownloader interface.
"""

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from asus_driver_extractor.core.asus_downloader import AsusDownloader, AsusDriverPackage


class TestAsusDownloader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_default_dir(self):
        """Test default download directory initialization."""
        # We patch Path.home() so it returns our temp dir
        with patch('asus_driver_extractor.core.asus_downloader.Path.home') as mock_home:
            mock_home.return_value = self.tmp_path

            downloader = AsusDownloader()

            expected_dir = self.tmp_path / "Downloads" / "AsusDrivers"
            self.assertEqual(downloader.download_dir, expected_dir)
            self.assertTrue(expected_dir.is_dir())

    def test_init_custom_dir(self):
        """Test custom download directory initialization."""
        custom_dir = self.tmp_path / "CustomDrivers"
        downloader = AsusDownloader(download_dir=custom_dir)

        self.assertEqual(downloader.download_dir, custom_dir)
        self.assertTrue(custom_dir.is_dir())

    def test_search_model(self):
        """Test search_model stub."""
        downloader = AsusDownloader(download_dir=self.tmp_path)
        model_name = "FA506NC"
        result = downloader.search_model(model_name)

        expected_result = [{"model": model_name, "status": "Ready for ASUS API link"}]
        self.assertEqual(result, expected_result)

    def test_fetch_driver_list(self):
        """Test fetch_driver_list stub."""
        downloader = AsusDownloader(download_dir=self.tmp_path)
        result = downloader.fetch_driver_list("GA402RJ")

        self.assertEqual(result, [])

    def test_download_package(self):
        """Test download_package stub."""
        downloader = AsusDownloader(download_dir=self.tmp_path)
        package = AsusDriverPackage(
            title="WLAN Driver",
            category="Networking",
            version="1.0.0",
            release_date="2023-01-01",
            download_url="https://dlcdnets.asus.com/pub/ASUS/GamingNB/FA506NC/WLAN_Driver.exe"
        )

        expected_path = self.tmp_path / "WLAN_Driver.exe"
        result_path = downloader.download_package(package)

        self.assertEqual(result_path, expected_path)

if __name__ == "__main__":
    unittest.main()
