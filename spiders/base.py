"""
爬虫基类模块

包含爬虫的抽象基类：
- BaseSpider: 爬虫基类
"""
import asyncio
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger
from fake_useragent import UserAgent

from config import Config


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
