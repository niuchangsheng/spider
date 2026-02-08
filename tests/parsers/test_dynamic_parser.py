"""
DynamicPageParser 单元测试
"""
import unittest
from pathlib import Path

from config import get_example_config
from parsers.dynamic_parser import DynamicPageParser


SAMPLE_HTML = """
<html>
<body>
  <div class="article">
    <h3 class="title"><a href="/news/123">文章标题</a></h3>
    <span class="author">作者</span>
    <span class="date">2025-01-01</span>
    <div class="body">摘要内容</div>
  </div>
  <div class="article">
    <h3 class="title"><a href="/news/456">第二篇</a></h3>
    <span class="author">作者2</span>
    <span class="date">2025-01-02</span>
    <div class="body">摘要2</div>
  </div>
</body>
</html>
"""


class TestDynamicPageParserParseArticles(unittest.TestCase):
    """parse_articles 测试"""

    @classmethod
    def setUpClass(cls):
        try:
            cls.config = get_example_config("sxd")
        except Exception:
            cls.config = None

    def test_parse_articles_with_config(self):
        """使用 sxd 配置解析文章列表"""
        if self.config is None:
            self.skipTest("config sxd 不存在")
        parser = DynamicPageParser(self.config)
        articles = parser.parse_articles(SAMPLE_HTML)
        self.assertIsInstance(articles, list)
        self.assertGreaterEqual(len(articles), 1)
        if articles:
            a = articles[0]
            self.assertIn("title", a)
            self.assertIn("url", a)

    def test_parse_articles_empty_html(self):
        """空 HTML 返回空列表"""
        from config import create_config_from_dict
        cfg = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://t.com",
            "selectors": {}, "urls": [],
        })
        parser = DynamicPageParser(cfg)
        articles = parser.parse_articles("<html><body></body></html>")
        self.assertEqual(articles, [])


class TestDynamicPageParserExtractArticleInfo(unittest.TestCase):
    """_extract_article_info 测试"""

    @classmethod
    def setUpClass(cls):
        from config import create_config_from_dict
        cls.config = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://news.com",
            "selectors": {
                "article": ".article",
                "title": ".title",
                "link": ".link",
                "author": ".author",
                "date": ".date",
                "summary": ".body",
            },
            "urls": [],
        })

    def test_extract_article_info_from_title_link(self):
        """从标题内链接提取"""
        from bs4 import BeautifulSoup
        html = '<div class="article"><h3 class="title"><a href="/detail/123">标题</a></h3><span class="author">a</span><span class="date">d</span><div class="body">b</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        parser = DynamicPageParser(self.config)
        article = parser._extract_article_info(soup.select_one(".article"))
        self.assertIsNotNone(article)
        self.assertEqual(article["title"], "标题")
        self.assertIn("123", article["url"])
        self.assertTrue(article["url"].startswith("https://"))

    def test_extract_article_info_missing_title_returns_none(self):
        """缺少标题返回 None"""
        from bs4 import BeautifulSoup
        html = '<div class="article"><span class="author">a</span><a class="link" href="/p/1">链接</a></div>'
        soup = BeautifulSoup(html, "html.parser")
        parser = DynamicPageParser(self.config)
        article = parser._extract_article_info(soup.select_one(".article"))
        self.assertIsNone(article)

    def test_extract_article_info_relative_url_prefixed(self):
        """相对 URL 补全 base_url"""
        from bs4 import BeautifulSoup
        html = '<div class="article"><h3 class="title"><a href="/item/456">文</a></h3><span class="author">x</span><span class="date">d</span><div class="body">b</div></div>'
        soup = BeautifulSoup(html, "html.parser")
        parser = DynamicPageParser(self.config)
        article = parser._extract_article_info(soup.select_one(".article"))
        self.assertIsNotNone(article)
        self.assertTrue(article["url"].startswith("https://news.com"))
