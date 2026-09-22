import unittest
import tempfile
from pathlib import Path
from asus_driver_extractor.core.organizer import DriverOrganizer


class TestDriverOrganizer(unittest.TestCase):

    def setUp(self):
        self.staging_temp = tempfile.TemporaryDirectory()
        self.output_temp = tempfile.TemporaryDirectory()
        self.staging_dir = Path(self.staging_temp.name)
        self.output_dir = Path(self.output_temp.name)

    def tearDown(self):
        self.staging_temp.cleanup()
        self.output_temp.cleanup()

    def test_organize_extracted_pool(self):
        # 1. Setup mock driver folder and dummy files
        driver_folder = self.staging_dir / "mock_driver"
        driver_folder.mkdir(parents=True, exist_ok=True)

        inf_content = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="TestProvider"
DriverVer=09/30/2025,1.2.3.4
"""
        inf_file = driver_folder / "test_driver.inf"
        inf_file.write_text(inf_content, encoding="utf-8")

        # Valid payload file
        sys_file = driver_folder / "driver.sys"
        sys_file.write_text("dummy driver data")

        # Excluded bloat files
        setup_exe = driver_folder / "setup.exe"
        setup_exe.write_text("dummy setup")
        install_tmp = driver_folder / "install.tmp"
        install_tmp.write_text("dummy tmp")

        # Excluded directory starting with Setup_
        setup_dir = driver_folder / "Setup_Files"
        setup_dir.mkdir()
        (setup_dir / "somefile.txt").write_text("should be excluded")

        # Excluded directory starting with _
        internal_dir = driver_folder / "_internal"
        internal_dir.mkdir()
        (internal_dir / "somefile.txt").write_text("should be excluded")

        # 2. Run organizer
        organizer = DriverOrganizer(self.output_dir)
        organized = organizer.organize_extracted_pool(self.staging_dir)

        # 3. Assertions
        self.assertEqual(len(organized), 1)
        meta = organized[0]
        self.assertEqual(meta.provider, "TestProvider")
        self.assertEqual(meta.driver_version, "1.2.3.4")
        self.assertEqual(meta.category, "Network_Ethernet")  # Fallback logic in InfParser based on "Net"

        # Predict the output folder path
        expected_output_folder = self.output_dir / "Network_Ethernet" / "TestProvider_test_driver_v1234"
        self.assertTrue(expected_output_folder.is_dir())

        # Payload files should be copied
        self.assertTrue((expected_output_folder / "driver.sys").is_file())

        # Bloatware files should not be copied
        self.assertFalse((expected_output_folder / "setup.exe").exists())
        self.assertFalse((expected_output_folder / "install.tmp").exists())
        self.assertFalse((expected_output_folder / "Setup_Files").exists())
        self.assertFalse((expected_output_folder / "_internal").exists())

        # Auto-generated files should exist
        self.assertTrue((expected_output_folder / "driver_manifest.json").is_file())
        self.assertTrue((expected_output_folder / "install.bat").is_file())
        self.assertTrue((expected_output_folder / "uninstall.bat").is_file())


if __name__ == "__main__":
    unittest.main()
