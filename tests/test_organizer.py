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

    def test_organize_multiple_infs_in_same_folder(self):
        """Test organizing a folder containing multiple distinct INF files."""
        driver_folder = self.staging_dir / "dual_driver"
        driver_folder.mkdir(parents=True, exist_ok=True)

        inf_content_1 = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="VendorAlpha"
DriverVer=01/01/2026,1.0.0.1
"""
        inf_content_2 = """
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="VendorAlpha"
DriverVer=01/01/2026,2.0.0.1
"""
        (driver_folder / "net1.inf").write_text(inf_content_1, encoding="utf-8")
        (driver_folder / "net2.inf").write_text(inf_content_2, encoding="utf-8")
        (driver_folder / "common.sys").write_text("dummy payload")

        organizer = DriverOrganizer(self.output_dir)
        organized = organizer.organize_extracted_pool(self.staging_dir)

        # Both drivers should be cataloged and organized
        self.assertEqual(len(organized), 2)
        inf_names = {m.inf_name for m in organized}
        self.assertEqual(inf_names, {"net1.inf", "net2.inf"})

        # Target folder should contain install/uninstall scripts and manifests for both
        dest_folder = self.output_dir / "Network_Ethernet" / "VendorAlpha_net1_v1001"
        self.assertTrue(dest_folder.is_dir())
        self.assertTrue((dest_folder / "install.bat").is_file())
        self.assertTrue((dest_folder / "uninstall.bat").is_file())
        self.assertTrue((dest_folder / "driver_manifest.json").is_file())

        self.assertTrue((dest_folder / "install_net2.bat").is_file())
        self.assertTrue((dest_folder / "uninstall_net2.bat").is_file())
        self.assertTrue((dest_folder / "driver_manifest_net2.json").is_file())

    def test_organize_preserves_legitimate_payload_files(self):
        """Test that diverse payload files (.dll, .bin, .ini, subdirs) are preserved."""
        driver_folder = self.staging_dir / "rich_payload"
        driver_folder.mkdir(parents=True, exist_ok=True)

        inf_content = """
[Version]
Signature="$WINDOWS NT$"
Class=Media
Provider="AudioCorp"
DriverVer=05/10/2025,6.0.1.100
"""
        (driver_folder / "audio.inf").write_text(inf_content, encoding="utf-8")
        (driver_folder / "audio.sys").write_text("sys")
        (driver_folder / "dsp_firmware.bin").write_text("firmware")
        (driver_folder / "settings.ini").write_text("[Audio]\nSampleRate=48000")
        (driver_folder / "helper.dll").write_text("dll")

        sub_folder = driver_folder / "x64"
        sub_folder.mkdir()
        (sub_folder / "processing.dll").write_text("64-bit dll")

        organizer = DriverOrganizer(self.output_dir)
        organized = organizer.organize_extracted_pool(self.staging_dir)

        self.assertEqual(len(organized), 1)
        target_dir = self.output_dir / "Audio" / "AudioCorp_audio_v601100"
        self.assertTrue((target_dir / "dsp_firmware.bin").is_file())
        self.assertTrue((target_dir / "settings.ini").is_file())
        self.assertTrue((target_dir / "helper.dll").is_file())
        self.assertTrue((target_dir / "x64" / "processing.dll").is_file())

    def test_organize_handles_corrupted_inf_gracefully(self):
        """Test that an unparseable or broken INF does not crash the entire pool organization."""
        good_folder = self.staging_dir / "good_driver"
        good_folder.mkdir(parents=True, exist_ok=True)
        (good_folder / "good.inf").write_text("""
[Version]
Signature="$WINDOWS NT$"
Class=Net
Provider="GoodVendor"
DriverVer=01/01/2026,1.0
""", encoding="utf-8")
        (good_folder / "good.sys").write_text("good")

        bad_folder = self.staging_dir / "bad_driver"
        bad_folder.mkdir(parents=True, exist_ok=True)
        # Write corrupted byte sequence that might cause parser failure
        (bad_folder / "broken.inf").write_bytes(b"\x00\xff\xfe\xaa\xbb\xcc\xdd\xee")

        organizer = DriverOrganizer(self.output_dir)
        organized = organizer.organize_extracted_pool(self.staging_dir)

        # The good driver must succeed regardless of the broken one
        self.assertTrue(any(d.inf_name == "good.inf" for d in organized))


if __name__ == "__main__":
    unittest.main()

