"""
基类模块

包含所有爬虫和解析器的抽象基类：
- BaseParser: 解析器基类
- BaseSpider: 爬虫基类
"""
import asyncio
import aiohttp
import re
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger
from fake_useragent import UserAgent

from config import Config


# ============================================================================
# 解析器基类
# ============================================================================

class BaseParser(ABC):
    """
    解析器基类
    
    所有解析器的公共基类，提供：
    - 基础HTML解析
    - URL处理
    - 图片提取
    - ID提取
    
    子类需要实现:
    - parse(): 解析页面的主方法（可选）
    """
    
    def __init__(self, parser_config=None):
        """
        初始化解析器
        
        Args:
            parser_config: 配置对象，可选
        """
        self._config = parser_config
    
    def _extract_id(self, url: str, patterns: List[str]) -> str:
        """
        从URL中提取ID
        
        Args:
            url: 页面URL
            patterns: 正则表达式列表
        
        Returns:
            提取的ID，失败返回URL的MD5哈希（前16位）
        """
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 回退：使用URL的MD5
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _extract_images_from_soup(
        self, 
        soup: BeautifulSoup, 
        selectors: List[str], 
        base_url: str
    ) -> List[str]:
        """
        从HTML中提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            selectors: CSS选择器列表
            base_url: 基础URL（用于处理相对路径）
        
        Returns:
            图片URL列表（已去重）
        """
        images = []
        for selector in selectors:
            for img in soup.select(selector):
                src = self._get_image_url(img)
                if src:
                    # 处理相对路径
                    if not src.startswith('http'):
                        src = urljoin(base_url, src)
                    # 去重
                    if src not in images:
                        images.append(src)
        return images
    
    def _get_image_url(self, img_tag) -> Optional[str]:
        """
        从img标签获取图片URL
        
        子类可重写此方法实现特定的图片URL提取逻辑
        （如：获取原图、处理懒加载等）
        
        Args:
            img_tag: BeautifulSoup img标签
        
        Returns:
            图片URL，如果无法获取返回None
        """
        return img_tag.get('src') or img_tag.get('data-src') or img_tag.get('data-original')
    
    def _is_valid_image_url(self, url: str, allowed_formats: Optional[List[str]] = None) -> bool:
        """
        验证图片URL是否有效
        
        Args:
            url: 图片URL
            allowed_formats: 允许的图片格式列表
        
        Returns:
            URL是否有效
        """
        if not url:
            return False
        
        # 检查是否是有效的URL
        try:
            result = urlparse(url)
            if not result.scheme or not result.netloc:
                return False
        except:
            return False
        
        # 检查是否是图片文件
        image_extensions = allowed_formats or ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        url_lower = url.lower()
        
        # 检查扩展名
        if any(url_lower.endswith(f'.{ext}') for ext in image_extensions):
            return True
        
        # 检查URL中是否包含图片相关关键词
        if any(keyword in url_lower for keyword in ['image', 'img', 'photo', 'pic', 'attachment']):
            return True
        
        return False


# ============================================================================
# 爬虫基类
# ============================================================================

class BaseSpider(ABC):
    """
    爬虫基类
    
    所有爬虫的公共基类，提供：
    - HTTP Session 管理
    - 页面获取
    - 统计信息
    - 异步上下文管理
    
    子类需要实现:
    - get_statistics(): 获取统计信息
    """
    
    def __init__(self, config: Config):
        """
        初始化爬虫
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.ua = UserAgent()
        
        # 基础统计信息
        self.stats = {
            'pages_fetched': 0,
            'requests_failed': 0,
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init(self):
        """
        初始化爬虫
        
        子类应该调用 super().init() 并添加特定初始化逻辑
        """
        logger.info("⚙️  初始化爬虫组件...")
        
        # 初始化HTTP会话
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """
        关闭爬虫
        
        子类应该先执行特定清理逻辑，再调用 super().close()
        """
        logger.info("🔒 关闭爬虫...")
        
        if self.session:
            await self.session.close()
        
        logger.info(f"📊 爬虫统计: {self.get_statistics()}")
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        
        子类可重写此方法添加特定请求头
        """
        headers = {
            "User-Agent": self.ua.random if self.config.crawler.rotate_user_agent else self.ua.chrome,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
        
        if self.config.bbs.base_url:
            headers["Referer"] = self.config.bbs.base_url
        
        return headers
    
    async def fetch_page(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            headers: 可选的额外请求头
        
        Returns:
            HTML内容，失败返回None
        """
        try:
            logger.debug(f"📄 获取页面: {url}")
            
            request_headers = self.get_headers()
            if headers:
                request_headers.update(headers)
            
            async with self.session.get(url, headers=request_headers) as response:
                if response.status == 200:
                    self.stats['pages_fetched'] += 1
                    html = await response.text()
                    await asyncio.sleep(self.config.crawler.download_delay)
                    return html
                else:
                    logger.warning(f"⚠️  获取失败 {url}: HTTP {response.status}")
                    return None
        
        except asyncio.TimeoutError:
            self.stats['requests_failed'] += 1
            logger.error(f"❌ 超时: {url}")
            return None
        except Exception as e:
            self.stats['requests_failed'] += 1
            logger.error(f"❌ 获取出错 {url}: {e}")
            return None
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        子类必须实现此方法
        """
        pass
