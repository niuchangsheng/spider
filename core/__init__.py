"""
核心模块

包含基础组件：
- downloader: 图片下载器
- storage: 数据存储
- deduplicator: 图片去重器
- checkpoint: 检查点管理器（断点续传）
- crawl_queue: 异步任务队列（性能优化）
- base: 基类（BaseSpider, BaseParser）
"""
from .downloader import ImageDownloader
from .storage import Storage
from .deduplicator import ImageDeduplicator
from .checkpoint import CheckpointManager, get_checkpoint_manager
from .crawl_queue import CrawlQueue, AdaptiveCrawlQueue

__all__ = [
    'ImageDownloader',
    'Storage',
    'ImageDeduplicator',
    'CheckpointManager',
    'get_checkpoint_manager',
    'CrawlQueue',
    'AdaptiveCrawlQueue'
]
