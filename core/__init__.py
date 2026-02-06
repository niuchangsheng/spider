"""
核心模块

包含基础组件：
- downloader: 图片下载器
- storage: 数据存储
- deduplicator: 图片去重器
- base: 基类（BaseSpider, BaseParser）
"""
from .downloader import ImageDownloader
from .storage import Storage
from .deduplicator import ImageDeduplicator

__all__ = [
    'ImageDownloader',
    'Storage',
    'ImageDeduplicator'
]
