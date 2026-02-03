"""
BBS图片爬虫 - 统一架构
支持多种论坛系统：Discuz、phpBB、vBulletin等
"""
import asyncio
import sys
import aiohttp
from typing import List, Dict, Any, Optional, Type
from loguru import logger
from pathlib import Path
from tqdm import tqdm
from fake_useragent import UserAgent

from config import Config, ConfigLoader, ForumPresets, get_example_config, get_forum_boards, get_forum_urls
from core.downloader import ImageDownloader
from core.parser import BBSParser
from core.storage import storage
from core.deduplicator import ImageDeduplicator


class BBSSpider:
    """
    BBS图片爬虫基类
    
    提供通用的爬取逻辑，子类可重写特定方法实现论坛特定处理
    """
    
    def __init__(self, config: Optional[Config] = None, url: Optional[str] = None, preset: Optional[str] = None):
        """
        初始化爬虫
        
        Args:
            config: 手动配置（优先级最高）
            url: 论坛URL，自动检测配置
            preset: 论坛类型预设 (discuz/phpbb/vbulletin)
        
        Note:
            推荐使用 SpiderFactory.create() 而不是直接实例化
        
        Examples:
            # ✅ 推荐：使用配置文件（自动加载 configs/xindong.json）
            config = get_example_config("xindong")
            spider = SpiderFactory.create(config=config)
            
            # ✅ 推荐：使用论坛类型预设
            spider = SpiderFactory.create(preset="discuz")
            
            # ✅ 推荐：自动检测
            spider = SpiderFactory.create(url="https://forum.com/board")
            
            # ⚠️ 不推荐：直接实例化（除非自定义子类）
            spider = BBSSpider(preset="discuz")
        """
        # 配置优先级: config > preset > url
        if config:
            self.config = config
        elif preset:
            self.config = ConfigLoader.load(preset)
        elif url:
            self.config = ConfigLoader.auto_detect(url)
        else:
            raise ValueError("必须提供 config、preset 或 url 参数之一")
        
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
        
        logger.info(f"🚀 初始化爬虫: {self.config.bbs.name} ({self.config.bbs.forum_type})")
    
    async def __aenter__(self):
        """异步上下文管理器"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.close()
    
    async def init(self):
        """初始化爬虫"""
        logger.info("⚙️  初始化爬虫组件...")
        
        # 初始化HTTP会话
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # 连接数据库
        storage.connect()
        
        # 加载已存在的文件哈希
        if self.config.image.enable_deduplication:
            self.deduplicator.load_existing_hashes(self.config.image.download_dir)
        
        logger.success("✅ 爬虫初始化完成")
    
    async def close(self):
        """关闭爬虫"""
        logger.info("🔒 关闭爬虫...")
        
        if self.session:
            await self.session.close()
        
        storage.close()
        
        # 输出统计信息
        logger.info(f"📊 爬虫统计: {self.stats}")
        logger.info(f"🔄 去重统计: {self.deduplicator.get_stats()}")
    
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
            logger.debug(f"📄 获取页面: {url}")
            
            async with self.session.get(url, headers=self.get_headers()) as response:
                if response.status == 200:
                    html = await response.text()
                    await asyncio.sleep(self.config.crawler.download_delay)
                    return html
                else:
                    logger.warning(f"⚠️  获取失败 {url}: HTTP {response.status}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ 获取出错 {url}: {e}")
            return None
    
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
    
    async def crawl_board(self, board_url: str, board_name: str, max_pages: Optional[int] = None):
        """
        爬取板块
        
        Args:
            board_url: 板块URL
            board_name: 板块名称
            max_pages: 最大页数
        """
        logger.info(f"📚 开始爬取板块: {board_name}")
        
        current_url = board_url
        page_count = 0
        
        while current_url and (max_pages is None or page_count < max_pages):
            page_count += 1
            logger.info(f"📄 爬取第 {page_count} 页: {current_url}")
            
            # 获取列表页
            html = await self.fetch_page(current_url)
            if not html:
                break
            
            # 解析帖子列表
            threads = self.parser.parse_thread_list(html, current_url)
            logger.info(f"✅ 发现 {len(threads)} 个帖子")
            
            # 爬取每个帖子
            for thread in threads:
                thread['board'] = board_name
                await self.crawl_thread(thread)
            
            # 查找下一页
            current_url = self.parser.find_next_page(html, current_url)
            if not current_url:
                logger.info("📌 没有更多页面")
                break
        
        logger.success(f"🎉 板块爬取完成: {board_name}, 总页数: {page_count}")
    
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
                else:
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


# ============================================================================
# 爬虫工厂
# ============================================================================

class SpiderFactory:
    """
    爬虫工厂类
    
    根据配置的论坛类型自动创建合适的爬虫实例
    """
    
    # 爬虫类型注册表
    _registry: Dict[str, Type[BBSSpider]] = {
        'discuz': DiscuzSpider,
        'phpbb': PhpBBSpider,
        'vbulletin': VBulletinSpider,
        'generic': BBSSpider,
    }
    
    @classmethod
    def register(cls, forum_type: str, spider_class: Type[BBSSpider]):
        """
        注册新的爬虫类型
        
        Args:
            forum_type: 论坛类型标识
            spider_class: 爬虫类
        
        Examples:
            SpiderFactory.register('mybb', MyBBSpider)
        """
        cls._registry[forum_type] = spider_class
        logger.info(f"✅ 注册爬虫类型: {forum_type} -> {spider_class.__name__}")
    
    @classmethod
    def create(cls, config: Optional[Config] = None, url: Optional[str] = None, preset: Optional[str] = None) -> BBSSpider:
        """
        创建爬虫实例（工厂方法）
        
        Args:
            config: 配置对象（优先级最高）
            url: 论坛URL，自动检测配置
            preset: 论坛类型预设 (discuz/phpbb/vbulletin)
        
        Returns:
            对应类型的爬虫实例 (BBSSpider 或其子类)
        
        Examples:
            # ✅ 方式1: 使用配置文件（推荐）
            from config import get_example_config
            config = get_example_config("xindong")  # 自动加载 configs/xindong.json
            spider = SpiderFactory.create(config=config)
            
            # ✅ 方式2: 使用论坛类型预设
            spider = SpiderFactory.create(preset="discuz")
            
            # ✅ 方式3: 自动检测论坛类型
            spider = SpiderFactory.create(url="https://forum.com/board")
            
            # ✅ 方式4: 完全自定义配置
            from config import Config
            custom_config = Config(bbs={...}, crawler={...})
            spider = SpiderFactory.create(config=custom_config)
        """
        # 先获取配置
        if config:
            final_config = config
        elif preset:
            final_config = ConfigLoader.load(preset)
        elif url:
            final_config = ConfigLoader.auto_detect(url)
        else:
            raise ValueError("必须提供 config、preset 或 url 参数之一")
        
        # 根据forum_type选择爬虫类
        forum_type = final_config.bbs.forum_type.lower()
        spider_class = cls._registry.get(forum_type, BBSSpider)
        
        logger.info(f"🏭 创建爬虫: {spider_class.__name__}")
        
        return spider_class(config=final_config)


# ============================================================================
# 便捷函数
# ============================================================================

async def crawl_single_thread(thread_url: str, preset: str = "xindong"):
    """
    爬取单个帖子（便捷函数）
    
    Args:
        thread_url: 帖子URL
        preset: 预设配置名称
    """
    async with SpiderFactory.create(preset=preset) as spider:
        thread_info = {
            'url': thread_url,
            'thread_id': spider.parser._extract_thread_id(thread_url),
        }
        await spider.crawl_thread(thread_info)
        return spider.get_statistics()


async def crawl_board(board_url: str, board_name: str, max_pages: int = 3, preset: str = "xindong"):
    """
    爬取板块（便捷函数）
    
    Args:
        board_url: 板块URL
        board_name: 板块名称
        max_pages: 最大页数
        preset: 预设配置名称
    """
    async with SpiderFactory.create(preset=preset) as spider:
        await spider.crawl_board(board_url, board_name, max_pages)
        return spider.get_statistics()


# ============================================================================
# 主函数示例
# ============================================================================

async def main():
    """主函数示例 - 展示多种使用方式"""
    import argparse
    
    # 命令行参数
    parser = argparse.ArgumentParser(
        description='BBS图片爬虫 (v2.0)',
        epilog='示例: python spider.py --config xindong --mode 1'
    )
    
    # 配置来源（互斥组）
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument('--preset', type=str,
                             help='论坛类型预设 (discuz/phpbb/vbulletin)')
    config_group.add_argument('--config', type=str, default="xindong",
                             help='配置文件名 (从 configs/ 加载，如: xindong)')
    config_group.add_argument('--url', type=str,
                             help='论坛URL（自动检测配置）')
    
    # 处理模式
    parser.add_argument('--mode', type=int, default=1, choices=[1, 2],
                       help='处理模式: 1=URL列表, 2=板块列表')
    
    # 可选参数
    parser.add_argument('--urls', type=str,
                       help='URL列表，逗号分隔（覆盖配置文件）')
    parser.add_argument('--boards', type=str,
                       help='板块URL列表，逗号分隔（覆盖配置文件）')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='每个板块最大爬取页数（mode 2，默认不限制，爬取所有页）')
    
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    log_file = Path(__file__).parent / "logs" / "spider.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        rotation="100 MB",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG"
    )
    
    print("\n" + "=" * 60)
    print("🕷️  BBS图片爬虫 (v2.0)")
    print("=" * 60)
    
    # 1. 加载配置
    config_name = None
    if args.config:
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
        config_name = args.config
    elif args.preset:
        logger.info(f"📋 使用论坛类型预设: {args.preset}")
        config = ConfigLoader.load(args.preset)
    elif args.url:
        logger.info(f"🌐 自动检测配置: {args.url}")
        config = await ConfigLoader.auto_detect_config(args.url)
    else:
        # 默认使用 xindong
        logger.info("📁 使用默认配置: xindong")
        config = get_example_config("xindong")
        config_name = "xindong"
    
    # 2. 创建爬虫
    spider = await SpiderFactory.create(config=config)
    
    async with spider:
        # 3. 根据模式执行任务
        if args.mode == 1:
            # 模式1: 批量爬取URL列表
            print(f"\n📌 模式1: 批量爬取URL列表")
            
            # 获取URL列表
            if args.urls:
                urls = [u.strip() for u in args.urls.split(',')]
                logger.info(f"📝 使用命令行URL: {len(urls)} 个")
            elif config_name:
                urls = get_forum_urls(config_name)
                logger.info(f"📝 从配置文件加载URL: {len(urls)} 个")
            else:
                urls = []
            
            if not urls:
                logger.error("❌ 没有URL可爬取！请提供 --urls 或在配置文件中定义")
                return
            
            # 并发爬取
            logger.info(f"🚀 开始并发爬取 {len(urls)} 个URL...")
            tasks = []
            for url in urls:
                thread_id = spider.parser._extract_thread_id(url)
                thread_info = {
                    'url': url,
                    'thread_id': thread_id,
                    'title': f'Thread-{thread_id}',
                    'board': config.bbs.name
                }
                tasks.append(spider.crawl_thread(thread_info))
            
            # 使用 asyncio.gather 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            failed_count = len(results) - success_count
            logger.info(f"✅ 完成: 成功 {success_count}, 失败 {failed_count}")
        
        elif args.mode == 2:
            # 模式2: 批量爬取板块列表
            print(f"\n📌 模式2: 批量爬取板块列表")
            
            # 获取板块列表
            if args.boards:
                board_urls = [u.strip() for u in args.boards.split(',')]
                boards_info = [{"name": f"Board-{i+1}", "url": url} for i, url in enumerate(board_urls)]
                logger.info(f"📝 使用命令行板块: {len(boards_info)} 个")
            elif config_name:
                boards_info = get_forum_boards(config_name)
                logger.info(f"📝 从配置文件加载板块: {len(boards_info)} 个")
            else:
                boards_info = []
            
            if not boards_info:
                logger.error("❌ 没有板块可爬取！请提供 --boards 或在配置文件中定义")
                return
            
            # 并发爬取板块
            if args.max_pages:
                logger.info(f"🚀 开始并发爬取 {len(boards_info)} 个板块（每个最多 {args.max_pages} 页）...")
            else:
                logger.info(f"🚀 开始并发爬取 {len(boards_info)} 个板块（爬取所有页面）...")
            tasks = []
            for board in boards_info:
                logger.info(f"📁 板块: {board['name']} - {board['url']}")
                tasks.append(spider.crawl_board(
                    board_url=board['url'],
                    board_name=board['name'],
                    max_pages=args.max_pages
                ))
            
            # 使用 asyncio.gather 并发执行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            failed_count = len(results) - success_count
            logger.info(f"✅ 完成: 成功 {success_count}, 失败 {failed_count}")
        
        # 4. 输出统计
        stats = spider.get_statistics()
        print("\n" + "=" * 60)
        print("📊 爬取统计:")
        print(f"  帖子数: {stats['threads_crawled']}")
        print(f"  发现图片: {stats['images_found']}")
        print(f"  下载成功: {stats['images_downloaded']}")
        print(f"  下载失败: {stats['images_failed']}")
        print(f"  去重跳过: {stats['duplicates_skipped']}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
