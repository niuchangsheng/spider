"""
BBS图片爬虫主程序
"""
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from loguru import logger
from pathlib import Path
from tqdm import tqdm
from fake_useragent import UserAgent

from config import config
from core.downloader import ImageDownloader
from core.parser import BBSParser
from core.storage import storage
from core.deduplicator import ImageDeduplicator


class BBSSpider:
    """BBS图片爬虫"""
    
    def __init__(self):
        self.config = config
        self.parser = BBSParser()
        self.deduplicator = ImageDeduplicator(use_perceptual_hash=True)
        self.ua = UserAgent()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 统计信息
        self.stats = {
            "threads_crawled": 0,
            "images_found": 0,
            "images_downloaded": 0,
            "images_failed": 0,
            "duplicates_skipped": 0
        }
    
    async def __aenter__(self):
        """异步上下文管理器"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
    
    async def init(self):
        """初始化爬虫"""
        logger.info("Initializing BBS Spider...")
        
        # 初始化HTTP会话
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # 连接数据库
        storage.connect()
        
        # 加载已存在的文件哈希
        if self.config.image.enable_deduplication:
            self.deduplicator.load_existing_hashes(self.config.image.download_dir)
        
        logger.success("BBS Spider initialized")
    
    async def close(self):
        """关闭爬虫"""
        logger.info("Closing BBS Spider...")
        
        if self.session:
            await self.session.close()
        
        storage.close()
        
        # 输出统计信息
        logger.info(f"Spider Statistics: {self.stats}")
        logger.info(f"Deduplication Statistics: {self.deduplicator.get_stats()}")
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
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
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """获取页面内容"""
        try:
            logger.debug(f"Fetching page: {url}")
            
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    html = await response.text()
                    await asyncio.sleep(self.config.crawler.download_delay)
                    return html
                else:
                    logger.warning(f"Failed to fetch {url}: HTTP {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def crawl_board(self, board_url: str, board_name: str, max_pages: Optional[int] = None):
        """
        爬取板块
        
        Args:
            board_url: 板块URL
            board_name: 板块名称
            max_pages: 最大页数
        """
        logger.info(f"Starting to crawl board: {board_name}")
        
        current_url = board_url
        page_count = 0
        
        while current_url and (max_pages is None or page_count < max_pages):
            page_count += 1
            logger.info(f"Crawling page {page_count}: {current_url}")
            
            # 获取列表页
            html = await self.fetch_page(current_url)
            if not html:
                break
            
            # 解析帖子列表
            threads = self.parser.parse_thread_list(html, current_url)
            logger.info(f"Found {len(threads)} threads on page {page_count}")
            
            # 爬取每个帖子
            for thread in threads:
                thread['board'] = board_name
                await self.crawl_thread(thread)
            
            # 查找下一页
            current_url = self.parser.find_next_page(html, current_url)
            if not current_url:
                logger.info("No more pages found")
                break
        
        logger.success(f"Finished crawling board: {board_name}, total pages: {page_count}")
    
    async def crawl_thread(self, thread_info: Dict[str, Any]):
        """
        爬取单个帖子
        
        Args:
            thread_info: 帖子信息
        """
        thread_url = thread_info['url']
        thread_id = thread_info['thread_id']
        
        # 检查是否已爬取
        if storage.thread_exists(thread_id):
            logger.info(f"Thread {thread_id} already crawled, skipping")
            return
        
        logger.info(f"Crawling thread: {thread_info.get('title', thread_id)}")
        
        # 获取帖子页面
        html = await self.fetch_page(thread_url)
        if not html:
            return
        
        # 解析帖子内容
        thread_data = self.parser.parse_thread_page(html, thread_url)
        thread_data['board'] = thread_info.get('board')
        thread_data['title'] = thread_info.get('title')
        
        # 更新统计
        self.stats['threads_crawled'] += 1
        self.stats['images_found'] += len(thread_data['images'])
        
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
            logger.info(f"No unique images to download for thread {thread_id}")
            return
        
        logger.info(f"Downloading {len(unique_images)} images for thread {thread_id}")
        
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
                else:
                    self.stats['images_failed'] += 1
    
    async def crawl_threads_from_list(self, thread_urls: List[str]):
        """
        从URL列表爬取帖子
        
        Args:
            thread_urls: 帖子URL列表
        """
        logger.info(f"Crawling {len(thread_urls)} threads from list")
        
        for url in tqdm(thread_urls, desc="Crawling threads"):
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


async def main():
    """主函数示例"""
    # 配置日志
    logger.add(
        config.log.log_dir / config.log.log_file,
        rotation=config.log.rotation,
        retention=config.log.retention,
        level=config.log.log_level,
        encoding="utf-8"
    )
    
    logger.info("=" * 60)
    logger.info("BBS Image Spider Starting...")
    logger.info("=" * 60)
    
    async with BBSSpider() as spider:
        # 示例1：爬取指定板块
        # await spider.crawl_board(
        #     board_url="https://example.com/forum/板块ID",
        #     board_name="图片板块",
        #     max_pages=5
        # )
        
        # 示例2：爬取指定帖子列表
        thread_urls = [
            # "https://example.com/thread/12345",
            # "https://example.com/thread/67890",
        ]
        
        if thread_urls:
            await spider.crawl_threads_from_list(thread_urls)
        else:
            logger.warning("No thread URLs provided. Please configure URLs in main()")
        
        # 输出统计信息
        stats = spider.get_statistics()
        logger.info("=" * 60)
        logger.info("Crawling Statistics:")
        logger.info(f"  Threads crawled: {stats['threads_crawled']}")
        logger.info(f"  Images found: {stats['images_found']}")
        logger.info(f"  Images downloaded: {stats['images_downloaded']}")
        logger.info(f"  Images failed: {stats['images_failed']}")
        logger.info(f"  Duplicates skipped: {stats['duplicates_skipped']}")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
