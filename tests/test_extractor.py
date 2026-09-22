"""
Unit tests for Binary Stream Carving and Archive Extractor.
"""

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from asus_driver_extractor.core.extractor import ArchiveExtractor


class TestArchiveExtractor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_carve_zip_from_mock_pe(self):
        extractor = ArchiveExtractor()

        # Create dummy in-memory zip
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("test_driver.inf", "[Version]\nClass=Net\n")
        zip_bytes = zip_buffer.getvalue()

        # Prepend dummy PE header bytes (e.g. 4KB of data)
        dummy_exe = self.tmp_path / "dummy_installer.exe"
        with open(dummy_exe, "wb") as f:
            f.write(b"MZ" + b"\x00" * 4096 + b"PE\x00\x00" + b"\x90" * 2048)
            f.write(zip_bytes)

        out_carve = self.tmp_path / "carved"
        out_carve.mkdir()
        carved = extractor.carve_embedded_archives(dummy_exe, out_carve)

        self.assertGreaterEqual(len(carved), 1)
        arch_type, carved_file = carved[0]
        self.assertEqual(arch_type, "zip")
        self.assertTrue(carved_file.is_file())

        # Test unpacking
        unpacked_dir = self.tmp_path / "unpacked"
        success = extractor.unpack_archive(carved_file, unpacked_dir)
        self.assertTrue(success)
        self.assertTrue((unpacked_dir / "test_driver.inf").is_file())


if __name__ == "__main__":
    unittest.main()
