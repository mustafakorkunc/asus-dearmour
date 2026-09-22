import unittest
from pathlib import Path
import tempfile
from asus_driver_extractor.core.extractor import ArchiveExtractor

class TestZip(unittest.TestCase):
    def test_zip_fail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            corrupt_zip = tmp_path / "corrupt.zip"
            with open(corrupt_zip, "wb") as f:
                f.write(b"garbage")

            extractor = ArchiveExtractor()
            extractor.tar_exe = None
            extractor.seven_zip = None
            extractor.expand_exe = None

            result = extractor.unpack_archive(corrupt_zip, tmp_path / "dest")
            print("Result:", result)

if __name__ == "__main__":
    unittest.main()
