"""
Storage 单元测试（使用临时 SQLite）
"""
import unittest
import tempfile
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import config
from core.storage import Storage, _serialize, _deserialize_json


class TestStorageSerializeHelpers(unittest.TestCase):
    """_serialize / _deserialize_json 辅助函数"""

    def test_serialize_none_returns_null(self):
        self.assertEqual(_serialize(None), "null")

    def test_serialize_dict_returns_json(self):
        self.assertEqual(_serialize({"a": 1}), '{"a": 1}')

    def test_serialize_non_dict_returns_str(self):
        self.assertEqual(_serialize(42), "42")

    def test_deserialize_null_returns_none(self):
        self.assertIsNone(_deserialize_json(None))
        self.assertIsNone(_deserialize_json("null"))

    def test_deserialize_invalid_json_returns_none(self):
        self.assertIsNone(_deserialize_json("not json"))


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

    def test_connect_failure_sets_conn_none(self):
        """connect 时 sqlite 异常则 _conn 为 None"""
        import unittest.mock as mock
        config.database.sqlite_path = self.db_path
        storage = Storage()
        with mock.patch("sqlite3.connect", side_effect=sqlite3.Error("fail")):
            storage.connect()
        self.assertIsNone(storage._conn)

    def test_unconnected_returns_empty_or_false(self):
        """未 connect 时 get_statistics/get_all_threads 返回空，article_exists/save_article 为 False"""
        config.database.sqlite_path = self.db_path
        storage = Storage()
        # 不调用 connect
        self.assertEqual(storage.get_statistics(), {})
        self.assertEqual(storage.get_all_threads(), [])
        self.assertEqual(storage.get_all_threads("b1"), [])
        self.assertFalse(storage.article_exists("art1"))
        self.assertFalse(storage.save_article({"article_id": "art1", "url": "https://x", "title": "T", "site": "x", "board": "", "metadata": {}}))
        self.assertIsNone(storage.get_thread("t1"))
        self.assertFalse(storage.thread_exists("t1"))

    def test_unconnected_save_thread_and_save_image_return_false(self):
        """未 connect 时 save_thread / save_image_record 返回 False"""
        config.database.sqlite_path = self.db_path
        storage = Storage()
        self.assertFalse(storage.save_thread({
            "thread_id": "t1", "title": "T", "url": "https://x", "board": "b1",
            "images": [], "image_count": 0, "metadata": {},
        }))
        self.assertFalse(storage.save_image_record({
            "url": "https://x/img.jpg", "save_path": "/x.jpg", "file_size": 0,
            "success": True, "metadata": {},
        }))


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

    def test_save_thread_with_datetime_created_at(self):
        """save_thread 支持 datetime 类型 created_at"""
        ok = self.storage.save_thread({
            "thread_id": "t2",
            "title": "T2",
            "url": "https://test.com/t2",
            "board": "b1",
            "images": [],
            "image_count": 0,
            "metadata": {},
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
        })
        self.assertTrue(ok)
        self.assertTrue(self.storage.thread_exists("t2"))

    def test_save_thread_sqlite_error_returns_false(self):
        """save_thread 时 SQL 异常返回 False"""
        import unittest.mock as mock
        fake_conn = mock.MagicMock()
        fake_conn.execute.side_effect = sqlite3.Error("db err")
        fake_conn.commit = mock.MagicMock()
        with mock.patch.object(self.storage, "_conn", fake_conn):
            ok = self.storage.save_thread({
                "thread_id": "terr",
                "title": "T",
                "url": "https://x/terr",
                "board": "b1",
                "images": [],
                "image_count": 0,
                "metadata": {},
            })
        self.assertFalse(ok)

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

    def test_save_image_record_with_path_and_created_at(self):
        """save_image_record 支持 Path 类型 save_path 和 datetime created_at"""
        ok = self.storage.save_image_record({
            "url": "https://test.com/img2.jpg",
            "save_path": Path("/downloads/img2.jpg"),
            "file_size": 2048,
            "success": False,
            "metadata": {},
            "created_at": datetime(2025, 1, 2),
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

    def test_get_thread_with_invalid_json_metadata_returns_none_metadata(self):
        """DB 中 metadata 为非法 JSON 时 _row_to_thread 通过 _deserialize_json 得到 None"""
        self.storage.save_thread({
            "thread_id": "traw",
            "title": "T",
            "url": "https://x/traw",
            "board": "b1",
            "images": "[]",
            "image_count": 0,
            "metadata": {},
        })
        # 直接写入非法 JSON，模拟历史脏数据
        self.storage._conn.execute(
            "UPDATE threads SET metadata = ? WHERE thread_id = ?",
            ("not json", "traw"),
        )
        self.storage._conn.commit()
        row = self.storage.get_thread("traw")
        self.assertIsNotNone(row)
        self.assertIsNone(row.get("metadata"))


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

    def test_article_exists_false_when_images_downloaded_zero(self):
        """未下载图片不算爬过：images_downloaded=0 时 article_exists 返回 False"""
        ok = self.storage.save_article({
            "article_id": "art1",
            "url": "https://news.com/1",
            "title": "News Title",
            "site": "news.com",
            "board": "",
            "metadata": {},
            "images_downloaded": False,
        })
        self.assertTrue(ok)
        self.assertFalse(self.storage.article_exists("art1"))

    def test_article_exists_false_when_images_downloaded_omitted(self):
        """未传 images_downloaded 时按 0 存，article_exists 返回 False"""
        ok = self.storage.save_article({
            "article_id": "art2",
            "url": "https://news.com/2",
            "title": "News Title 2",
            "site": "news.com",
            "board": "",
            "metadata": {},
        })
        self.assertTrue(ok)
        self.assertFalse(self.storage.article_exists("art2"))

    def test_save_article_with_created_at_string(self):
        """save_article 支持 created_at 为字符串"""
        ok = self.storage.save_article({
            "article_id": "art3",
            "url": "https://news.com/3",
            "title": "T3",
            "site": "news.com",
            "board": "",
            "metadata": {},
            "created_at": "2025-01-01T00:00:00",
            "images_downloaded": True,
        })
        self.assertTrue(ok)


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

    def test_get_from_queue_returns_non_json_as_value(self):
        """队列中非 JSON 字符串作为原始值返回"""
        self.storage.add_to_queue("q3", "plain")
        val = self.storage.get_from_queue("q3")
        self.assertEqual(val, "plain")

    def test_close_clears_visited_and_queues(self):
        """close 后 _visited_urls 和队列清空"""
        self.storage.mark_url_visited("https://x.com/1")
        self.storage.add_to_queue("q4", {"a": 1})
        self.storage.close()
        self.assertIsNone(self.storage._conn)
        self.assertFalse(self.storage.is_url_visited("https://x.com/1"))
        self.assertEqual(self.storage.get_queue_size("q4"), 0)

    def test_get_queue_size_nonexistent_returns_zero(self):
        """不存在的队列 get_queue_size 返回 0"""
        self.assertEqual(self.storage.get_queue_size("nonexistent_queue"), 0)


class TestStorageCheckpointExists(unittest.TestCase):
    """Storage checkpoint_exists 测试"""

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

    def test_checkpoint_exists_after_save(self):
        self.storage.save_checkpoint(
            "exist.com", "b1",
            {"current_page": 1, "last_thread_id": "", "last_thread_url": "", "status": "running", "stats": {}},
        )
        self.assertTrue(self.storage.checkpoint_exists("exist.com", "b1"))

    def test_checkpoint_exists_false_when_none(self):
        self.assertFalse(self.storage.checkpoint_exists("none.com", "b1"))


class TestStorageCheckpointUnconnected(unittest.TestCase):
    """未连接时检查点方法返回 None/False"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig_sqlite = config.database.sqlite_path
        config.database.sqlite_path = self.db_path
        self.storage = Storage()
        # 不 connect

    def tearDown(self):
        config.database.sqlite_path = self._orig_sqlite
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_load_checkpoint_returns_none(self):
        self.assertIsNone(self.storage.load_checkpoint("x", "b1"))

    def test_delete_checkpoint_returns_false(self):
        self.assertFalse(self.storage.delete_checkpoint("x", "b1"))

    def test_checkpoint_exists_returns_false(self):
        self.assertFalse(self.storage.checkpoint_exists("x", "b1"))

    def test_save_checkpoint_returns_false(self):
        self.assertFalse(self.storage.save_checkpoint("x", "b1", {"current_page": 1}))


class TestStorageSaveThreadException(unittest.TestCase):
    """save_thread 异常分支（sqlite 报错）"""

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

    def test_save_thread_execute_raises_returns_false(self):
        """execute 异常时返回 False（覆盖 188-190）"""
        import unittest.mock as mock
        fake_conn = mock.MagicMock()
        fake_conn.execute.side_effect = sqlite3.Error("constraint")
        fake_conn.commit = mock.MagicMock()
        with mock.patch.object(self.storage, "_conn", fake_conn):
            ok = self.storage.save_thread({
                "thread_id": "t1", "title": "T", "url": "https://x", "board": "b1",
                "images": [], "image_count": 0, "metadata": {},
            })
        self.assertFalse(ok)


class TestStorageSaveArticleException(unittest.TestCase):
    """save_article 异常分支"""

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

    def test_save_article_execute_raises_returns_false(self):
        """execute 异常时返回 False（覆盖 359-361）"""
        import unittest.mock as mock
        fake_conn = mock.MagicMock()
        fake_conn.execute.side_effect = sqlite3.Error("constraint")
        fake_conn.commit = mock.MagicMock()
        with mock.patch.object(self.storage, "_conn", fake_conn):
            ok = self.storage.save_article({
                "article_id": "a1", "url": "https://x", "title": "T", "site": "x", "board": "", "metadata": {},
            })
        self.assertFalse(ok)
