"""
BBS论坛爬虫模块

包含:
- BBSSpider: BBS论坛爬虫基类
- DiscuzSpider: Discuz论坛爬虫
- PhpBBSpider: phpBB论坛爬虫
- VBulletinSpider: vBulletin论坛爬虫
"""
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
from tqdm import tqdm

from spiders.base import BaseSpider
from core.downloader import ImageDownloader
from core.storage import storage
from core.deduplicator import ImageDeduplicator
from core.checkpoint import CheckpointManager
from core.crawl_queue import CrawlQueue, AdaptiveCrawlQueue
from parsers.bbs_parser import BBSParser
from config import Config, ConfigLoader


class BBSSpider(BaseSpider):
    """
    BBS论坛图片爬虫
    
    继承 BaseSpider，添加论坛特有功能：
    - 帖子列表爬取
    - 帖子详情爬取
    - 图片下载和去重
    
    子类（如 DiscuzSpider）可重写 process_images() 实现论坛特定处理
    """
    
    def __init__(self, config: Optional[Config] = None, url: Optional[str] = None, preset: Optional[str] = None):
        """
        初始化BBS爬虫
        
        Args:
            config: 手动配置（优先级最高）
            url: 论坛URL，自动检测配置
            preset: 论坛类型预设 (discuz/phpbb/vbulletin)
        
        Note:
            推荐使用 SpiderFactory.create() 而不是直接实例化
        """
        # 配置优先级: config > preset > url
        if config:
            final_config = config
        elif preset:
            final_config = ConfigLoader.load(preset)
        elif url:
            final_config = ConfigLoader.auto_detect(url)
        else:
            raise ValueError("必须提供 config、preset 或 url 参数之一")
        
        # 调用基类初始化
        super().__init__(final_config)
        
        # BBS特有组件
        self.parser = BBSParser()
        self.deduplicator = ImageDeduplicator(use_perceptual_hash=True)
        
        # BBS特有统计信息（扩展基类stats）
        self.stats.update({
            "threads_crawled": 0,
            "images_found": 0,
            "images_downloaded": 0,
            "images_failed": 0,
            "duplicates_skipped": 0
        })
        
        logger.info(f"🚀 初始化爬虫: {self.config.bbs.name} ({self.config.bbs.forum_type})")
    
    async def init(self):
        """初始化BBS爬虫"""
        # 调用基类初始化
        await super().init()
        
        # BBS特有初始化
        storage.connect()
        
        # 加载已存在的文件哈希
        if self.config.image.enable_deduplication:
            self.deduplicator.load_existing_hashes(self.config.image.download_dir)
        
        logger.success("✅ 爬虫初始化完成")
    
    async def close(self):
        """关闭BBS爬虫"""
        # BBS特有清理
        storage.close()
        
        # 输出去重统计
        logger.info(f"🔄 去重统计: {self.deduplicator.get_stats()}")
        
        # 调用基类关闭
        await super().close()
    
    async def process_images(self, images: List[str]) -> List[str]:
        """
        处理图片URL（钩子方法）
        
        子类可重写此方法实现论坛特定的图片处理逻辑
        
        Args:
            images: 原始图片URL列表
        
        Returns:
            处理后的图片URL列表
        """
        return images
    
    async def crawl_board(
        self, 
        board_url: str, 
        board_name: str, 
        max_pages: Optional[int] = None,
        resume: bool = True,
        start_page: Optional[int] = None
    ):
        """
        爬取板块（支持断点续传）
        
        Args:
            board_url: 板块URL
            board_name: 板块名称
            max_pages: 最大页数
            resume: 是否从检查点恢复（默认True）
            start_page: 起始页码（如果指定，会覆盖检查点）
        """
        logger.info(f"📚 开始爬取板块: {board_name}")
        
        # 1. 创建检查点管理器
        checkpoint = CheckpointManager(
            site=self.config.bbs.base_url,
            board=board_name
        )
        
        # 2. 确定起始页
        start_from_checkpoint = False
        if start_page is not None:
            # 手动指定起始页（覆盖检查点）
            start_page_num = start_page
            logger.info(f"📌 手动指定起始页: {start_page_num}")
            if checkpoint.exists():
                logger.info("⚠️  将覆盖现有检查点")
        elif resume and checkpoint.exists():
            # 从检查点恢复
            checkpoint_data = checkpoint.load_checkpoint()
            if checkpoint_data:
                status = checkpoint_data.get('status', 'running')
                if status == 'completed':
                    logger.info("✅ 该板块已完成爬取，跳过")
                    return
                
                # 检查点保存的是"当前页"（刚爬完的页），恢复时从下一页开始
                checkpoint_page = checkpoint_data.get('current_page', 1)
                start_page_num = checkpoint_page
                last_thread_id = checkpoint_data.get('last_thread_id')
                logger.info(f"🔄 从检查点恢复: 第 {start_page_num} 页")
                if last_thread_id:
                    logger.info(f"   最后爬取的帖子ID: {last_thread_id}")
                start_from_checkpoint = True
            else:
                start_page_num = 1
        else:
            # 从头开始
            start_page_num = 1
        
        # 3. 从起始页开始爬取
        current_url = board_url
        page_count = 0
        last_thread_id = None
        last_thread_url = None
        
        # 如果从检查点恢复且起始页>1，需要跳转到指定页
        # 注意：不同论坛的分页方式不同，这里采用简单策略：
        # 从第一页开始，通过"下一页"链接到达指定页（会跳过已爬的帖子）
        if start_from_checkpoint and start_page_num > 1:
            logger.info(f"⏩ 从检查点恢复，需要跳转到第 {start_page_num} 页")
            logger.info(f"   提示：将从第一页开始，通过'下一页'链接到达指定页")
            logger.info(f"   已爬取的帖子会自动跳过（通过去重机制）")
        
        try:
            while current_url and (max_pages is None or page_count < max_pages):
                page_count += 1
                
                # 计算实际页码
                if start_from_checkpoint and start_page_num > 1:
                    # 从检查点恢复：前几页跳过，到达指定页后开始爬取
                    actual_page = page_count
                    if actual_page < start_page_num:
                        # 跳过已爬页，只查找下一页
                        logger.debug(f"⏭️  跳过第 {actual_page} 页（已爬取）")
                        html = await self.fetch_page(current_url)
                        if html:
                            current_url = self.parser.find_next_page(html, current_url)
                            if not current_url:
                                logger.warning("⚠️  无法找到下一页，可能已到达最后一页")
                                break
                        continue
                    actual_page = page_count
                else:
                    # 正常情况：从指定页或第1页开始
                    actual_page = start_page_num + page_count - 1 if start_page_num > 1 else page_count
                
                logger.info(f"📄 爬取第 {actual_page} 页: {current_url}")
                
                # 获取列表页
                html = await self.fetch_page(current_url)
                if not html:
                    checkpoint.mark_error("无法获取页面")
                    logger.error(f"❌ 无法获取第 {actual_page} 页")
                    break
                
                # 解析帖子列表
                threads = self.parser.parse_thread_list(html, current_url)
                logger.info(f"✅ 发现 {len(threads)} 个帖子")
                
                if not threads:
                    logger.warning(f"⚠️  第 {actual_page} 页没有找到帖子")
                    # 保存检查点后继续下一页
                    checkpoint.save_checkpoint(
                        current_page=actual_page + 1,
                        last_thread_id=last_thread_id,
                        last_thread_url=last_thread_url,
                        status="running",
                        stats={
                            "crawled_count": self.stats['threads_crawled'],
                            "failed_count": self.stats['images_failed'],
                            "images_downloaded": self.stats['images_downloaded']
                        }
                    )
                    # 查找下一页
                    current_url = self.parser.find_next_page(html, current_url)
                    if not current_url:
                        break
                    continue
                
                # 使用异步任务队列并发爬取帖子（如果启用）
                if self.config.crawler.use_async_queue:
                    # 准备任务列表
                    thread_tasks = []
                    for thread in threads:
                        thread['board'] = board_name
                        thread_tasks.append(thread)
                    
                    # 创建队列并运行
                    max_workers = self.config.crawler.max_concurrent_requests or 5
                    use_adaptive = self.config.crawler.use_adaptive_queue
                    queue_size = self.config.crawler.queue_size or 1000
                    
                    if use_adaptive:
                        queue = AdaptiveCrawlQueue(
                            initial_workers=max_workers,
                            max_workers=max_workers * 2,
                            min_workers=1,
                            queue_size=queue_size
                        )
                        logger.info(f"🎯 使用自适应队列: 初始并发={max_workers}")
                    else:
                        queue = CrawlQueue(max_workers=max_workers, queue_size=queue_size)
                        logger.info(f"🚀 使用异步队列: 并发数={max_workers}")
                    
                    # 定义工作函数
                    async def crawl_thread_task(thread_info: Dict[str, Any]):
                        """队列工作函数"""
                        await self.crawl_thread(thread_info)
                        return thread_info
                    
                    # 运行队列
                    queue_stats = await queue.run(thread_tasks, crawl_thread_task)
                    logger.info(f"📊 队列统计: {queue_stats}")
                else:
                    # 串行爬取（兼容模式）
                    logger.debug("📝 使用串行模式爬取帖子")
                    for thread in threads:
                        thread['board'] = board_name
                        await self.crawl_thread(thread)
                
                # 更新最后爬取的帖子信息
                if threads:
                    last_thread_id = threads[-1].get('thread_id')
                    last_thread_url = threads[-1].get('url')
                
                # 4. 保存检查点（每页保存一次）
                checkpoint.save_checkpoint(
                    current_page=actual_page + 1,  # 下一页
                    last_thread_id=last_thread_id,
                    last_thread_url=last_thread_url,
                    status="running",
                    stats={
                        "crawled_count": self.stats['threads_crawled'],
                        "failed_count": self.stats['images_failed'],
                        "images_downloaded": self.stats['images_downloaded']
                    }
                )
                
                # 查找下一页
                current_url = self.parser.find_next_page(html, current_url)
                if not current_url:
                    logger.info("📌 没有更多页面")
                    break
            
            # 5. 标记完成
            checkpoint.mark_completed(final_stats={
                "total_crawled": self.stats['threads_crawled'],
                "total_images": self.stats['images_downloaded'],
                "total_failed": self.stats['images_failed']
            })
            
            logger.success(f"🎉 板块爬取完成: {board_name}, 总页数: {page_count}")
            
        except Exception as e:
            # 发生错误时保存检查点
            logger.error(f"❌ 爬取过程中发生错误: {e}")
            checkpoint.mark_error(str(e))
            raise
    
    async def crawl_thread(self, thread_info: Dict[str, Any]):
        """
        爬取单个帖子
        
        Args:
            thread_info: 帖子信息字典
        """
        thread_url = thread_info['url']
        thread_id = thread_info['thread_id']
        
        # 检查是否已爬取
        if storage.thread_exists(thread_id):
            logger.info(f"⏭️  帖子 {thread_id} 已爬取，跳过")
            return
        
        logger.info(f"📝 爬取帖子: {thread_info.get('title', thread_id)}")
        
        # 获取帖子页面
        html = await self.fetch_page(thread_url)
        if not html:
            return
        
        # 解析帖子内容
        thread_data = self.parser.parse_thread_page(html, thread_url)
        thread_data['board'] = thread_info.get('board')
        thread_data['title'] = thread_info.get('title')
        
        # 论坛特定处理（策略模式 - 子类可重写）
        thread_data['images'] = await self.process_images(thread_data['images'])
        
        # 更新统计
        self.stats['threads_crawled'] += 1
        self.stats['images_found'] += len(thread_data['images'])
        
        logger.info(f"🖼️  发现 {len(thread_data['images'])} 张图片")
        
        # 下载图片
        if thread_data['images']:
            await self.download_thread_images(thread_data)
        
        # 保存帖子数据
        storage.save_thread(thread_data)
    
    async def download_thread_images(self, thread_data: Dict[str, Any]):
        """下载帖子中的图片"""
        images = thread_data['images']
        thread_id = thread_data['thread_id']
        board = thread_data.get('board', 'unknown')
        
        # 过滤重复URL
        unique_images = []
        for img_url in images:
            if self.config.image.enable_deduplication:
                if not self.deduplicator.is_duplicate_url(img_url):
                    unique_images.append(img_url)
                else:
                    self.stats['duplicates_skipped'] += 1
            else:
                unique_images.append(img_url)
        
        if not unique_images:
            logger.info(f"⏭️  没有新图片需要下载")
            return
        
        logger.info(f"⬇️  下载 {len(unique_images)} 张图片...")
        
        # 创建保存目录
        save_dir = self.config.image.download_dir / board / thread_id
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # 下载图片
        async with ImageDownloader() as downloader:
            metadata = {
                'board': board,
                'thread_id': thread_id,
                'thread_url': thread_data['url']
            }
            
            results = await downloader.download_batch(
                unique_images,
                save_dir,
                metadata
            )
            
            # 统计结果
            for result in results:
                if result.get('success'):
                    self.stats['images_downloaded'] += 1
                    
                    # 检查文件去重
                    if self.config.image.enable_deduplication:
                        file_path = Path(result['save_path'])
                        if self.deduplicator.is_duplicate_file(file_path):
                            self.deduplicator.remove_duplicate_file(file_path)
                            self.stats['duplicates_skipped'] += 1
                            self.stats['images_downloaded'] -= 1
                            continue
                    
                    # 保存图片记录
                    storage.save_image_record(result)
                elif result.get('skipped'):
                    # 被跳过的图片（已存在/尺寸不符等）
                    self.stats['duplicates_skipped'] += 1
                else:
                    # 真正下载失败的图片
                    self.stats['images_failed'] += 1
    
    async def crawl_threads_from_list(self, thread_urls: List[str]):
        """
        从URL列表爬取帖子
        
        Args:
            thread_urls: 帖子URL列表
        """
        logger.info(f"📋 批量爬取 {len(thread_urls)} 个帖子")
        
        for url in tqdm(thread_urls, desc="爬取进度"):
            thread_info = {
                'url': url,
                'thread_id': self.parser._extract_thread_id(url)
            }
            await self.crawl_thread(thread_info)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats['deduplication'] = self.deduplicator.get_stats()
        stats['storage'] = storage.get_statistics()
        return stats


# ============================================================================
# 论坛特定爬虫
# ============================================================================

class DiscuzSpider(BBSSpider):
    """
    Discuz论坛专用爬虫
    
    处理Discuz特有的图片链接格式和附件系统
    """
    
    async def process_images(self, images: List[str]) -> List[str]:
        """
        处理Discuz特殊图片链接
        
        Discuz的附件链接格式: forum.php?mod=attachment&aid=xxx
        需要添加 &nothumb=yes 参数获取原图
        """
        processed_images = []
        
        for img_url in images:
            # 处理相对路径
            if img_url.startswith('forum.php') or img_url.startswith('/forum.php'):
                img_url = f"{self.config.bbs.base_url}/{img_url.lstrip('/')}"
            
            # Discuz附件链接需要添加原图参数
            if 'mod=attachment' in img_url and 'nothumb' not in img_url:
                img_url += '&nothumb=yes'
            
            processed_images.append(img_url)
        
        return processed_images


class PhpBBSpider(BBSSpider):
    """
    phpBB论坛专用爬虫
    
    处理phpBB特有的结构
    """
    pass  # 暂时使用基类逻辑，可根据需要扩展


class VBulletinSpider(BBSSpider):
    """
    vBulletin论坛专用爬虫
    
    处理vBulletin特有的结构
    """
    pass  # 暂时使用基类逻辑，可根据需要扩展
