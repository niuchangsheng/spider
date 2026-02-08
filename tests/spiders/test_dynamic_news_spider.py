"""
DynamicNewsCrawler 单元测试（检查点与 max_pages 等场景）
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from config import get_example_config
from spiders.dynamic_news_spider import DynamicNewsCrawler


class TestCrawlDynamicPageAjaxCheckpointMaxPages(unittest.TestCase):
    """crawl_dynamic_page_ajax：检查点超过 max_pages 时本次不爬取"""

    def test_returns_empty_and_sets_skipped_when_checkpoint_page_gt_max_pages(self):
        """检查点 current_page > max_pages 时返回 [] 且 _skipped_checkpoint_over_max_pages=True"""
        config = get_example_config("sxd")
        crawler = DynamicNewsCrawler(config)

        with patch("spiders.dynamic_news_spider.CheckpointManager") as MockCP:
            mock_cp = MagicMock()
            mock_cp.exists.return_value = True
            mock_cp.load_checkpoint.return_value = {
                "current_page": 10,
                "status": "running",
                "seen_article_ids": [],
                "min_article_id": None,
                "max_article_id": None,
            }
            MockCP.return_value = mock_cp

            async def run():
                return await crawler.crawl_dynamic_page_ajax(
                    "https://sxd.xd.com/",
                    max_pages=5,
                    resume=True,
                )

            result = asyncio.run(run())

        self.assertEqual(result, [])
        self.assertTrue(getattr(crawler, "_skipped_checkpoint_over_max_pages", False))
        mock_cp.load_checkpoint.assert_called_once()

    def test_does_not_skip_when_checkpoint_page_le_max_pages(self):
        """检查点 current_page <= max_pages 时不设 _skipped，会进入爬取逻辑（需 mock fetch）"""
        config = get_example_config("sxd")
        crawler = DynamicNewsCrawler(config)

        with patch("spiders.dynamic_news_spider.CheckpointManager") as MockCP:
            mock_cp = MagicMock()
            mock_cp.exists.return_value = True
            mock_cp.load_checkpoint.return_value = {
                "current_page": 3,
                "status": "running",
                "seen_article_ids": [],
                "min_article_id": None,
                "max_article_id": None,
            }
            MockCP.return_value = mock_cp

            with patch.object(crawler, "fetch_page", new_callable=AsyncMock, return_value="<html></html>"):
                with patch("spiders.dynamic_news_spider.storage") as mock_storage:
                    mock_storage.article_exists.return_value = False
                    with patch.object(crawler.parser, "parse_articles", return_value=[]):

                        async def run():
                            return await crawler.crawl_dynamic_page_ajax(
                                "https://sxd.xd.com/",
                                max_pages=5,
                                resume=True,
                            )

                        result = asyncio.run(run())

        self.assertFalse(getattr(crawler, "_skipped_checkpoint_over_max_pages", True))
        self.assertEqual(result, [])
