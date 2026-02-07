"""
SelectorDetector 单元测试
"""
import unittest
from detector.selector_detector import SelectorDetector


class TestSelectorDetector(unittest.TestCase):
    """SelectorDetector 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.detector = SelectorDetector()
    
    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.detector.confidence_threshold, 0.7)
    
    def test_detect_forum_type_discuz(self):
        """测试检测 Discuz 论坛"""
        html = '<html><body>Powered by Discuz!</body></html>'
        forum_type = self.detector.detect_forum_type(html, "https://test.com")
        self.assertEqual(forum_type, "discuz")
    
    def test_detect_forum_type_phpbb(self):
        """测试检测 phpBB 论坛"""
        html = '<html><body>Powered by phpBB</body></html>'
        forum_type = self.detector.detect_forum_type(html, "https://test.com")
        self.assertEqual(forum_type, "phpbb")
    
    def test_detect_forum_type_vbulletin(self):
        """测试检测 vBulletin 论坛"""
        html = '<html><body>vBulletin</body></html>'
        forum_type = self.detector.detect_forum_type(html, "https://test.com")
        self.assertEqual(forum_type, "vbulletin")
    
    def test_detect_forum_type_custom(self):
        """测试检测自定义论坛"""
        html = '<html><body>Custom Forum</body></html>'
        forum_type = self.detector.detect_forum_type(html, "https://test.com")
        self.assertEqual(forum_type, "custom")
    
    def test_detect_thread_list_selector_discuz(self):
        """测试检测 Discuz 帖子列表选择器"""
        html = '''
        <html>
        <body>
            <tbody id="normalthread_1"></tbody>
            <tbody id="normalthread_2"></tbody>
            <tbody id="stickthread_1"></tbody>
        </body>
        </html>
        '''
        selector, confidence = self.detector.detect_thread_list_selector(html, "discuz")
        self.assertIsNotNone(selector)
        self.assertGreater(confidence, 0)
    
    def test_detect_image_selector(self):
        """测试检测图片选择器"""
        html = '''
        <html>
        <body>
            <div class="content">
                <img src="test1.jpg" class="post-image" />
                <img src="test2.jpg" class="post-image" />
            </div>
        </body>
        </html>
        '''
        selector, confidence = self.detector.detect_image_selector(html)
        self.assertIsNotNone(selector)
        self.assertGreater(confidence, 0)
    
    def test_detect_next_page_selector(self):
        """测试检测下一页选择器"""
        html = '''
        <html>
        <body>
            <a href="?page=2" class="next">下一页</a>
        </body>
        </html>
        '''
        selector, confidence = self.detector.detect_next_page_selector(html)
        self.assertIsNotNone(selector)
        self.assertGreater(confidence, 0)
    
    def test_is_content_image(self):
        """测试判断是否是内容图片"""
        from bs4 import BeautifulSoup
        
        # 内容图片
        img1 = BeautifulSoup('<img src="photo.jpg" width="500" height="300" />', 'lxml').find('img')
        self.assertTrue(self.detector._is_content_image(img1))
        
        # 头像图片
        img2 = BeautifulSoup('<img src="avatar.jpg" />', 'lxml').find('img')
        self.assertFalse(self.detector._is_content_image(img2))
        
        # 小图标
        img3 = BeautifulSoup('<img src="icon.jpg" width="50" height="50" />', 'lxml').find('img')
        self.assertFalse(self.detector._is_content_image(img3))

    def test_auto_detect_selectors(self):
        """测试 auto_detect_selectors 完整流程"""
        html = """
        <html><head><meta name="generator" content="Discuz!" /></head>
        <body>
            <tbody id="normalthread_1"><tr><td><a href="/thread/1" class="s xst">帖1</a></td></tr></tbody>
            <tbody id="normalthread_2"><tr><td><a href="/thread/2" class="xst">帖2</a></td></tr></tbody>
            <div class="content"><img src="a.jpg" width="200" /><img src="b.jpg" /></div>
            <a href="?page=2" class="nxt">下一页</a>
        </body>
        </html>
        """
        result = self.detector.auto_detect_selectors(html, "https://bbs.example.com/forum/1")
        self.assertIn("forum_type", result)
        self.assertIn("selectors", result)
        self.assertIn("thread_list_selector", result["selectors"])
        self.assertIn("thread_link_selector", result["selectors"])
        self.assertIn("image_selector", result["selectors"])
        self.assertIn("next_page_selector", result["selectors"])
        self.assertIn("confidence", result)
        self.assertIn("overall", result["confidence"])
        self.assertIn(result["status"], ("success", "uncertain"))


if __name__ == '__main__':
    unittest.main()
