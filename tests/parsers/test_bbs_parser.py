"""
BBSParser 单元测试
"""
import unittest
from pathlib import Path

from config import load_forum_config_file, create_config_from_dict
from parsers.bbs_parser import BBSParser


# Discuz 列表页片段：tbody + a.xst
SAMPLE_LIST_HTML = """
<table>
<tbody id="stickthread_123">
<tr><td><a href="forum.php?mod=viewthread&tid=123" class="xst">【公告】测试帖1</a></td></tr>
</tbody>
<tbody id="normalthread_456">
<tr><td><a href="/forum.php?mod=viewthread&tid=456" class="xst">普通帖2</a></td></tr>
</tbody>
</table>
"""


class TestBBSParserParseThreadList(unittest.TestCase):
    """parse_thread_list 测试"""

    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent.parent.parent / "configs" / "xindong.json"
        if path.exists():
            data = load_forum_config_file(path)
            cls.config = create_config_from_dict(data)
        else:
            cls.config = None

    def test_parse_thread_list_with_config(self):
        """使用 xindong 配置解析列表页"""
        if self.config is None:
            self.skipTest("configs/xindong.json 不存在")
        parser = BBSParser(self.config)
        threads = parser.parse_thread_list(SAMPLE_LIST_HTML, "https://bbs.xd.com/")
        self.assertIsInstance(threads, list)
        self.assertGreaterEqual(len(threads), 2)
        t1 = next((t for t in threads if t.get("thread_id") == "123"), None)
        t2 = next((t for t in threads if t.get("thread_id") == "456"), None)
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertIn("公告", t1["title"] or "")
        self.assertIn("123", t1["url"])
        self.assertIn("456", t2["url"])

    def test_parse_thread_list_empty_html(self):
        """空 HTML 返回空列表"""
        parser = BBSParser()
        threads = parser.parse_thread_list("<html><body></body></html>", "https://example.com/")
        self.assertEqual(threads, [])


class TestBBSParserParseThreadPage(unittest.TestCase):
    """parse_thread_page 测试"""

    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent.parent.parent / "configs" / "xindong.json"
        if path.exists():
            data = load_forum_config_file(path)
            cls.config = create_config_from_dict(data)
        else:
            cls.config = None

    def test_parse_thread_page_extracts_images(self):
        """解析帖子页能提取图片"""
        if self.config is None:
            self.skipTest("configs/xindong.json 不存在")
        html = """
        <div class="pcb">
            <img src="https://bbs.xd.com/1.jpg" />
            <img file="https://bbs.xd.com/2.png" />
        </div>
        """
        parser = BBSParser(self.config)
        result = parser.parse_thread_page(html, "https://bbs.xd.com/forum.php?mod=viewthread&tid=999")
        self.assertIn("images", result)
        self.assertIsInstance(result["images"], list)
        self.assertGreaterEqual(len(result["images"]), 1)


class TestBBSParserFindNextPage(unittest.TestCase):
    """find_next_page 测试"""

    @classmethod
    def setUpClass(cls):
        path = Path(__file__).parent.parent.parent / "configs" / "xindong.json"
        if path.exists():
            data = load_forum_config_file(path)
            cls.config = create_config_from_dict(data)
        else:
            cls.config = None

    def test_find_next_page(self):
        """能找到下一页链接"""
        if self.config is None:
            self.skipTest("configs/xindong.json 不存在")
        html = '<div class="pg"><a href="forum.php?mod=forumdisplay&fid=21&page=2" class="nxt">下一页</a></div>'
        parser = BBSParser(self.config)
        next_url = parser.find_next_page(html, "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21")
        self.assertIsNotNone(next_url)
        self.assertIn("page=2", next_url)

    def test_find_next_page_none(self):
        """无下一页时返回 None"""
        parser = BBSParser()
        next_url = parser.find_next_page("<html><body>无分页</body></html>", "https://example.com/")
        self.assertIsNone(next_url)
