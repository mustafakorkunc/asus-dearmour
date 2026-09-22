"""
Unit tests for Deployment Script Generator.
"""

import json
import tempfile
import unittest
from pathlib import Path

from asus_driver_extractor.core.script_generator import MasterScriptGenerator
from asus_driver_extractor.core.inf_parser import DriverMetadata


class TestMasterScriptGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_root = Path(self.temp_dir.name)

        # Mock driver data
        self.mock_drivers = [
            DriverMetadata(
                inf_path=Path("dummy_path/driver1.inf"),
                inf_name="driver1.inf",
                provider="Intel",
                driver_class="Net",
                category="Network_Ethernet",
                driver_version="1.0.0.1"
            ),
            DriverMetadata(
                inf_path=Path("dummy_path/driver2.inf"),
                inf_name="driver2.inf",
                provider="Realtek",
                driver_class="Media",
                category="Audio",
                driver_version="2.0.0.1"
            )
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_scripts_creates_files(self):
        """Test that the generator creates the expected script files and catalog."""
        MasterScriptGenerator.generate_scripts(self.output_root, self.mock_drivers)

        bat_file = self.output_root / "INSTALL_ALL_DRIVERS.bat"
        ps1_file = self.output_root / "INSTALL_ALL_DRIVERS.ps1"
        catalog_file = self.output_root / "drivers_catalog.json"

        # Assert files are created
        self.assertTrue(bat_file.exists())
        self.assertTrue(ps1_file.exists())
        self.assertTrue(catalog_file.exists())

    def test_generate_scripts_bat_content(self):
        """Test that the batch script contains the correct content."""
        MasterScriptGenerator.generate_scripts(self.output_root, self.mock_drivers)
        bat_file = self.output_root / "INSTALL_ALL_DRIVERS.bat"
        content = bat_file.read_text(encoding="utf-8")

        self.assertIn("pnputil /add-driver", content)
        self.assertIn("ADMINISTRATOR PRIVILEGES REQUIRED", content)
        self.assertIn("DeArmour - BATCH DRIVER DEPLOYMENT", content)

    def test_generate_scripts_ps1_content(self):
        """Test that the powershell script contains the correct content."""
        MasterScriptGenerator.generate_scripts(self.output_root, self.mock_drivers)
        ps1_file = self.output_root / "INSTALL_ALL_DRIVERS.ps1"
        content = ps1_file.read_text(encoding="utf-8")

        self.assertIn("pnputil", content)
        self.assertIn("Administrator privileges", content)
        self.assertIn("DeArmour - BATCH DRIVER DEPLOYMENT", content)

    def test_generate_scripts_catalog_content(self):
        """Test that the JSON catalog contains correct metadata."""
        MasterScriptGenerator.generate_scripts(self.output_root, self.mock_drivers)
        catalog_file = self.output_root / "drivers_catalog.json"

        with open(catalog_file, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        self.assertEqual(catalog_data["total_drivers"], 2)
        self.assertEqual(catalog_data["categories"], sorted(["Audio", "Network_Ethernet"]))

        drivers = catalog_data["drivers"]
        self.assertEqual(len(drivers), 2)

        # Check first driver
        self.assertEqual(drivers[0]["inf_name"], "driver1.inf")
        self.assertEqual(drivers[0]["provider"], "Intel")
        self.assertEqual(drivers[0]["category"], "Network_Ethernet")
        self.assertEqual(drivers[0]["driver_version"], "1.0.0.1")

        # Check second driver
        self.assertEqual(drivers[1]["inf_name"], "driver2.inf")
        self.assertEqual(drivers[1]["provider"], "Realtek")
        self.assertEqual(drivers[1]["category"], "Audio")
        self.assertEqual(drivers[1]["driver_version"], "2.0.0.1")

if __name__ == "__main__":
    unittest.main()
