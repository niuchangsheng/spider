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


class TestConfigGetBoardsAndUrls(unittest.TestCase):
    """Config.get_boards / get_page_urls / get_page_entries 测试"""

    def test_get_boards(self):
        cfg = create_config_from_dict({
            "name": "T", "forum_type": "discuz", "base_url": "https://t.com",
            "selectors": {"thread_list": "x", "thread_link": "y"},
            "urls": [
                {"type": "board", "name": "版1", "url": "https://t.com/b1"},
                {"type": "thread", "name": "帖1", "url": "https://t.com/t1"},
            ],
        })
        boards = cfg.get_boards()
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0]["name"], "版1")
        self.assertEqual(boards[0]["url"], "https://t.com/b1")

    def test_get_page_urls_and_entries(self):
        cfg = create_config_from_dict({
            "name": "T", "forum_type": "discuz", "base_url": "https://t.com",
            "selectors": {"thread_list": "x", "thread_link": "y"},
            "urls": ["https://t.com/1", {"type": "thread", "name": "帖1", "url": "https://t.com/t1"}],
        })
        entries = cfg.get_page_entries()
        self.assertEqual(len(entries), 2)
        urls = cfg.get_page_urls()
        self.assertEqual(urls, ["https://t.com/1", "https://t.com/t1"])


class TestLoadConfigFromEnv(unittest.TestCase):
    """load_config_from_env 测试"""

    def test_load_config_from_env(self):
        import os
        from config import load_config_from_env
        orig = os.environ.get("BBS_BASE_URL")
        try:
            os.environ["BBS_BASE_URL"] = "https://env.com"
            cfg = load_config_from_env()
            self.assertEqual(cfg.bbs.base_url, "https://env.com")
        finally:
            if orig is not None:
                os.environ["BBS_BASE_URL"] = orig
            elif "BBS_BASE_URL" in os.environ:
                del os.environ["BBS_BASE_URL"]


class TestForumPresets(unittest.TestCase):
    """ForumPresets 直接调用测试"""

    def test_discuz(self):
        from config import ForumPresets
        cfg = ForumPresets.discuz()
        self.assertEqual(cfg.bbs.forum_type, "discuz")
        self.assertIn("normalthread", cfg.bbs.thread_list_selector)

    def test_phpbb(self):
        from config import ForumPresets
        cfg = ForumPresets.phpbb()
        self.assertEqual(cfg.bbs.forum_type, "phpbb")

    def test_vbulletin(self):
        from config import ForumPresets
        cfg = ForumPresets.vbulletin()
        self.assertEqual(cfg.bbs.forum_type, "vbulletin")
