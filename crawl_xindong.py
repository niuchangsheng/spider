"""
心动论坛爬虫 - 专用启动脚本
针对 https://bbs.xd.com 进行优化
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# 导入配置
from config_xindong import xindong_config, XINDONG_BOARDS, EXAMPLE_THREADS
from bbs_spider import BBSSpider

# 应用心动论坛配置
import config as config_module
config_module.config = xindong_config


class XindongSpider(BBSSpider):
    """心动论坛专用爬虫"""
    
    def __init__(self):
        super().__init__()
        logger.info("心动论坛爬虫初始化完成")
        logger.info(f"目标站点: {self.config.bbs.base_url}")
    
    async def process_discuz_images(self, images: list) -> list:
        """
        处理Discuz论坛的特殊图片链接
        Discuz的附件链接格式：forum.php?mod=attachment&aid=xxx
        """
        processed_images = []
        
        for img_url in images:
            # 处理相对路径
            if img_url.startswith('forum.php') or img_url.startswith('/forum.php'):
                img_url = f"{self.config.bbs.base_url}/{img_url.lstrip('/')}"
            
            # Discuz附件链接通常需要添加 &nothumb=yes 获取原图
            if 'mod=attachment' in img_url and 'nothumb' not in img_url:
                img_url += '&nothumb=yes'
            
            processed_images.append(img_url)
        
        return processed_images
    
    async def crawl_thread(self, thread_info: dict):
        """重写爬取方法，添加Discuz特殊处理"""
        thread_url = thread_info['url']
        thread_id = thread_info['thread_id']
        
        # 检查是否已爬取
        if self.config.database and hasattr(self, 'storage'):
            from core.storage import storage
            if storage.thread_exists(thread_id):
                logger.info(f"帖子 {thread_id} 已爬取，跳过")
                return
        
        logger.info(f"正在爬取帖子: {thread_info.get('title', thread_id)}")
        
        # 获取帖子页面
        html = await self.fetch_page(thread_url)
        if not html:
            return
        
        # 解析帖子内容
        thread_data = self.parser.parse_thread_page(html, thread_url)
        thread_data['board'] = thread_info.get('board')
        thread_data['title'] = thread_info.get('title')
        
        # 处理Discuz特殊图片链接
        thread_data['images'] = await self.process_discuz_images(thread_data['images'])
        
        # 更新统计
        self.stats['threads_crawled'] += 1
        self.stats['images_found'] += len(thread_data['images'])
        
        logger.info(f"发现 {len(thread_data['images'])} 张图片")
        
        # 下载图片
        if thread_data['images']:
            await self.download_thread_images(thread_data)
        
        # 保存帖子数据（如果配置了数据库）
        try:
            from core.storage import storage
            if storage.mongo_client:
                storage.save_thread(thread_data)
        except:
            logger.debug("数据库未配置，跳过保存元数据")


async def crawl_single_thread():
    """示例1：爬取单个帖子"""
    logger.info("=" * 60)
    logger.info("爬取心动论坛单个帖子")
    logger.info("=" * 60)
    
    async with XindongSpider() as spider:
        # 爬取示例帖子
        thread_url = EXAMPLE_THREADS[0]
        
        thread_info = {
            'url': thread_url,
            'thread_id': spider.parser._extract_thread_id(thread_url),
            'title': '神仙道怀旧服公测',
            'board': '神仙道'
        }
        
        await spider.crawl_thread(thread_info)
        
        # 显示统计
        stats = spider.get_statistics()
        logger.success("=" * 60)
        logger.success(f"爬取完成！")
        logger.success(f"帖子数: {stats['threads_crawled']}")
        logger.success(f"发现图片: {stats['images_found']}")
        logger.success(f"下载成功: {stats['images_downloaded']}")
        logger.success(f"下载失败: {stats['images_failed']}")
        logger.success(f"去重跳过: {stats['duplicates_skipped']}")
        logger.success("=" * 60)


async def crawl_board():
    """示例2：爬取板块"""
    logger.info("=" * 60)
    logger.info("爬取心动论坛板块")
    logger.info("=" * 60)
    
    board_info = XINDONG_BOARDS["神仙道"]
    
    async with XindongSpider() as spider:
        await spider.crawl_board(
            board_url=board_info["url"],
            board_name=board_info["board_name"],
            max_pages=3  # 只爬取前3页
        )


async def crawl_multiple_threads():
    """示例3：批量爬取多个帖子"""
    logger.info("=" * 60)
    logger.info("批量爬取心动论坛帖子")
    logger.info("=" * 60)
    
    # 添加更多帖子URL
    thread_urls = [
        "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1",
        # 可以添加更多帖子URL
    ]
    
    async with XindongSpider() as spider:
        await spider.crawl_threads_from_list(thread_urls)


def main():
    """主函数"""
    import argparse
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='心动论坛图片爬虫')
    parser.add_argument(
        '--mode', 
        type=int, 
        default=1, 
        choices=[1, 2, 3],
        help='运行模式: 1=单个帖子(默认), 2=爬取板块, 3=批量帖子'
    )
    args = parser.parse_args()
    
    # 配置日志
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # 同时输出到文件
    log_file = Path(__file__).parent / "logs" / "xindong_spider.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_file,
        rotation="100 MB",
        retention="30 days",
        encoding="utf-8",
        level="DEBUG"
    )
    
    print("\n" + "=" * 60)
    print("心动论坛图片爬虫")
    print("=" * 60)
    
    # 根据参数选择功能
    choice = args.mode
    
    if choice == 1:
        print("\n📌 模式: 爬取示例帖子")
        asyncio.run(crawl_single_thread())
    elif choice == 2:
        print("\n📌 模式: 爬取神仙道板块（前3页）")
        asyncio.run(crawl_board())
    elif choice == 3:
        print("\n📌 模式: 批量爬取多个帖子")
        asyncio.run(crawl_multiple_threads())


if __name__ == "__main__":
    main()
