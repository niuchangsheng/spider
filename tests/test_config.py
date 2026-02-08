# config module tests - see test_config_classes below
import unittest
from pathlib import Path
from unittest.mock import patch
from config import (
    CONFIG_DIR,
    load_forum_config_file,
    load_all_forum_configs,
    create_config_from_dict,
    get_example_config,
    get_forum_boards,
    get_forum_urls,
    get_news_urls,
    get_example_threads,
    Config,
    ConfigLoader,
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

    def test_invalid_crawler_type_falls_back_to_bbs(self):
        """crawler_type 非 bbs/news 时回退为 bbs"""
        data = {"name": "X", "forum_type": "custom", "base_url": "https://x.com", "crawler_type": "other", "selectors": {}, "urls": []}
        cfg = create_config_from_dict(data)
        self.assertEqual(cfg.crawler_type, "bbs")

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

    def test_get_boards_fallback_when_no_board_type_in_urls(self):
        """urls 中无 type=board 时回退到 data.get('boards')"""
        with patch("config.load_forum_config_file") as mock_load:
            mock_load.return_value = {
                "name": "T", "forum_type": "discuz", "base_url": "https://t.com",
                "urls": [{"type": "thread", "url": "https://t.com/1"}],
                "boards": [{"name": "版1", "url": "https://t.com/b1"}],
            }
            boards = get_forum_boards("xindong")
            self.assertEqual(len(boards), 1)
            self.assertEqual(boards[0]["name"], "版1")

    def test_load_error_returns_empty(self):
        from unittest.mock import patch
        with patch("config.load_forum_config_file") as mock_load:
            mock_load.side_effect = ValueError("bad json")
            self.assertEqual(get_forum_boards("xindong"), [])


class TestGetForumUrls(unittest.TestCase):
    def test_xindong_has_urls(self):
        urls = get_forum_urls("xindong")
        self.assertIsInstance(urls, list)

    def test_nonexistent_returns_empty(self):
        self.assertEqual(get_forum_urls("nonexistent_xyz"), [])

    def test_load_error_returns_empty(self):
        from unittest.mock import patch
        with patch("config.load_forum_config_file") as mock_load:
            mock_load.side_effect = ValueError("bad json")
            self.assertEqual(get_forum_urls("xindong"), [])


class TestGetNewsUrls(unittest.TestCase):
    def test_sxd_has_urls(self):
        urls = get_news_urls("sxd")
        self.assertIsInstance(urls, list)

    def test_nonexistent_returns_empty(self):
        self.assertEqual(get_news_urls("nonexistent_xyz"), [])

    def test_load_error_returns_empty(self):
        with patch("config.load_forum_config_file") as mock_load:
            mock_load.side_effect = ValueError("bad json")
            self.assertEqual(get_news_urls("sxd"), [])


class TestGetExampleThreads(unittest.TestCase):
    """get_example_threads 已废弃，委托 get_forum_urls"""

    def test_get_example_threads_delegates_to_get_forum_urls(self):
        """get_example_threads 委托 get_forum_urls"""
        with patch("config.get_forum_urls", return_value=["https://x.com/1"]) as mock_get:
            result = get_example_threads("xindong")
            mock_get.assert_called_once_with("xindong")
            self.assertEqual(result, ["https://x.com/1"])


class TestLoadAllForumConfigs(unittest.TestCase):
    """load_all_forum_configs 测试"""

    def test_config_dir_not_exists_returns_empty(self):
        with patch("config.CONFIG_DIR") as mock_dir:
            mock_dir.exists.return_value = False
            result = load_all_forum_configs()
            self.assertEqual(result, {})

    def test_load_one_file_raises_continues_empty(self):
        """某个配置文件加载失败时打 warning 并继续，该文件不计入结果（覆盖 325-326 except）"""
        with patch("config.CONFIG_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [Path("bad.json")]
            with patch("config.load_forum_config_file", side_effect=Exception("bad json")):
                result = load_all_forum_configs()
            self.assertEqual(result, {})

    def test_load_one_file_success_includes_config(self):
        """单个配置文件加载成功时计入 configs 并打 logger.info（覆盖 323-325）"""
        with patch("config.CONFIG_DIR") as mock_dir:
            mock_dir.exists.return_value = True
            mock_dir.glob.return_value = [Path("ok.json")]
            good_data = {"name": "OK", "forum_type": "discuz", "base_url": "https://ok.com", "selectors": {}, "urls": []}
            with patch("config.load_forum_config_file", return_value=good_data):
                result = load_all_forum_configs()
            self.assertIn("ok", result)
            self.assertEqual(result["ok"].bbs.name, "OK")


class TestConfigLoader(unittest.TestCase):
    """ConfigLoader.load 测试"""

    def test_load_discuz(self):
        cfg = ConfigLoader.load("discuz")
        self.assertEqual(cfg.bbs.forum_type, "discuz")

    def test_load_phpbb(self):
        cfg = ConfigLoader.load("phpbb")
        self.assertEqual(cfg.bbs.forum_type, "phpbb")

    def test_load_vbulletin(self):
        cfg = ConfigLoader.load("vbulletin")
        self.assertEqual(cfg.bbs.forum_type, "vbulletin")

    def test_load_unknown_preset_uses_load_config_from_env(self):
        """未知 preset 调用 load_config_from_env"""
        with patch("config.load_config_from_env") as mock_load:
            mock_cfg = create_config_from_dict({
                "name": "Env", "forum_type": "custom", "base_url": "https://env.com",
                "selectors": {}, "urls": [],
            })
            mock_load.return_value = mock_cfg
            cfg = ConfigLoader.load("default")
            mock_load.assert_called_once()
            self.assertEqual(cfg.bbs.base_url, "https://env.com")


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


class TestConfigLoaderAutoDetect(unittest.TestCase):
    """ConfigLoader.auto_detect 测试（mock requests 与 detector）"""

    def test_auto_detect_success(self):
        from unittest.mock import patch, MagicMock
        from config import ConfigLoader
        mock_response = MagicMock()
        mock_response.text = "<html><body>Powered by Discuz!</body></html>"
        with patch("requests.get", return_value=mock_response), \
             patch("detector.selector_detector.SelectorDetector") as mock_detector_cls:
            mock_detector = MagicMock()
            mock_detector.auto_detect_selectors.return_value = {
                "forum_type": "discuz",
                "selectors": {
                    "thread_list_selector": "tbody.thread",
                    "thread_link_selector": "a.xst",
                    "image_selector": "img",
                    "next_page_selector": "a.nxt",
                },
                "confidence": {"overall": 0.85},
            }
            mock_detector_cls.return_value = mock_detector
            cfg = ConfigLoader.auto_detect("https://bbs.example.com/")
            self.assertEqual(cfg.bbs.forum_type, "discuz")
            self.assertEqual(cfg.bbs.thread_list_selector, "tbody.thread")

    def test_auto_detect_exception_returns_default(self):
        from unittest.mock import patch
        from config import ConfigLoader
        with patch("requests.get", side_effect=Exception("network error")):
            cfg = ConfigLoader.auto_detect("https://bbs.example.com/")
            self.assertIsInstance(cfg, Config)

    def test_auto_detect_low_confidence_warning(self):
        """置信度 < 70% 时打 warning 仍返回配置"""
        from unittest.mock import patch, MagicMock
        from config import ConfigLoader
        mock_response = MagicMock()
        mock_response.text = "<html><body>Unknown</body></html>"
        with patch("requests.get", return_value=mock_response), \
             patch("detector.selector_detector.SelectorDetector") as mock_detector_cls:
            mock_detector = MagicMock()
            mock_detector.auto_detect_selectors.return_value = {
                "forum_type": "discuz",
                "selectors": {"thread_list_selector": "x", "thread_link_selector": "a", "image_selector": "img", "next_page_selector": "n"},
                "confidence": {"overall": 0.5},
            }
            mock_detector_cls.return_value = mock_detector
            cfg = ConfigLoader.auto_detect("https://bbs.example.com/")
            self.assertIsInstance(cfg, Config)
            self.assertEqual(cfg.bbs.forum_type, "discuz")
