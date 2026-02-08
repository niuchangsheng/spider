"""
CLI handlers 单元测试
"""
import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from config import config
from core.storage import storage
from cli.handlers import handle_checkpoint_status, print_statistics, handle_crawl_bbs, handle_crawl_news, handle_crawl


class TestHandleCheckpointStatus(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "test.db"
        self._orig = config.database.sqlite_path
        config.database.sqlite_path = self.db_path

    def tearDown(self):
        storage.close()
        config.database.sqlite_path = self._orig
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_no_checkpoint(self):
        args = MagicMock(site="test.com", board="b1", clear=False)
        asyncio.run(handle_checkpoint_status(args))

    def test_clear_when_none(self):
        args = MagicMock(site="test.com", board="b1", clear=True)
        asyncio.run(handle_checkpoint_status(args))

    def test_with_data(self):
        storage.connect()
        storage.save_checkpoint("test.com", "b1", {"current_page": 2, "last_thread_id": "123", "status": "running", "stats": {}})
        storage.close()
        args = MagicMock(site="test.com", board="b1", clear=False)
        asyncio.run(handle_checkpoint_status(args))

    def test_clear_existing(self):
        storage.connect()
        storage.save_checkpoint("clear.com", "b1", {"current_page": 1, "last_thread_id": "", "status": "running", "stats": {}})
        storage.close()
        args = MagicMock(site="clear.com", board="b1", clear=True)
        asyncio.run(handle_checkpoint_status(args))


class TestPrintStatistics(unittest.TestCase):
    """print_statistics 输出统计"""

    def test_print_statistics(self):
        spider = MagicMock()
        spider.get_statistics.return_value = {
            "threads_crawled": 5,
            "images_found": 10,
            "images_downloaded": 8,
            "images_failed": 2,
            "duplicates_skipped": 3,
        }
        print_statistics(spider)
        spider.get_statistics.assert_called_once()


class TestHandleCrawlBbs(unittest.TestCase):
    """handle_crawl_bbs 测试（mock SpiderFactory）"""

    @patch("cli.handlers.SpiderFactory")
    @patch("cli.handlers.get_example_config")
    def test_handle_crawl_bbs_board(self, mock_get_config, mock_factory):
        from config import get_example_config
        try:
            cfg = get_example_config("xindong")
        except Exception:
            self.skipTest("xindong config missing")
        mock_get_config.return_value = cfg
        spider = MagicMock()
        spider.__aenter__ = AsyncMock(return_value=spider)
        spider.__aexit__ = AsyncMock(return_value=None)
        spider.crawl_board = AsyncMock()
        spider.get_statistics.return_value = {"threads_crawled": 0, "images_found": 0, "images_downloaded": 0, "images_failed": 0, "duplicates_skipped": 0}
        mock_factory.create.return_value = spider
        args = MagicMock(config="xindong", target="https://bbs.xd.com/f1", type="board", max_workers=None, use_adaptive_queue=None, auto_detect=False, max_pages=None, resume=True, start_page=None)
        asyncio.run(handle_crawl_bbs(args))
        mock_factory.create.assert_called_once()
        spider.crawl_board.assert_called_once()

    def test_handle_crawl_bbs_no_config_no_auto(self):
        args = MagicMock(config=None, target="https://x.com", type="board", auto_detect=False)
        asyncio.run(handle_crawl_bbs(args))

    def test_handle_crawl_bbs_both_config_and_auto(self):
        args = MagicMock(config="xindong", target="https://x.com", type="board", auto_detect=True)
        asyncio.run(handle_crawl_bbs(args))


class TestHandleCrawlNews(unittest.TestCase):
    """handle_crawl_news 测试（mock crawler）"""

    @patch("cli.handlers.DynamicNewsCrawler")
    def test_handle_crawl_news_with_url(self, mock_crawler_class):
        crawler = MagicMock()
        crawler.__aenter__ = AsyncMock(return_value=crawler)
        crawler.__aexit__ = AsyncMock(return_value=None)
        crawler.crawl_news_and_download_images = AsyncMock(return_value=(2, 5))
        crawler.get_statistics.return_value = {"articles_crawled": 2, "articles_failed": 0}
        mock_crawler_class.return_value = crawler
        args = MagicMock(url="https://news.com/page1", config=None, max_pages=1, resume=True, start_page=None, download_images=True, max_workers=None, use_adaptive_queue=None)
        asyncio.run(handle_crawl_news(args))
        mock_crawler_class.assert_called_once()
        crawler.crawl_news_and_download_images.assert_called_once()


class TestHandleCrawl(unittest.TestCase):
    """handle_crawl 全量爬取测试（mock SpiderFactory）"""

    @patch("cli.handlers.SpiderFactory")
    @patch("cli.handlers.get_example_config")
    def test_handle_crawl_bbs_config(self, mock_get_config, mock_factory):
        from config import get_example_config
        try:
            cfg = get_example_config("xindong")
        except Exception:
            self.skipTest("xindong config missing")
        mock_get_config.return_value = cfg
        spider = MagicMock()
        spider.__aenter__ = AsyncMock(return_value=spider)
        spider.__aexit__ = AsyncMock(return_value=None)
        spider.crawl_board = AsyncMock(return_value=None)
        spider.crawl_thread = AsyncMock(return_value=None)
        spider.get_statistics.return_value = {"threads_crawled": 0, "images_found": 0, "images_downloaded": 0, "images_failed": 0, "duplicates_skipped": 0}
        # parser 需有 _extract_thread_id
        spider.parser = MagicMock()
        spider.parser._extract_thread_id.return_value = "123"
        mock_factory.create.return_value = spider
        args = MagicMock(config="xindong", max_workers=None, use_adaptive_queue=None, max_pages=None, resume=True, start_page=None, download_images=False)
        asyncio.run(handle_crawl(args))
        mock_factory.create.assert_called_once()
        self.assertGreaterEqual(spider.crawl_board.call_count + spider.crawl_thread.call_count, 1)

    @patch("cli.handlers.DynamicNewsCrawler")
    @patch("cli.handlers.get_example_config")
    def test_handle_crawl_news_config(self, mock_get_config, mock_crawler_class):
        from config import create_config_from_dict
        cfg = create_config_from_dict({
            "name": "N", "forum_type": "news", "base_url": "https://n.com",
            "crawler_type": "news", "selectors": {}, "urls": ["https://news.com/1"],
        })
        mock_get_config.return_value = cfg
        crawler = MagicMock()
        crawler.__aenter__ = AsyncMock(return_value=crawler)
        crawler.__aexit__ = AsyncMock(return_value=None)
        crawler.crawl_news_and_download_images = AsyncMock(return_value=(1, 2))
        crawler.get_statistics.return_value = {"articles_crawled": 1, "articles_failed": 0}
        mock_crawler_class.return_value = crawler
        args = MagicMock(config="sxd", max_workers=None, use_adaptive_queue=None, max_pages=1, resume=True, start_page=None, download_images=False)
        asyncio.run(handle_crawl(args))
        mock_crawler_class.assert_called_once()
        self.assertEqual(crawler.crawl_news_and_download_images.call_count, 1)
