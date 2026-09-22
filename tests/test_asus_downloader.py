"""
Unit tests for AsusDownloader interface and hardware detection.
"""

import io
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from asus_driver_extractor.core.asus_downloader import AsusDownloader, AsusDriverPackage


class TestAsusDownloader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_default_dir(self):
        """Test default download directory initialization."""
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

    def test_detect_local_system(self):
        """Test hardware detection returns valid dictionary structure."""
        info = AsusDownloader.detect_local_system()
        self.assertIn("model", info)
        self.assertIn("os_name", info)
        self.assertIn("osid", info)
        self.assertIn("is_asus", info)
        self.assertTrue(len(info["model"]) > 0)

    def test_search_model(self):
        """Test search_model returns formatted result."""
        downloader = AsusDownloader(download_dir=self.tmp_path)
        result = downloader.search_model("fa506nc")
        self.assertEqual(result, [{"model": "FA506NC", "status": "ASUS Support API Ready"}])

    @patch('urllib.request.urlopen')
    def test_fetch_driver_list(self, mock_urlopen):
        """Test fetch_driver_list parses ASUS REST API JSON correctly."""
        mock_response = MagicMock()
        mock_payload = {
            "Result": {
                "Count": 2,
                "Obj": [
                    {
                        "Name": "Networking",
                        "Files": [
                            {
                                "Title": "Realtek WLAN Driver",
                                "Version": "V1.0.0",
                                "ReleaseDate": "2024/01/01",
                                "FileSize": "10 MB",
                                "Description": "Wireless driver",
                                "DownloadUrl": {
                                    "Global": "https://dlcdnets.asus.com/pub/ASUS/WLAN.exe"
                                }
                            },
                            {
                                "Title": "Store App",
                                "DownloadUrl": {
                                    "Global": "https://www.microsoft.com/store/apps/12345"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        mock_response.read.return_value = json.dumps(mock_payload).encode('utf-8')
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        downloader = AsusDownloader(download_dir=self.tmp_path)
        packages = downloader.fetch_driver_list("FA506NC")

        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0].title, "Realtek WLAN Driver")
        self.assertEqual(packages[0].category, "Networking")
        self.assertEqual(packages[0].version, "V1.0.0")
        self.assertEqual(packages[0].filename, "WLAN.exe")

    @patch('urllib.request.urlopen')
    def test_download_package(self, mock_urlopen):
        """Test streaming download of a package."""
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "12"
        mock_response.read.side_effect = [b"driver_bytes", b""]
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        downloader = AsusDownloader(download_dir=self.tmp_path)
        package = AsusDriverPackage(
            title="WLAN Driver",
            category="Networking",
            version="1.0.0",
            release_date="2024-01-01",
            download_url="https://dlcdnets.asus.com/pub/ASUS/GamingNB/FA506NC/WLAN_Driver.exe"
        )

        progress_calls = []
        def on_progress(written, total):
            progress_calls.append((written, total))

        result_path = downloader.download_package(package, progress_callback=on_progress)

        expected_path = self.tmp_path / "WLAN_Driver.exe"
        self.assertEqual(result_path, expected_path)
        self.assertTrue(result_path.is_file())
        self.assertEqual(result_path.read_bytes(), b"driver_bytes")
        self.assertGreaterEqual(len(progress_calls), 1)


if __name__ == "__main__":
    unittest.main()
