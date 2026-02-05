"""
动态页面解析器
用于解析使用Ajax异步加载内容的动态网页
"""
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from loguru import logger

from core.parser import BBSParser


class DynamicPageParser(BBSParser):
    """
    动态页面解析器
    
    专门用于解析通过Ajax/JavaScript动态加载内容的网页，
    如新闻列表、公告页面等。
    
    主要功能：
    - 解析文章列表
    - 提取文章基本信息（标题、作者、日期、摘要、链接）
    - 检测"查看更多"按钮及其加载参数
    - 支持多种日期格式（相对时间、绝对时间）
    
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
        super().__init__()
        
        # 保存config引用
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
        
        Example:
            articles = parser.parse_articles(html)
            # [
            #   {
            #     'article_id': '15537',
            #     'title': '许愿树和一锤定音即将开启！',
            #     'author': '《神仙道》运营团队',
            #     'date': '5天前',
            #     'summary': '亲爱的仙友们...',
            #     'url': 'https://sxd.xd.com/15537'
            #   },
            #   ...
            # ]
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
        """
        从单个文章元素中提取信息
        
        Args:
            element: BeautifulSoup元素对象
        
        Returns:
            文章信息字典，如果提取失败返回None
        """
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
        
        # 提取链接
        link_elem = element.select_one(self.link_selector)
        url = link_elem.get('href') if link_elem else None
        
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
        """
        从URL中提取文章ID
        
        Args:
            url: 文章URL
        
        Returns:
            文章ID字符串
        
        Example:
            'https://sxd.xd.com/15537' -> '15537'
            '/article/15537' -> '15537'
            '/news?id=15537' -> '15537'
        """
        import re
        
        # 尝试多种模式
        patterns = [
            r'/(\d+)/?$',           # 末尾的数字: /15537
            r'/(\d+)[?&#]',         # 数字后跟参数: /15537?xx
            r'[?&]id=(\d+)',        # URL参数: ?id=15537
            r'[?&]article_id=(\d+)', # URL参数: ?article_id=15537
            r'/article/(\d+)',      # 路径中: /article/15537
            r'/news/(\d+)',         # 路径中: /news/15537
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 如果都不匹配，使用URL的MD5
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def has_load_more_button(self, html: str) -> bool:
        """
        检查页面是否还有"查看更多"按钮
        
        Args:
            html: HTML内容
        
        Returns:
            如果存在"查看更多"按钮返回True，否则False
        
        Example:
            if parser.has_load_more_button(html):
                print("还有更多内容可以加载")
        """
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
        """
        获取下一页的页码
        
        从"查看更多"按钮的data-page属性中提取页码。
        
        Args:
            html: HTML内容
        
        Returns:
            下一页页码，如果没有返回None
        
        Example:
            next_page = parser.get_next_page_number(html)
            if next_page:
                url = f"{base_url}?page={next_page}"
        """
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
        """
        解析文章详情页
        
        Args:
            html: 文章详情页HTML
            url: 文章URL
        
        Returns:
            文章详情字典，包含完整内容和图片列表
        """
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
            # 以下是备选，可能包含过多内容
            # '.widget_body',           # 可能包含整个页面
            # '.block-body',            # 可能包含整个页面
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                logger.info(f"✓ 找到内容容器: {selector}")
                # 打印容器的前100个字符，用于调试
                text = content_elem.get_text(strip=True)[:100]
                logger.info(f"   容器内容预览: {text}...")
                
                # 调试图片数量
                imgs = content_elem.find_all('img')
                logger.info(f"   容器内图片数: {len(imgs)}")
                break
        
        if not content_elem:
            # 如果没有找到特定容器，使用整个body
            content_elem = soup.find('body')
            logger.info("⚠️  未找到特定容器，使用整个body作为内容")
            
            if content_elem:
                imgs = content_elem.find_all('img')
                logger.info(f"   Body内图片数: {len(imgs)}")
        
        # 提取文本内容
        content = content_elem.get_text(strip=True) if content_elem else ""
        
        # 提取图片
        images = []
        if content_elem:
            img_tags = content_elem.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src:
                    # 转换为完整URL
                    if not src.startswith('http'):
                        base_url = self.config.bbs.base_url
                        if src.startswith('/'):
                            src = f"{base_url}{src}"
                        else:
                            src = f"{base_url}/{src}"
                    images.append(src)
        
        logger.debug(f"✓ 提取到 {len(images)} 张图片")
        
        # 提取文章ID
        article_id = self._extract_article_id(url)
        
        return {
            'article_id': article_id,
            'url': url,
            'content': content,
            'images': images
        }
