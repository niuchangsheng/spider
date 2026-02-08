"""
Storage 单元测试（使用临时 SQLite）
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from config import config
from core.storage import Storage


class TestStorageConnect(unittest.TestCase):
    """Storage.connect 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path

    def tearDown(self):
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_connect_creates_db(self):
        """connect 创建数据库文件"""
        config.database.sqlite_path = self.db_path
        storage = Storage()
        storage.connect()
        try:
            self.assertTrue(self.db_path.exists())
            self.assertIsNotNone(storage._conn)
        finally:
            storage.close()


class TestStorageCheckpoint(unittest.TestCase):
    """Storage 检查点读写测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_and_load_checkpoint(self):
        """保存并加载检查点"""
        self.storage.save_checkpoint(
            "test.com",
            "board1",
            {
                "current_page": 3,
                "last_thread_id": "123",
                "last_thread_url": "https://test.com/t/123",
                "status": "running",
                "stats": {"crawled": 10},
            },
        )
        row = self.storage.load_checkpoint("test.com", "board1")
        self.assertIsNotNone(row)
        self.assertEqual(row["current_page"], 3)
        self.assertEqual(row["last_thread_id"], "123")
        self.assertEqual(row["status"], "running")

    def test_load_checkpoint_nonexistent_returns_none(self):
        """不存在的检查点返回 None"""
        row = self.storage.load_checkpoint("nonexistent.com", "board")
        self.assertIsNone(row)

    def test_delete_checkpoint(self):
        """删除检查点"""
        self.storage.save_checkpoint(
            "del.com", "b1",
            {"current_page": 1, "last_thread_id": "", "last_thread_url": "", "status": "running", "stats": {}},
        )
        self.storage.delete_checkpoint("del.com", "b1")
        row = self.storage.load_checkpoint("del.com", "b1")
        self.assertIsNone(row)


class TestStorageThreadExists(unittest.TestCase):
    """Storage thread_exists 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_thread_exists_after_save(self):
        """保存帖子后 thread_exists 为 True"""
        self.storage.save_thread({
            "thread_id": "t1",
            "title": "Title",
            "url": "https://test.com/t1",
            "board": "b1",
            "images": [],
            "image_count": 0,
            "metadata": {},
        })
        self.assertTrue(self.storage.thread_exists("t1"))

    def test_thread_exists_false_when_not_saved(self):
        """未保存的 thread_id 返回 False"""
        self.assertFalse(self.storage.thread_exists("nonexistent_tid"))


class TestStorageSaveImageRecord(unittest.TestCase):
    """Storage save_image_record / get_thread 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_image_record(self):
        """保存图片记录"""
        ok = self.storage.save_image_record({
            "url": "https://test.com/img.jpg",
            "save_path": "/downloads/img.jpg",
            "file_size": 1024,
            "success": True,
            "metadata": {},
        })
        self.assertTrue(ok)

    def test_get_thread_after_save(self):
        """保存帖子后可 get_thread"""
        self.storage.save_thread({
            "thread_id": "t99",
            "title": "Title99",
            "url": "https://test.com/t99",
            "board": "b1",
            "images": ["https://a.com/1.jpg"],
            "image_count": 1,
            "metadata": {},
        })
        row = self.storage.get_thread("t99")
        self.assertIsNotNone(row)
        self.assertEqual(row.get("thread_id"), "t99")
        self.assertEqual(row.get("title"), "Title99")


class TestStorageGetAllThreadsAndStats(unittest.TestCase):
    """Storage get_all_threads / get_statistics 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_get_all_threads_empty(self):
        self.assertEqual(self.storage.get_all_threads(), [])

    def test_get_all_threads_by_board(self):
        self.storage.save_thread({
            "thread_id": "a1", "title": "A", "url": "https://x/a1", "board": "b1",
            "images": [], "image_count": 0, "metadata": {},
        })
        self.storage.save_thread({
            "thread_id": "a2", "title": "B", "url": "https://x/a2", "board": "b2",
            "images": [], "image_count": 0, "metadata": {},
        })
        rows = self.storage.get_all_threads("b1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["thread_id"], "a1")
        all_rows = self.storage.get_all_threads()
        self.assertEqual(len(all_rows), 2)

    def test_get_statistics(self):
        self.storage.save_thread({
            "thread_id": "s1", "title": "S", "url": "https://x/s1", "board": "b1",
            "images": [], "image_count": 0, "metadata": {},
        })
        stats = self.storage.get_statistics()
        self.assertIn("total_threads", stats)
        self.assertIn("total_images", stats)
        self.assertIn("boards", stats)
        self.assertEqual(stats["total_threads"], 1)


class TestStorageArticle(unittest.TestCase):
    """Storage article_exists / save_article 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_article_exists_false_when_empty(self):
        self.assertFalse(self.storage.article_exists("art1"))

    def test_save_article_and_exists(self):
        ok = self.storage.save_article({
            "article_id": "art1",
            "url": "https://news.com/1",
            "title": "News Title",
            "site": "news.com",
            "board": "",
            "metadata": {},
            "images_downloaded": True,
        })
        self.assertTrue(ok)
        self.assertTrue(self.storage.article_exists("art1"))


class TestStorageVisitedAndQueue(unittest.TestCase):
    """Storage is_url_visited / mark_url_visited / add_to_queue / get_from_queue / get_queue_size / clear_queue 测试"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        self.storage.connect()

    def tearDown(self):
        self.storage.close()
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mark_and_is_url_visited(self):
        self.assertFalse(self.storage.is_url_visited("https://x.com/1"))
        self.storage.mark_url_visited("https://x.com/1")
        self.assertTrue(self.storage.is_url_visited("https://x.com/1"))

    def test_add_to_queue_get_from_queue(self):
        self.assertTrue(self.storage.add_to_queue("q1", {"id": 1}))
        self.assertEqual(self.storage.get_queue_size("q1"), 1)
        item = self.storage.get_from_queue("q1")
        self.assertEqual(item, {"id": 1})
        self.assertEqual(self.storage.get_queue_size("q1"), 0)
        self.assertIsNone(self.storage.get_from_queue("q1"))

    def test_clear_queue(self):
        self.storage.add_to_queue("q2", "a")
        self.storage.clear_queue("q2")
        self.assertEqual(self.storage.get_queue_size("q2"), 0)
        self.assertIsNone(self.storage.get_from_queue("q2"))
