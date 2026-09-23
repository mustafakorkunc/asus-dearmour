"""
Unit tests for Command Line Interface functions.
"""

import unittest
import tempfile
from pathlib import Path
from asus_driver_extractor.cli import (
    collect_target_files,
    clean_output_directory,
    run_pipeline,
)


class TestCollectTargetFiles(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_file(self, path_relative, size_bytes=0):
        file_path = self.tmp_path / path_relative
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"0" * size_bytes)
        return file_path

    def test_single_exe_file(self):
        # Even if size is 0, passing specific file directly should return it
        file_path = self._create_file("installer.exe", size_bytes=10)
        result = collect_target_files(file_path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], file_path.resolve())

    def test_single_non_exe_file(self):
        file_path = self._create_file("installer.zip", size_bytes=10)
        result = collect_target_files(file_path)
        self.assertEqual(len(result), 0)

    def test_directory_non_recursive(self):
        # Create a mix of files
        large_exe = self._create_file("large.exe", size_bytes=100_001)
        small_exe = self._create_file("small.exe", size_bytes=50_000)
        large_txt = self._create_file("large.txt", size_bytes=200_000)
        subdir_exe = self._create_file("subdir/large_subdir.exe", size_bytes=150_000)

        result = collect_target_files(self.tmp_path, recursive=False)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], large_exe.resolve())

    def test_directory_recursive(self):
        # Create a mix of files
        large_exe = self._create_file("large.exe", size_bytes=100_001)
        small_exe = self._create_file("small.exe", size_bytes=50_000)
        large_txt = self._create_file("large.txt", size_bytes=200_000)
        subdir_exe = self._create_file("subdir/large_subdir.exe", size_bytes=150_000)

        result = collect_target_files(self.tmp_path, recursive=True)
        self.assertEqual(len(result), 2)
        resolved_results = set(r for r in result)
        self.assertIn(large_exe.resolve(), resolved_results)
        self.assertIn(subdir_exe.resolve(), resolved_results)

    def test_non_existent_path(self):
        non_existent = self.tmp_path / "does_not_exist.exe"
        result = collect_target_files(non_existent)
        self.assertEqual(len(result), 0)


class TestCleanOutputDirectory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_clean_output_directory_removes_contents(self):
        out_dir = self.tmp_path / "out"
        out_dir.mkdir()
        file1 = out_dir / "test.txt"
        file1.write_text("hello", encoding="utf-8")
        sub = out_dir / "subdir"
        sub.mkdir()
        (sub / "nested.bin").write_bytes(b"123")

        self.assertTrue(out_dir.exists())
        self.assertEqual(len(list(out_dir.iterdir())), 2)

        clean_output_directory(out_dir)

        self.assertTrue(out_dir.exists())
        self.assertEqual(list(out_dir.iterdir()), [])

    def test_clean_output_directory_protects_system_roots(self):
        home = Path.home()
        with self.assertRaises(ValueError):
            clean_output_directory(home)

        anchor = Path(home.anchor)
        with self.assertRaises(ValueError):
            clean_output_directory(anchor)


class TestRunPipelineOutputDirectory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_pipeline_refuses_non_empty_dir_by_default(self):
        out_dir = self.tmp_path / "out"
        out_dir.mkdir()
        stray_file = out_dir / "old_driver.inf"
        stray_file.write_text("[Version]", encoding="utf-8")

        with self.assertRaises(FileExistsError) as ctx:
            run_pipeline([], out_dir)

        self.assertIn("is not empty", str(ctx.exception))
        # Ensure files were not touched
        self.assertTrue(stray_file.exists())

    def test_run_pipeline_allows_overwrite(self):
        out_dir = self.tmp_path / "out"
        out_dir.mkdir()
        stray_file = out_dir / "old_driver.inf"
        stray_file.write_text("[Version]", encoding="utf-8")

        res = run_pipeline([], out_dir, overwrite=True)
        self.assertEqual(res, [])
        self.assertTrue(out_dir.exists())
        self.assertFalse(stray_file.exists())
        self.assertEqual(list(out_dir.iterdir()), [])

    def test_run_pipeline_allows_merge(self):
        out_dir = self.tmp_path / "out"
        out_dir.mkdir()
        stray_file = out_dir / "old_driver.inf"
        stray_file.write_text("[Version]", encoding="utf-8")

        res = run_pipeline([], out_dir, merge=True)
        self.assertEqual(res, [])
        self.assertTrue(out_dir.exists())
        self.assertTrue(stray_file.exists())

    def test_run_pipeline_creates_non_existent_dir(self):
        out_dir = self.tmp_path / "new_dir"
        self.assertFalse(out_dir.exists())

        res = run_pipeline([], out_dir)
        self.assertEqual(res, [])
        self.assertTrue(out_dir.exists())


if __name__ == "__main__":
    unittest.main()
