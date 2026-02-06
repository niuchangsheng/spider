"""
解析器基类模块

包含解析器的抽象基类：
- BaseParser: 解析器基类
"""
import re
import hashlib
from abc import ABC
from typing import List, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


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
