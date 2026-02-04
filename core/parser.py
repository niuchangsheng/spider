"""
BBS页面解析器模块
"""
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
from loguru import logger

from config import config


class BBSParser:
    """BBS页面解析器"""
    
    def __init__(self):
        self.config = config.bbs
    
    def parse_thread_list(self, html: str, base_url: str) -> List[Dict[str, Any]]:
        """
        解析帖子列表页
        
        Args:
            html: HTML内容
            base_url: 基础URL
        
        Returns:
            帖子列表
        """
        soup = BeautifulSoup(html, 'lxml')
        threads = []
        
        try:
            # 查找所有帖子元素
            thread_elements = soup.select(self.config.thread_list_selector)
            
            for element in thread_elements:
                try:
                    thread = self._parse_thread_item(element, base_url)
                    if thread:
                        threads.append(thread)
                except Exception as e:
                    logger.warning(f"Failed to parse thread item: {e}")
                    continue
            
            logger.info(f"Parsed {len(threads)} threads from list page")
        
        except Exception as e:
            logger.error(f"Failed to parse thread list: {e}")
        
        return threads
    
    def _parse_thread_item(self, element, base_url: str) -> Optional[Dict[str, Any]]:
        """解析单个帖子项"""
        # 获取帖子链接
        link_element = element.select_one(self.config.thread_link_selector)
        if not link_element:
            return None
        
        thread_url = link_element.get('href')
        if not thread_url:
            return None
        
        # 处理相对路径
        thread_url = urljoin(base_url, thread_url)
        
        # 提取帖子ID（从URL中）
        thread_id = self._extract_thread_id(thread_url)
        
        # 提取帖子标题
        title = link_element.get_text(strip=True)
        
        return {
            "thread_id": thread_id,
            "title": title,
            "url": thread_url,
        }
    
    def parse_thread_page(self, html: str, thread_url: str) -> Dict[str, Any]:
        """
        解析帖子详情页
        
        Args:
            html: HTML内容
            thread_url: 帖子URL
        
        Returns:
            帖子数据（包含图片链接）
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # 提取图片
        images = self._extract_images(soup, thread_url)
        
        # 提取帖子元数据
        metadata = self._extract_metadata(soup)
        
        # 提取内容
        content = self._extract_content(soup)
        
        result = {
            "url": thread_url,
            "thread_id": self._extract_thread_id(thread_url),
            "images": images,
            "metadata": metadata,
            "content": content,
            "image_count": len(images)
        }
        
        logger.info(f"Parsed thread page: {result['thread_id']}, found {len(images)} images")
        
        return result
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取图片链接"""
        images = []
        image_elements = soup.select(self.config.image_selector)
        
        for img in image_elements:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if not src:
                continue
            
            # 处理相对路径
            img_url = urljoin(base_url, src)
            
            # 验证URL
            if self._is_valid_image_url(img_url):
                images.append(img_url)
        
        # 去重
        images = list(dict.fromkeys(images))
        
        return images
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """提取帖子元数据"""
        metadata = {}
        
        try:
            # 提取作者
            author_element = soup.select_one('.author, .username, [class*="author"]')
            if author_element:
                metadata['author'] = author_element.get_text(strip=True)
            
            # 提取发布时间
            time_element = soup.select_one('.post-time, .time, [class*="time"]')
            if time_element:
                metadata['post_time'] = time_element.get_text(strip=True)
            
            # 提取浏览数
            views_element = soup.select_one('.views, [class*="view"]')
            if views_element:
                views_text = views_element.get_text(strip=True)
                metadata['views'] = self._extract_number(views_text)
            
            # 提取回复数
            replies_element = soup.select_one('.replies, [class*="reply"]')
            if replies_element:
                replies_text = replies_element.get_text(strip=True)
                metadata['replies'] = self._extract_number(replies_text)
        
        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
        
        return metadata
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """提取帖子内容"""
        try:
            content_element = soup.select_one('.post-content, .content, article')
            if content_element:
                return content_element.get_text(strip=True, separator='\n')
        except Exception as e:
            logger.warning(f"Failed to extract content: {e}")
        
        return ""
    
    def _extract_thread_id(self, url: str) -> str:
        """从URL中提取帖子ID"""
        # 尝试多种模式
        patterns = [
            r'/thread[/-](\d+)',
            r'/t[/-](\d+)',
            r'tid=(\d+)',
            r'id=(\d+)',
            r'/(\d+)\.html',
            r'/(\d+)$',  # URL末尾的数字（如：https://sxd.xd.com/15486）
            r'/(\d+)[/?]',  # 数字后跟 / 或 ?
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 如果无法提取，使用URL的hash值（取绝对值避免负数）
        hash_value = abs(hash(url))
        logger.warning(f"无法从URL提取thread_id，使用hash: {url} -> {hash_value}")
        return str(hash_value)
    
    def _extract_number(self, text: str) -> int:
        """从文本中提取数字"""
        match = re.search(r'\d+', text.replace(',', ''))
        return int(match.group(0)) if match else 0
    
    def _is_valid_image_url(self, url: str) -> bool:
        """验证图片URL"""
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
        image_extensions = self.config.allowed_formats if hasattr(self.config, 'allowed_formats') else [
            'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'
        ]
        
        url_lower = url.lower()
        
        # 检查扩展名
        if any(url_lower.endswith(f'.{ext}') for ext in image_extensions):
            return True
        
        # 检查URL中是否包含图片相关关键词
        if any(keyword in url_lower for keyword in ['image', 'img', 'photo', 'pic']):
            return True
        
        return False
    
    def find_next_page(self, html: str, current_url: str) -> Optional[str]:
        """查找下一页链接"""
        soup = BeautifulSoup(html, 'lxml')
        
        try:
            next_element = soup.select_one(self.config.next_page_selector)
            if next_element:
                next_url = next_element.get('href')
                if next_url:
                    return urljoin(current_url, next_url)
        except Exception as e:
            logger.warning(f"Failed to find next page: {e}")
        
        return None
