# config module tests - see test_config_classes below
import unittest
from pathlib import Path
from config import (
    CONFIG_DIR,
    load_forum_config_file,
    create_config_from_dict,
    get_example_config,
    get_forum_boards,
    get_forum_urls,
    get_news_urls,
    Config,
)


class TestLoadForumConfigFile(unittest.TestCase):
    def test_load_existing_config(self):
        path = CONFIG_DIR / "xindong.json"
        if not path.exists():
            self.skipTest("configs/xindong.json missing")
        data = load_forum_config_file(path)
        self.assertIsInstance(data, dict)
        self.assertIn("name", data)
        self.assertIn("selectors", data)

    def test_load_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_forum_config_file(Path("/nonexistent/config.json"))


class TestCreateConfigFromDict(unittest.TestCase):
    def test_bbs_config(self):
        data = {
            "name": "TestForum",
            "forum_type": "discuz",
            "base_url": "https://test.com",
            "crawler_type": "bbs",
            "selectors": {"thread_list": "tbody.thread", "thread_link": "a.xst", "image": "img", "next_page": "a.nxt"},
            "urls": [{"type": "board", "name": "b1", "url": "https://test.com/f1"}, "https://test.com/1"],
            "crawler": {},
        }
        cfg = create_config_from_dict(data)
        self.assertEqual(cfg.crawler_type, "bbs")
        self.assertEqual(cfg.bbs.name, "TestForum")
        self.assertEqual(len(cfg.urls), 2)

    def test_news_config(self):
        data = {"name": "N", "forum_type": "news", "base_url": "https://n.com", "crawler_type": "news", "selectors": {}, "urls": []}
        cfg = create_config_from_dict(data)
        self.assertEqual(cfg.crawler_type, "news")

    def test_boards_legacy_merged(self):
        data = {
            "name": "L",
            "forum_type": "discuz",
            "base_url": "https://b.com",
            "selectors": {"thread_list": "x", "thread_link": "y"},
            "boards": [{"name": "版1", "url": "https://b.com/1"}],
            "urls": [],
        }
        cfg = create_config_from_dict(data)
        self.assertEqual(len(cfg.urls), 1)
        self.assertEqual(cfg.urls[0].get("type"), "board")


class TestGetExampleConfig(unittest.TestCase):
    def test_get_existing(self):
        cfg = get_example_config("xindong")
        self.assertIsInstance(cfg, Config)
        self.assertEqual(cfg.bbs.name, "心动论坛")

    def test_get_unknown_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_example_config("nonexistent_xyz")
        self.assertIn("未知的示例配置", str(ctx.exception))


class TestGetForumBoards(unittest.TestCase):
    def test_xindong_has_boards(self):
        boards = get_forum_boards("xindong")
        self.assertIsInstance(boards, list)

    def test_nonexistent_returns_empty(self):
        self.assertEqual(get_forum_boards("nonexistent_xyz"), [])


class TestGetForumUrls(unittest.TestCase):
    def test_xindong_has_urls(self):
        urls = get_forum_urls("xindong")
        self.assertIsInstance(urls, list)

    def test_nonexistent_returns_empty(self):
        self.assertEqual(get_forum_urls("nonexistent_xyz"), [])


class TestGetNewsUrls(unittest.TestCase):
    def test_sxd_has_urls(self):
        urls = get_news_urls("sxd")
        self.assertIsInstance(urls, list)

    def test_nonexistent_returns_empty(self):
        self.assertEqual(get_news_urls("nonexistent_xyz"), [])


class TestConfigLoader(unittest.TestCase):
    """ConfigLoader.load 测试"""

    def test_load_discuz(self):
        from config import ConfigLoader
        cfg = ConfigLoader.load("discuz")
        self.assertEqual(cfg.bbs.forum_type, "discuz")

    def test_load_phpbb(self):
        from config import ConfigLoader
        cfg = ConfigLoader.load("phpbb")
        self.assertEqual(cfg.bbs.forum_type, "phpbb")

    def test_load_vbulletin(self):
        from config import ConfigLoader
        cfg = ConfigLoader.load("vbulletin")
        self.assertEqual(cfg.bbs.forum_type, "vbulletin")
