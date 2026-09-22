with open('tests/test_extractor.py', 'r') as f:
    lines = f.readlines()

out = []
in_main = False
for line in lines:
    if line.strip() == "if __name__ == \"__main__\":":
        in_main = True
        break
    out.append(line)

out.append("""    @unittest.mock.patch("asus_driver_extractor.core.extractor.zipfile.ZipFile")
    def test_unpack_archive_zipfile_exception_fallback(self, mock_zipfile):
        \"\"\"Test that a failure in standard ZIP extraction falls through gracefully.\"\"\"
        mock_zipfile.side_effect = Exception("Simulated ZIP failure")

        extractor = ArchiveExtractor()

        # Disable fallback extractors to ensure we just return False at the end
        extractor.tar_exe = None
        extractor.seven_zip = None
        extractor.expand_exe = None

        dummy_zip = self.tmp_path / "corrupt.zip"
        dummy_zip.touch()

        dest_dir = self.tmp_path / "dest"

        result = extractor.unpack_archive(dummy_zip, dest_dir)

        # It should catch the exception, skip to next methods, and eventually return False
        self.assertFalse(result)
        mock_zipfile.assert_called_once()

if __name__ == "__main__":
    unittest.main()
""")

with open('tests/test_extractor.py', 'w') as f:
    f.writelines(out)
