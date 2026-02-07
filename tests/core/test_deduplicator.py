"""
ImageDeduplicator 单元测试
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from PIL import Image
from core.deduplicator import ImageDeduplicator


def _create_temp_image(path, size=(10, 10)):
    img = Image.new("RGB", size, color="red")
    img.save(path, "PNG")


class TestImageDeduplicatorUrl(unittest.TestCase):
    def test_is_duplicate_url_first_time_false(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        self.assertFalse(d.is_duplicate_url("https://example.com/1.jpg"))

    def test_is_duplicate_url_second_time_true(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.is_duplicate_url("https://example.com/1.jpg")
        self.assertTrue(d.is_duplicate_url("https://example.com/1.jpg"))

    def test_stats_updated(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.is_duplicate_url("https://a.com/1.jpg")
        d.is_duplicate_url("https://a.com/1.jpg")
        stats = d.get_stats()
        self.assertEqual(stats["total_checked"], 2)
        self.assertEqual(stats["duplicates_found"], 1)
        self.assertEqual(stats["duplicate_rate"], 0.5)


class TestImageDeduplicatorFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_is_duplicate_file_first_false(self):
        p = self.tmp_path / "a.png"
        _create_temp_image(p)
        d = ImageDeduplicator(use_perceptual_hash=False)
        self.assertFalse(d.is_duplicate_file(p))

    def test_is_duplicate_file_same_content_true(self):
        p = self.tmp_path / "a.png"
        _create_temp_image(p)
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.is_duplicate_file(p)
        self.assertTrue(d.is_duplicate_file(p))

    def test_is_duplicate_file_nonexistent_returns_false(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        self.assertFalse(d.is_duplicate_file(self.tmp_path / "nonexistent.png"))


class TestImageDeduplicatorLoadHashes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_existing_hashes(self):
        _create_temp_image(self.tmp_path / "img1.png")
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.load_existing_hashes(self.tmp_path)
        self.assertGreaterEqual(len(d.file_hashes), 1)

    def test_load_nonexistent_dir_no_error(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.load_existing_hashes(Path("/nonexistent/dir/xyz"))


class TestImageDeduplicatorClear(unittest.TestCase):
    def test_clear_resets_state(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        d.is_duplicate_url("https://a.com/1.jpg")
        d.clear()
        self.assertFalse(d.is_duplicate_url("https://a.com/1.jpg"))


class TestImageDeduplicatorGetStats(unittest.TestCase):
    def test_get_stats_empty_duplicate_rate_zero(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        stats = d.get_stats()
        self.assertEqual(stats["duplicate_rate"], 0.0)
        self.assertEqual(stats["total_checked"], 0)


class TestImageDeduplicatorPerceptualHash(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_perceptual_duplicate_same_image(self):
        p = self.tmp_path / "a.png"
        _create_temp_image(p)
        d = ImageDeduplicator(use_perceptual_hash=True)
        d.is_duplicate_file(p)
        self.assertTrue(d.is_duplicate_file(p))


class TestImageDeduplicatorRemoveFile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tmp_path = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_remove_existing_file(self):
        p = self.tmp_path / "a.png"
        _create_temp_image(p)
        d = ImageDeduplicator(use_perceptual_hash=False)
        self.assertTrue(d.remove_duplicate_file(p))
        self.assertFalse(p.exists())

    def test_remove_nonexistent_returns_false(self):
        d = ImageDeduplicator(use_perceptual_hash=False)
        self.assertFalse(d.remove_duplicate_file(self.tmp_path / "nonexistent.png"))
