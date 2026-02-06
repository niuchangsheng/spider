"""
动态页面解析器
用于解析使用Ajax异步加载内容的动态网页
"""
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from loguru import logger
import re

from parsers.base import BaseParser


class DynamicPageParser(BaseParser):
    """
    动态页面解析器
    
    继承 BaseParser，添加动态页面特有功能：
    - 解析文章列表
    - 提取文章基本信息（标题、作者、日期、摘要、链接）
    - 检测"查看更多"按钮及其加载参数
    - 支持多种日期格式（相对时间、绝对时间）
    - 原图URL智能提取
    
    Example:
        parser = DynamicPageParser(config)
        articles = parser.parse_articles(html)
        has_more = parser.has_load_more_button(html)
    """
    
    def __init__(self, config):
        """
        初始化动态页面解析器
        
        Args:
            config: 配置对象，包含选择器等信息
        """
        super().__init__(config)
        
        # 保存config引用（动态页面需要完整config）
        self.config = config
        
        # 默认文章选择器（可通过配置覆盖）
        self.article_selector = getattr(config.bbs, 'article_selector', '.article')
        self.title_selector = getattr(config.bbs, 'title_selector', '.title')
        self.author_selector = getattr(config.bbs, 'author_selector', '.author')
        self.date_selector = getattr(config.bbs, 'date_selector', '.date')
        self.summary_selector = getattr(config.bbs, 'summary_selector', '.body')
        self.link_selector = getattr(config.bbs, 'link_selector', 'a[href]')
        
        logger.debug(f"🔧 动态页面解析器初始化完成")
        logger.debug(f"   文章选择器: {self.article_selector}")
    
    def parse_articles(self, html: str) -> List[Dict]:
        """
        解析文章列表
        
        从HTML中提取所有文章的基本信息。
        
        Args:
            html: HTML内容
        
        Returns:
            文章信息列表，每个文章是一个字典，包含：
            - article_id: 文章ID
            - title: 标题
            - author: 作者
            - date: 发布日期
            - summary: 摘要
            - url: 详情链接
        """
        soup = BeautifulSoup(html, 'html.parser')
        articles = []
        
        # 查找所有文章元素
        article_elements = soup.select(self.article_selector)
        
        logger.debug(f"🔍 找到 {len(article_elements)} 个文章元素")
        
        for i, elem in enumerate(article_elements, 1):
            try:
                article = self._extract_article_info(elem)
                if article:
                    articles.append(article)
                    logger.debug(f"   ✓ 文章 #{i}: {article.get('title', 'N/A')[:30]}")
                else:
                    logger.debug(f"   ✗ 文章 #{i}: 提取失败（缺少必要字段）")
            except Exception as e:
                logger.error(f"❌ 解析文章 #{i} 失败: {e}")
                continue
        
        logger.info(f"📄 成功解析 {len(articles)}/{len(article_elements)} 篇文章")
        
        return articles
    
    def _extract_article_info(self, element) -> Optional[Dict]:
        """从单个文章元素中提取信息"""
        # 提取标题
        title_elem = element.select_one(self.title_selector)
        title = title_elem.get_text(strip=True) if title_elem else None
        
        # 提取作者
        author_elem = element.select_one(self.author_selector)
        author = author_elem.get_text(strip=True) if author_elem else "未知作者"
        
        # 提取日期
        date_elem = element.select_one(self.date_selector)
        date = date_elem.get_text(strip=True) if date_elem else None
        
        # 提取摘要
        summary_elem = element.select_one(self.summary_selector)
        summary = summary_elem.get_text(strip=True) if summary_elem else ""
        
        # 提取链接（优先从标题中提取，避免提取到图片链接）
        url = None
        
        # 方法1: 从标题元素中提取链接（最可靠）
        if title_elem:
            title_link = title_elem.find('a', href=True)
            if title_link:
                url = title_link.get('href')
        
        # 方法2: 如果标题中没有链接，使用link_selector
        if not url:
            link_elem = element.select_one(self.link_selector)
            if link_elem:
                candidate_url = link_elem.get('href', '')
                # 排除图片链接（包含图片扩展名或图片域名）
                if candidate_url and not any(ext in candidate_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'res.xdcdn.net']):
                    url = candidate_url
        
        # 方法3: 如果还是没有，尝试查找所有链接，选择最像文章链接的
        if not url:
            all_links = element.select('a[href]')
            for link in all_links:
                href = link.get('href', '')
                # 排除图片链接
                if any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'res.xdcdn.net']):
                    continue
                # 优先选择包含数字的链接（可能是文章ID）
                if href and any(c.isdigit() for c in href):
                    url = href
                    break
            # 如果还是没有，使用第一个非图片链接
            if not url and all_links:
                for link in all_links:
                    href = link.get('href', '')
                    if not any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', 'res.xdcdn.net']):
                        url = href
                        break
        
        # 验证必需字段
        if not title or not url:
            logger.debug(f"   ⚠️  缺少必需字段: title={bool(title)}, url={bool(url)}")
            return None
        
        # 提取文章ID（从URL中）
        article_id = self._extract_article_id(url)
        
        # 确保URL是完整的
        if url and not url.startswith('http'):
            base_url = self.config.bbs.base_url
            if url.startswith('/'):
                url = f"{base_url}{url}"
            else:
                url = f"{base_url}/{url}"
        
        return {
            'article_id': article_id,
            'title': title,
            'author': author,
            'date': date,
            'summary': summary,
            'url': url
        }
    
    def _extract_article_id(self, url: str) -> str:
        """从URL中提取文章ID"""
        patterns = [
            r'/(\d+)/?$',           # 末尾的数字: /15537
            r'/(\d+)[?&#]',         # 数字后跟参数: /15537?xx
            r'[?&]id=(\d+)',        # URL参数: ?id=15537
            r'[?&]article_id=(\d+)', # URL参数: ?article_id=15537
            r'/article/(\d+)',      # 路径中: /article/15537
            r'/news/(\d+)',         # 路径中: /news/15537
        ]
        return self._extract_id(url, patterns)
    
    def has_load_more_button(self, html: str) -> bool:
        """检查页面是否还有"查看更多"按钮"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找"查看更多"按钮（多种可能的选择器）
        load_more_selectors = [
            'a.more[data-action="switch_page"]',  # 神仙道官网格式
            'a.load-more',                        # 通用格式1
            'button.load-more',                   # 通用格式2
            '[data-action*="load"]',              # 包含load的data-action
            '[data-action*="more"]',              # 包含more的data-action
        ]
        
        for selector in load_more_selectors:
            element = soup.select_one(selector)
            if element:
                logger.debug(f"✓ 找到'查看更多'按钮: {selector}")
                return True
        
        # 也检查文本内容
        more_texts = ['查看更多', 'load more', '加载更多', 'show more', '更多']
        for text in more_texts:
            if soup.find(string=lambda t: text in t.lower() if t else False):
                logger.debug(f"✓ 找到'查看更多'文本: {text}")
                return True
        
        logger.debug("✗ 未找到'查看更多'按钮")
        return False
    
    def get_next_page_number(self, html: str) -> Optional[int]:
        """获取下一页的页码"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找带有data-page属性的元素
        load_more = soup.select_one('[data-page]')
        if load_more:
            try:
                page_num = int(load_more.get('data-page'))
                logger.debug(f"✓ 下一页页码: {page_num}")
                return page_num
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️  无法解析页码: {e}")
                return None
        
        logger.debug("✗ 未找到data-page属性")
        return None
    
    def parse_article_detail(self, html: str, url: str) -> Dict:
        """解析文章详情页"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找文章内容容器（按优先级排序，越精确的选择器越靠前）
        content_selectors = [
            '.article .body',           # 神仙道官网 - 文章正文（最精确）
            '#single .article .body',   # 神仙道官网 - 带ID的更精确选择器
            '.article-body',            # 常见变体
            '.article-content',         # 常见变体
            '.post-body',               # 博客类
            '.post-content',            # 博客类
            '.news-detail',             # 新闻类
            '.news-content',            # 新闻类
            '.detail-content',          # 详情页
            'article .content',         # HTML5 article标签
            '#content',                 # 通用ID
            '.content',                 # 通用类（可能太宽泛）
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                logger.info(f"✓ 找到内容容器: {selector}")
                text = content_elem.get_text(strip=True)[:100]
                logger.info(f"   容器内容预览: {text}...")
                imgs = content_elem.find_all('img')
                logger.info(f"   容器内图片数: {len(imgs)}")
                break
        
        if not content_elem:
            content_elem = soup.find('body')
            logger.info("⚠️  未找到特定容器，使用整个body作为内容")
            if content_elem:
                imgs = content_elem.find_all('img')
                logger.info(f"   Body内图片数: {len(imgs)}")
        
        # 提取文本内容
        content = content_elem.get_text(strip=True) if content_elem else ""
        
        # 提取图片（优先获取原图URL）
        images = []
        if content_elem:
            # 方法1: 从 <a> 标签获取原图链接
            for a_tag in content_elem.find_all('a'):
                href = a_tag.get('href', '')
                if href and any(ext in href.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    if not href.startswith('http'):
                        href = urljoin(url, href)
                    if href not in images:
                        images.append(href)
            
            # 方法2: 从 <img> 标签获取
            if not images:
                img_tags = content_elem.find_all('img')
                for img in img_tags:
                    original_src = self._get_image_url(img)
                    if original_src:
                        if not original_src.startswith('http'):
                            original_src = urljoin(url, original_src)
                        if original_src not in images:
                            images.append(original_src)
        
        logger.debug(f"✓ 提取到 {len(images)} 张图片")
        
        article_id = self._extract_article_id(url)
        
        return {
            'article_id': article_id,
            'url': url,
            'content': content,
            'images': images
        }
    
    def _get_image_url(self, img_tag) -> Optional[str]:
        """
        重写基类方法：从 img 标签获取原图 URL
        
        动态页面特有的图片提取逻辑，优先获取原图：
        1. srcset 中最大尺寸的图片
        2. data-src（懒加载原图）
        3. src（可能是缩略图）并尝试去除尺寸后缀
        """
        # 方法1: 从 srcset 获取最大尺寸的图片
        srcset = img_tag.get('srcset', '')
        if srcset:
            max_width = 0
            max_url = None
            for item in srcset.split(','):
                item = item.strip()
                if ' ' in item:
                    parts = item.rsplit(' ', 1)
                    url_part = parts[0].strip()
                    size_part = parts[1].strip()
                    width_match = re.search(r'(\d+)w', size_part)
                    if width_match:
                        width = int(width_match.group(1))
                        if width > max_width:
                            max_width = width
                            max_url = url_part
            if max_url:
                return max_url
        
        # 方法2: 从 data-src 获取（懒加载）
        data_src = img_tag.get('data-src')
        if data_src:
            return data_src
        
        # 方法3: 从 src 获取，并尝试去除尺寸后缀获取原图
        src = img_tag.get('src', '')
        if src:
            original_url = re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', src)
            return original_url
        
        return None
