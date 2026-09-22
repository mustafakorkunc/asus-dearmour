"""
Unit tests for Binary Stream Carving and Archive Extractor.
"""

import io
import tempfile
import unittest
import unittest.mock
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

    def test_unpack_archive_zipfile_exception_fallback(self):
        """Test that a failure in standard ZIP extraction falls through gracefully."""
        import unittest.mock
        with unittest.mock.patch("asus_driver_extractor.core.extractor.zipfile.ZipFile") as mock_zipfile:
            mock_zipfile.side_effect = Exception("Simulated ZIP failure")

            extractor = ArchiveExtractor()
            extractor.tar_exe = None
            extractor.seven_zip = None
            extractor.expand_exe = None

            dummy_zip = self.tmp_path / "corrupt.zip"
            dummy_zip.touch()

            dest_dir = self.tmp_path / "dest"
            result = extractor.unpack_archive(dummy_zip, dest_dir)

            self.assertFalse(result)
            mock_zipfile.assert_called_once()

    def test_safe_extract_zip_rejects_path_traversal(self):
        """Test that relative path traversal (../evil.exe) is rejected."""
        from asus_driver_extractor.core.extractor import ExtractionError
        extractor = ArchiveExtractor()

        zip_path = self.tmp_path / "traversal.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../evil.exe", "malicious payload")

        dest_dir = self.tmp_path / "unpacked_safe"
        with self.assertRaises(ExtractionError):
            extractor.unpack_archive(zip_path, dest_dir)

    def test_safe_extract_zip_rejects_backslash_traversal(self):
        """Test that Windows-style backslash traversal (..\\..\\evil.exe) is rejected."""
        from asus_driver_extractor.core.extractor import ExtractionError
        extractor = ArchiveExtractor()

        zip_path = self.tmp_path / "win_traversal.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("..\\..\\evil.exe", "malicious payload")

        dest_dir = self.tmp_path / "unpacked_safe"
        with self.assertRaises(ExtractionError):
            extractor.unpack_archive(zip_path, dest_dir)

    def test_safe_extract_zip_rejects_absolute_path(self):
        """Test that absolute paths are rejected."""
        from asus_driver_extractor.core.extractor import ExtractionError
        extractor = ArchiveExtractor()

        zip_path = self.tmp_path / "abs_traversal.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/passwd", "root:x:0:0")

        dest_dir = self.tmp_path / "unpacked_safe"
        with self.assertRaises(ExtractionError):
            extractor.unpack_archive(zip_path, dest_dir)

    def test_safe_extract_zip_allows_legitimate_nested_dirs(self):
        """Test that legitimate nested driver directory structures extract safely."""
        extractor = ArchiveExtractor()

        zip_path = self.tmp_path / "legit_nested.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("driver_pack/x64/subfolder/driver.inf", "[Version]\nClass=Net\n")
            zf.writestr("driver_pack/x64/subfolder/driver.sys", "valid driver binary")

        dest_dir = self.tmp_path / "unpacked_nested"
        success = extractor.unpack_archive(zip_path, dest_dir)
        self.assertTrue(success)
        self.assertTrue((dest_dir / "driver_pack" / "x64" / "subfolder" / "driver.inf").is_file())
        self.assertTrue((dest_dir / "driver_pack" / "x64" / "subfolder" / "driver.sys").is_file())

    @unittest.mock.patch("shutil.which")
    def test_find_system_tool_does_not_use_path(self, mock_which):
        """Test that finding system tools does not fall back to PATH via shutil.which."""
        mock_which.return_value = "malicious_path"

        result = ArchiveExtractor._find_system_tool("nonexistent_tool.exe")

        # Verify it returns None since it shouldn't exist in System32
        self.assertIsNone(result)
        # Verify shutil.which was not called
        mock_which.assert_not_called()

    @unittest.mock.patch("asus_driver_extractor.core.extractor.Path.is_file")
    @unittest.mock.patch("shutil.which")
    def test_find_seven_zip_does_not_use_path(self, mock_which, mock_is_file):
        """Test that finding 7-zip does not check PATH via shutil.which."""
        mock_which.return_value = "malicious_path"
        mock_is_file.return_value = False

        # In a test environment, mock these absolute paths to not exist, so it should return None
        result = ArchiveExtractor._find_seven_zip()

        self.assertIsNone(result)
        # Verify shutil.which was not called
        mock_which.assert_not_called()


if __name__ == "__main__":
    unittest.main()

