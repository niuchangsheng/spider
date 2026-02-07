"""
CheckpointManager 单元测试（v2.4：基于 Storage，使用临时 SQLite）
"""
import unittest
import tempfile
import shutil
from pathlib import Path

from config import config
from core.storage import storage
from core.checkpoint import CheckpointManager


class TestCheckpointManager(unittest.TestCase):
    """CheckpointManager 测试类"""

    def setUp(self):
        """测试前准备：使用临时 SQLite，连接 Storage"""
        self.test_dir = tempfile.mkdtemp()
        config.database.sqlite_path = Path(self.test_dir) / "test.db"
        storage.connect()
        self.checkpoint = CheckpointManager(
            site="test.com",
            board="test_board",
            checkpoint_dir=Path(self.test_dir) / "checkpoints",
        )

    def tearDown(self):
        """测试后清理"""
        storage.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.checkpoint.site, "test.com")
        self.assertEqual(self.checkpoint.board, "test_board")
        self.assertIn("test.com", self.checkpoint.checkpoint_file)
        self.assertIn("test_board", self.checkpoint.checkpoint_file)

    def test_save_and_load_checkpoint(self):
        """测试保存和加载检查点"""
        result = self.checkpoint.save_checkpoint(
            current_page=5,
            last_thread_id="12345",
            last_thread_url="https://test.com/thread/12345",
            status="running",
            stats={"crawled_count": 100},
        )
        self.assertTrue(result)
        self.assertTrue(self.checkpoint.exists())

        data = self.checkpoint.load_checkpoint()
        self.assertIsNotNone(data)
        self.assertEqual(data["current_page"], 5)
        self.assertEqual(data["last_thread_id"], "12345")
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["stats"]["crawled_count"], 100)

    def test_save_checkpoint_with_article_ids(self):
        """测试保存包含 article_id 的检查点"""
        result = self.checkpoint.save_checkpoint(
            current_page=3,
            seen_article_ids=["1001", "1002", "1003"],
            min_article_id="1001",
            max_article_id="1003",
        )
        self.assertTrue(result)

        data = self.checkpoint.load_checkpoint()
        self.assertEqual(data["seen_article_ids"], ["1001", "1002", "1003"])
        self.assertEqual(data["min_article_id"], "1001")
        self.assertEqual(data["max_article_id"], "1003")

    def test_get_seen_article_ids(self):
        """测试获取已爬取的文章ID集合"""
        self.checkpoint.save_checkpoint(
            current_page=1,
            seen_article_ids=["1001", "1002", "1003"],
        )
        seen_ids = self.checkpoint.get_seen_article_ids()
        self.assertEqual(seen_ids, {"1001", "1002", "1003"})

    def test_get_min_max_article_id(self):
        """测试获取最小/最大文章ID"""
        self.checkpoint.save_checkpoint(
            current_page=1,
            min_article_id="1001",
            max_article_id="1003",
        )
        self.assertEqual(self.checkpoint.get_min_article_id(), "1001")
        self.assertEqual(self.checkpoint.get_max_article_id(), "1003")

    def test_mark_completed(self):
        """测试标记完成"""
        self.checkpoint.save_checkpoint(
            current_page=10,
            status="running",
        )
        result = self.checkpoint.mark_completed(final_stats={"total": 100})
        self.assertTrue(result)
        data = self.checkpoint.load_checkpoint()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["stats"]["total"], 100)

    def test_mark_error(self):
        """测试标记错误"""
        self.checkpoint.save_checkpoint(
            current_page=5,
            status="running",
        )
        result = self.checkpoint.mark_error("测试错误")
        self.assertTrue(result)
        data = self.checkpoint.load_checkpoint()
        self.assertEqual(data["status"], "error")
        self.assertIn("last_error", data["stats"])

    def test_get_current_page(self):
        """测试获取当前页"""
        self.assertEqual(self.checkpoint.get_current_page(), 1)
        self.checkpoint.save_checkpoint(current_page=5)
        self.assertEqual(self.checkpoint.get_current_page(), 5)

    def test_get_status(self):
        """测试获取状态"""
        self.assertIsNone(self.checkpoint.get_status())
        self.checkpoint.save_checkpoint(current_page=1, status="running")
        self.assertEqual(self.checkpoint.get_status(), "running")

    def test_clear_checkpoint(self):
        """测试清除检查点"""
        self.checkpoint.save_checkpoint(current_page=1)
        self.assertTrue(self.checkpoint.exists())
        self.checkpoint.clear_checkpoint()
        self.assertFalse(self.checkpoint.exists())

    def test_exists(self):
        """测试检查点是否存在"""
        self.assertFalse(self.checkpoint.exists())
        self.checkpoint.save_checkpoint(current_page=1)
        self.assertTrue(self.checkpoint.exists())

    def test_site_sanitization(self):
        """测试站点名称规范化"""
        checkpoint1 = CheckpointManager(
            site="https://test.com",
            board="board",
            checkpoint_dir=Path(self.test_dir) / "checkpoints",
        )
        self.assertEqual(checkpoint1.site, "test.com")
        checkpoint2 = CheckpointManager(
            site="test.com",
            board="board",
            checkpoint_dir=Path(self.test_dir) / "checkpoints",
        )
        self.assertEqual(checkpoint2.site, "test.com")


if __name__ == "__main__":
    unittest.main()
