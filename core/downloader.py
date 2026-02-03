"""
图片下载器模块
"""
import aiohttp
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
from fake_useragent import UserAgent
from PIL import Image
import io
from datetime import datetime

from config import config


class ImageDownloader:
    """图片下载器"""
    
    def __init__(self):
        self.config = config.image
        self.crawler_config = config.crawler
        self.ua = UserAgent()
        self.session: Optional[aiohttp.ClientSession] = None
        self.download_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init_session(self):
        """初始化HTTP会话"""
        timeout = aiohttp.ClientTimeout(total=self.crawler_config.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("Image downloader initialized")
    
    async def close(self):
        """关闭会话"""
        if self.session:
            await self.session.close()
            logger.info(f"Download stats: {self.download_stats}")
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "User-Agent": self.ua.random if self.crawler_config.rotate_user_agent else self.ua.chrome,
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": config.bbs.base_url,
        }
        return headers
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def download_image(
        self,
        url: str,
        save_path: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
            metadata: 元数据（板块、帖子ID等）
        
        Returns:
            下载结果字典
        """
        self.download_stats["total"] += 1
        
        try:
            logger.debug(f"Downloading image: {url}")
            
            # 发起请求
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
                
                # 读取图片数据
                image_data = await response.read()
                
                # 验证图片
                if not self._validate_image(image_data, url):
                    self.download_stats["skipped"] += 1
                    return {
                        "success": False,
                        "url": url,
                        "reason": "validation_failed"
                    }
                
                # 处理图片
                processed_data = await self._process_image(image_data)
                
                # 保存图片
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(processed_data)
                
                file_size = len(processed_data)
                self.download_stats["success"] += 1
                
                logger.success(f"Downloaded: {save_path.name} ({file_size} bytes)")
                
                return {
                    "success": True,
                    "url": url,
                    "save_path": str(save_path),
                    "file_size": file_size,
                    "metadata": metadata or {},
                    "download_time": datetime.now().isoformat()
                }
        
        except Exception as e:
            self.download_stats["failed"] += 1
            logger.error(f"Failed to download {url}: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e)
            }
    
    def _validate_image(self, image_data: bytes, url: str) -> bool:
        """验证图片"""
        try:
            # 检查文件大小
            if len(image_data) < self.config.min_size:
                logger.debug(f"Image too small: {url}")
                return False
            
            if len(image_data) > self.config.max_size:
                logger.debug(f"Image too large: {url}")
                return False
            
            # 检查图片格式和尺寸
            img = Image.open(io.BytesIO(image_data))
            
            # 检查尺寸
            if img.width < self.config.min_width or img.height < self.config.min_height:
                logger.debug(f"Image dimensions too small: {url} ({img.width}x{img.height})")
                return False
            
            # 检查格式
            img_format = img.format.lower() if img.format else ""
            if img_format not in self.config.allowed_formats:
                logger.debug(f"Image format not allowed: {url} ({img_format})")
                return False
            
            return True
        
        except Exception as e:
            logger.warning(f"Image validation error: {url} - {e}")
            return False
    
    async def _process_image(self, image_data: bytes) -> bytes:
        """处理图片（压缩、转换等）"""
        if not (self.config.compress_images or self.config.convert_to_jpg):
            return image_data
        
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # 转换RGBA到RGB（如果需要保存为JPG）
            if self.config.convert_to_jpg and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # 保存到字节流
            output = io.BytesIO()
            save_format = 'JPEG' if self.config.convert_to_jpg else img.format
            save_kwargs = {}
            
            if save_format == 'JPEG':
                save_kwargs['quality'] = self.config.quality
                save_kwargs['optimize'] = True
            
            img.save(output, format=save_format, **save_kwargs)
            return output.getvalue()
        
        except Exception as e:
            logger.warning(f"Image processing error: {e}, using original")
            return image_data
    
    async def download_batch(
        self,
        image_urls: list,
        save_dir: Path,
        metadata: Optional[Dict[str, Any]] = None
    ) -> list:
        """
        批量下载图片
        
        Args:
            image_urls: 图片URL列表
            save_dir: 保存目录
            metadata: 元数据
        
        Returns:
            下载结果列表
        """
        if not image_urls:
            return []
        
        save_dir.mkdir(parents=True, exist_ok=True)
        
        tasks = []
        for idx, url in enumerate(image_urls, 1):
            # 生成文件名
            filename = self._generate_filename(url, idx, metadata)
            save_path = save_dir / filename
            
            # 创建下载任务
            task = self.download_image(url, save_path, metadata)
            tasks.append(task)
            
            # 添加延迟（避免过于频繁的请求）
            if idx < len(image_urls):
                await asyncio.sleep(self.crawler_config.download_delay)
        
        # 并发下载（带限制）
        semaphore = asyncio.Semaphore(self.crawler_config.max_concurrent_requests)
        
        async def download_with_semaphore(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(
            *[download_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        return [r for r in results if not isinstance(r, Exception)]
    
    def _generate_filename(
        self,
        url: str,
        index: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成文件名"""
        # 从URL提取文件扩展名
        ext = url.split('.')[-1].split('?')[0].lower()
        if ext not in self.config.allowed_formats:
            ext = 'jpg'
        
        # 如果启用了转换为JPG
        if self.config.convert_to_jpg:
            ext = 'jpg'
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if metadata:
            board = metadata.get('board', 'unknown')
            thread_id = metadata.get('thread_id', 'unknown')
            filename = f"{board}_{thread_id}_{index:03d}_{timestamp}.{ext}"
        else:
            filename = f"image_{index:03d}_{timestamp}.{ext}"
        
        return filename
    
    def get_stats(self) -> Dict[str, int]:
        """获取下载统计"""
        return self.download_stats.copy()
