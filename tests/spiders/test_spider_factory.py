"""
SpiderFactory 单元测试
"""
import unittest
from unittest.mock import patch

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

    def test_create_with_url_auto_detect(self):
        """create(url=...) 调用 ConfigLoader.auto_detect"""
        cfg = get_example_config("xindong")
        with patch("spiders.spider_factory.ConfigLoader.auto_detect", return_value=cfg):
            spider = SpiderFactory.create(url="https://bbs.xd.com/")
        self.assertIsInstance(spider, BBSSpider)
        self.assertEqual(spider.config.bbs.name, "心动论坛")


class TestSpiderFactoryCreateDynamic(unittest.TestCase):
    def test_create_dynamic_with_config(self):
        cfg = get_example_config("sxd")
        spider = SpiderFactory.create(config=cfg, spider_type="dynamic")
        self.assertIsInstance(spider, DynamicNewsCrawler)

    def test_create_dynamic_convenience_method(self):
        cfg = get_example_config("sxd")
        spider = SpiderFactory.create_dynamic(config=cfg)
        self.assertIsInstance(spider, DynamicNewsCrawler)


class TestSpiderFactoryRegister(unittest.TestCase):
    """SpiderFactory.register 测试"""

    def test_register_and_create_custom_forum_type(self):
        """注册自定义 forum_type 后 create 可返回该类型"""
        from config import create_config_from_dict
        custom_cfg = create_config_from_dict({
            "name": "Custom",
            "forum_type": "discuz",
            "base_url": "https://custom.com",
            "selectors": {},
            "urls": [],
        })
        SpiderFactory.register("discuz", DiscuzSpider)
        spider = SpiderFactory.create(config=custom_cfg)
        self.assertIsInstance(spider, DiscuzSpider)
