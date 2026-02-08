"""
BaseParser 单元测试（通过 BBSParser 子类调用基类方法）
"""
import unittest
from parsers.bbs_parser import BBSParser
from bs4 import BeautifulSoup


class TestBaseParserExtractId(unittest.TestCase):
    """_extract_id：正则匹配与 MD5 回退"""

    def test_extract_id_by_pattern(self):
        parser = BBSParser()
        tid = parser._extract_id("https://bbs.com/forum.php?mod=viewthread&tid=12345", ["tid=(\\d+)", "id=(\\d+)"])
        self.assertEqual(tid, "12345")

    def test_extract_id_fallback_md5(self):
        parser = BBSParser()
        tid = parser._extract_id("https://bbs.com/page/foo", ["tid=(\\d+)"])
        self.assertEqual(len(tid), 16)
        self.assertTrue(tid.isalnum())


class TestBaseParserImageHelpers(unittest.TestCase):
    """_get_image_url / _extract_images_from_soup / _is_valid_image_url"""

    def test_get_image_url_src(self):
        parser = BBSParser()
        soup = BeautifulSoup("<img src='https://x.com/1.jpg' />", "html.parser")
        url = parser._get_image_url(soup.find("img"))
        self.assertEqual(url, "https://x.com/1.jpg")

    def test_get_image_url_data_src(self):
        parser = BBSParser()
        soup = BeautifulSoup("<img data-src='https://x.com/2.png' />", "html.parser")
        url = parser._get_image_url(soup.find("img"))
        self.assertEqual(url, "https://x.com/2.png")

    def test_get_image_url_none(self):
        parser = BBSParser()
        soup = BeautifulSoup("<img />", "html.parser")
        url = parser._get_image_url(soup.find("img"))
        self.assertIsNone(url)

    def test_is_valid_image_url_true_extension(self):
        parser = BBSParser()
        self.assertTrue(parser._is_valid_image_url("https://cdn.com/a.jpg"))
        self.assertTrue(parser._is_valid_image_url("https://cdn.com/b.png"))

    def test_is_valid_image_url_true_keyword(self):
        parser = BBSParser()
        self.assertTrue(parser._is_valid_image_url("https://cdn.com/path/image/123"))

    def test_is_valid_image_url_false_empty(self):
        parser = BBSParser()
        self.assertFalse(parser._is_valid_image_url(""))

    def test_is_valid_image_url_false_invalid(self):
        parser = BBSParser()
        self.assertFalse(parser._is_valid_image_url("not-a-url"))

    def test_is_valid_image_url_false_no_extension_no_keyword(self):
        """无扩展名且无关键词时返回 False"""
        parser = BBSParser()
        self.assertFalse(parser._is_valid_image_url("https://cdn.com/page"))

    def test_is_valid_image_url_invalid_input_returns_false(self):
        """无效输入（如 None）导致 urlparse 异常时返回 False"""
        parser = BBSParser()
        self.assertFalse(parser._is_valid_image_url(None))

    def test_is_valid_image_url_non_string_causes_exception_returns_false(self):
        """非字符串（如 int）导致 urlparse 异常时返回 False"""
        parser = BBSParser()
        self.assertFalse(parser._is_valid_image_url(123))

    def test_extract_images_from_soup(self):
        parser = BBSParser()
        html = """
        <div>
            <img src="https://a.com/1.jpg" />
            <img src="/relative/2.png" />
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        urls = parser._extract_images_from_soup(soup, ["img"], "https://base.com/")
        self.assertIn("https://a.com/1.jpg", urls)
        self.assertIn("https://base.com/relative/2.png", urls)
        self.assertEqual(len(urls), 2)
