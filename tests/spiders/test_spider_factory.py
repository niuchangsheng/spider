"""
SpiderFactory 单元测试
"""
import unittest
from config import get_example_config
from spiders.spider_factory import SpiderFactory
from spiders.bbs_spider import BBSSpider, DiscuzSpider
from spiders.dynamic_news_spider import DynamicNewsCrawler


class TestSpiderFactoryCreateWithConfig(unittest.TestCase):
    def test_create_with_xindong_config_returns_discuz(self):
        cfg = get_example_config("xindong")
        spider = SpiderFactory.create(config=cfg)
        self.assertIsInstance(spider, DiscuzSpider)
        self.assertIsInstance(spider, BBSSpider)
        self.assertEqual(spider.config.bbs.name, "心动论坛")

    def test_create_with_preset_discuz(self):
        spider = SpiderFactory.create(preset="discuz")
        self.assertIsInstance(spider, DiscuzSpider)
        self.assertEqual(spider.config.bbs.forum_type, "discuz")

    def test_create_with_preset_phpbb(self):
        from spiders.bbs_spider import PhpBBSpider
        spider = SpiderFactory.create(preset="phpbb")
        self.assertIsInstance(spider, PhpBBSpider)

    def test_create_without_args_raises(self):
        with self.assertRaises(ValueError) as ctx:
            SpiderFactory.create()
        self.assertIn("必须提供", str(ctx.exception))


class TestSpiderFactoryCreateDynamic(unittest.TestCase):
    def test_create_dynamic_with_config(self):
        cfg = get_example_config("sxd")
        spider = SpiderFactory.create(config=cfg, spider_type="dynamic")
        self.assertIsInstance(spider, DynamicNewsCrawler)

    def test_create_dynamic_convenience_method(self):
        cfg = get_example_config("sxd")
        spider = SpiderFactory.create_dynamic(config=cfg)
        self.assertIsInstance(spider, DynamicNewsCrawler)
