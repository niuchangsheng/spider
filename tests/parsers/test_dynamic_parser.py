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


class TestDynamicPageParserHasLoadMoreButton(unittest.TestCase):
    """has_load_more_button 测试"""

    @classmethod
    def setUpClass(cls):
        from config import create_config_from_dict
        cls.config = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://news.com",
            "selectors": {}, "urls": [],
        })

    def test_has_load_more_button_true_by_selector(self):
        """通过选择器找到'查看更多'返回 True"""
        parser = DynamicPageParser(self.config)
        html = '<html><body><a class="more" data-action="switch_page">更多</a></body></html>'
        self.assertTrue(parser.has_load_more_button(html))

    def test_has_load_more_button_true_by_text(self):
        """通过文本'查看更多'返回 True"""
        parser = DynamicPageParser(self.config)
        html = '<html><body><span>查看更多</span></body></html>'
        self.assertTrue(parser.has_load_more_button(html))

    def test_has_load_more_button_false(self):
        """无'查看更多'返回 False（正文不含'更多'等关键词）"""
        parser = DynamicPageParser(self.config)
        html = '<html><body><p>正文内容</p></body></html>'
        self.assertFalse(parser.has_load_more_button(html))


class TestDynamicPageParserGetNextPageNumber(unittest.TestCase):
    """get_next_page_number 测试"""

    @classmethod
    def setUpClass(cls):
        from config import create_config_from_dict
        cls.config = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://news.com",
            "selectors": {}, "urls": [],
        })

    def test_get_next_page_number_found(self):
        """找到 data-page 返回页码"""
        parser = DynamicPageParser(self.config)
        html = '<html><body><a data-page="3">下一页</a></body></html>'
        self.assertEqual(parser.get_next_page_number(html), 3)

    def test_get_next_page_number_not_found(self):
        """无 data-page 返回 None"""
        parser = DynamicPageParser(self.config)
        html = '<html><body></body></html>'
        self.assertIsNone(parser.get_next_page_number(html))


class TestDynamicPageParserParseArticleDetail(unittest.TestCase):
    """parse_article_detail 测试"""

    @classmethod
    def setUpClass(cls):
        from config import create_config_from_dict
        cls.config = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://news.com",
            "selectors": {}, "urls": [],
        })

    def test_parse_article_detail_returns_content_and_images(self):
        """解析详情页返回 content 和 images"""
        parser = DynamicPageParser(self.config)
        html = '''
        <html><body>
          <div class="article"><div class="body">正文内容在这里</div></div>
        </body></html>
        '''
        result = parser.parse_article_detail(html, "https://news.com/detail/999")
        self.assertIn("content", result)
        self.assertIn("images", result)
        self.assertIn("article_id", result)
        self.assertIn("正文", result["content"])

    def test_parse_article_detail_extracts_images_from_links(self):
        """从 <a href="*.jpg"> 提取图片"""
        parser = DynamicPageParser(self.config)
        html = '''
        <html><body>
          <div class="article"><div class="body">
            <a href="/img/1.jpg">图1</a>
          </div></div>
        </body></html>
        '''
        result = parser.parse_article_detail(html, "https://news.com/detail/1")
        self.assertIsInstance(result["images"], list)
        self.assertGreaterEqual(len(result["images"]), 1)
        self.assertTrue(any("1.jpg" in u for u in result["images"]))

    def test_parse_article_detail_uses_body_when_no_content_selector(self):
        """未找到内容选择器时使用 body"""
        parser = DynamicPageParser(self.config)
        html = '<html><body><p>仅body内容</p></body></html>'
        result = parser.parse_article_detail(html, "https://news.com/detail/2")
        self.assertIn("仅body内容", result["content"])


class TestDynamicPageParserGetBestImageUrl(unittest.TestCase):
    """_get_image_url 测试（srcset / data-src / src 尺寸后缀，覆盖 321-351）"""

    @classmethod
    def setUpClass(cls):
        from config import create_config_from_dict
        cls.config = create_config_from_dict({
            "name": "T", "forum_type": "news", "base_url": "https://news.com",
            "selectors": {}, "urls": [],
        })

    def test_get_best_image_url_from_srcset(self):
        """从 srcset 取最大宽度 URL"""
        from bs4 import BeautifulSoup
        parser = DynamicPageParser(self.config)
        html = '<img srcset="https://cdn.com/small.jpg 320w, https://cdn.com/large.jpg 800w" src="/fallback.jpg" />'
        img = BeautifulSoup(html, "html.parser").find("img")
        url = parser._get_image_url(img)
        self.assertEqual(url, "https://cdn.com/large.jpg")

    def test_get_best_image_url_from_data_src(self):
        """无 srcset 时从 data-src 取"""
        from bs4 import BeautifulSoup
        parser = DynamicPageParser(self.config)
        html = '<img data-src="https://lazy.com/img.jpg" />'
        img = BeautifulSoup(html, "html.parser").find("img")
        url = parser._get_image_url(img)
        self.assertEqual(url, "https://lazy.com/img.jpg")

    def test_get_best_image_url_from_src_strip_size_suffix(self):
        """从 src 取并去除 -100x100 尺寸后缀"""
        from bs4 import BeautifulSoup
        parser = DynamicPageParser(self.config)
        html = '<img src="https://cdn.com/photo-100x100.jpg" />'
        img = BeautifulSoup(html, "html.parser").find("img")
        url = parser._get_image_url(img)
        self.assertEqual(url, "https://cdn.com/photo.jpg")
