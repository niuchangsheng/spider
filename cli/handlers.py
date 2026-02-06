"""
CLI命令处理函数
"""
import asyncio
import re
import os
from typing import Dict, Any
from urllib.parse import urlparse
from loguru import logger

from config import Config, ConfigLoader, get_example_config, get_forum_boards, get_forum_urls
from spiders import SpiderFactory
from spiders.dynamic_news_spider import DynamicNewsCrawler
from core.downloader import ImageDownloader


def _extract_image_filename(url: str) -> str:
    """
    从图片URL提取原始文件名
    
    处理逻辑：
    1. 从URL路径提取文件名
    2. 去掉尺寸后缀（如 -1024x481）
    3. 保留原始扩展名
    
    Args:
        url: 图片URL
    
    Returns:
        清理后的文件名
    """
    try:
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path)
        
        # 去掉尺寸后缀（如 -1024x481, -300x200 等）
        clean_name = re.sub(r'-\d+x\d+', '', filename)
        
        # 去掉查询参数可能带来的后缀
        clean_name = clean_name.split('?')[0]
        
        # 如果文件名为空或无效，生成一个默认名
        if not clean_name or clean_name == '.' or '.' not in clean_name:
            import hashlib
            hash_name = hashlib.md5(url.encode()).hexdigest()[:12]
            clean_name = f"{hash_name}.jpg"
        
        return clean_name
    except Exception:
        import hashlib
        hash_name = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"{hash_name}.jpg"


async def handle_crawl_url(args):
    """处理 crawl-url 子命令"""
    print(f"\n📌 命令: 爬取单个URL")
    print(f"URL: {args.url}")
    
    # 1. 加载配置
    if args.auto_detect:
        logger.info(f"🌐 自动检测配置: {args.url}")
        config = ConfigLoader.auto_detect(args.url)
    elif args.preset:
        logger.info(f"📋 使用论坛类型预设: {args.preset}")
        config = ConfigLoader.load(args.preset)
    elif args.config:
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
    else:
        logger.error("❌ 请指定配置来源: --auto-detect 或 --preset 或 --config")
        return
    
    # 2. 创建爬虫
    spider = SpiderFactory.create(config=config)
    
    # 3. 爬取URL
    async with spider:
        thread_id = spider.parser._extract_thread_id(args.url)
        thread_info = {
            'url': args.url,
            'thread_id': thread_id,
            'title': f'Thread-{thread_id}',
            'board': config.bbs.name
        }
        
        logger.info(f"🚀 开始爬取URL...")
        await spider.crawl_thread(thread_info)
        logger.info(f"✅ 爬取完成")
        
        # 输出统计
        print_statistics(spider)


async def handle_crawl_urls(args):
    """处理 crawl-urls 子命令"""
    print(f"\n📌 命令: 爬取配置中的URL列表")
    print(f"配置: {args.config}")
    
    # 1. 加载配置
    logger.info(f"📁 使用配置文件: {args.config}")
    config = get_example_config(args.config)
    
    # 2. 获取URL列表
    urls = get_forum_urls(args.config)
    logger.info(f"📝 从配置文件加载URL: {len(urls)} 个")
    
    if not urls:
        logger.error("❌ 配置文件中没有URLs！")
        return
    
    # 3. 创建爬虫并并发爬取
    spider = SpiderFactory.create(config=config)
    
    async with spider:
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
        
        # 输出统计
        print_statistics(spider)


async def handle_crawl_board(args):
    """处理 crawl-board 子命令"""
    print(f"\n📌 命令: 爬取单个板块")
    print(f"板块URL: {args.board_url}")
    if args.max_pages:
        print(f"最大页数: {args.max_pages}")
    else:
        print(f"最大页数: 不限制（爬取所有页）")
    
    # 1. 加载配置
    if args.auto_detect:
        logger.info(f"🌐 自动检测配置: {args.board_url}")
        config = ConfigLoader.auto_detect(args.board_url)
    elif args.preset:
        logger.info(f"📋 使用论坛类型预设: {args.preset}")
        config = ConfigLoader.load(args.preset)
    elif args.config:
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
    else:
        logger.error("❌ 请指定配置来源: --auto-detect 或 --preset 或 --config")
        return
    
    # 2. 创建爬虫
    spider = SpiderFactory.create(config=config)
    
    # 3. 爬取板块
    async with spider:
        logger.info(f"🚀 开始爬取板块...")
        await spider.crawl_board(
            board_url=args.board_url,
            board_name=config.bbs.name,
            max_pages=args.max_pages
        )
        logger.info(f"✅ 爬取完成")
        
        # 输出统计
        print_statistics(spider)


async def handle_crawl_boards(args):
    """处理 crawl-boards 子命令"""
    print(f"\n📌 命令: 爬取配置中的所有板块")
    print(f"配置: {args.config}")
    if args.max_pages:
        print(f"每个板块最大页数: {args.max_pages}")
    else:
        print(f"每个板块最大页数: 不限制（爬取所有页）")
    
    # 1. 加载配置
    logger.info(f"📁 使用配置文件: {args.config}")
    config = get_example_config(args.config)
    
    # 2. 获取板块列表
    boards_info = get_forum_boards(args.config)
    logger.info(f"📝 从配置文件加载板块: {len(boards_info)} 个")
    
    if not boards_info:
        logger.error("❌ 配置文件中没有板块！")
        return
    
    # 3. 创建爬虫并并发爬取
    spider = SpiderFactory.create(config=config)
    
    async with spider:
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
        
        # 输出统计
        print_statistics(spider)


async def handle_crawl_news(args):
    """处理 crawl-news 子命令"""
    print(f"\n📌 命令: 爬取动态新闻页面")
    print(f"URL: {args.url}")
    print(f"方式: {args.method}")
    if args.max_pages:
        print(f"最大页数: {args.max_pages}")
    else:
        print(f"最大页数: 不限制（爬取所有页）")
    
    # 1. 加载配置
    if args.config:
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
    else:
        # 创建默认配置
        logger.info(f"🌐 使用默认配置")
        parsed = urlparse(args.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        config = Config(
            bbs={
                "name": "动态新闻网站",
                "base_url": base_url,
                "forum_type": "custom"
            }
        )
    
    # 2. 创建爬虫
    crawler = DynamicNewsCrawler(config)
    
    # 3. 爬取页面
    async with crawler:
        logger.info(f"🚀 开始爬取动态新闻页面...")
        
        # 选择爬取方式
        if args.method == 'ajax':
            articles = await crawler.crawl_dynamic_page_ajax(
                args.url,
                max_pages=args.max_pages
            )
        else:  # selenium
            articles = await crawler.crawl_dynamic_page_selenium(
                args.url,
                max_clicks=args.max_pages
            )
        
        if not articles:
            logger.warning("⚠️  没有找到文章")
            return
        
        logger.info(f"✅ 发现 {len(articles)} 篇文章")
        
        # 4. 是否下载文章详情和图片
        if args.download_images:
            logger.info(f"🚀 开始下载文章详情和图片...")
            
            # 爬取文章详情
            full_articles = await crawler.crawl_articles_batch(articles)
            
            # 下载图片
            total_images = 0
            downloaded_images = 0
            
            # 从URL提取域名作为存储目录
            domain = urlparse(args.url).netloc  # 如 sxd.xd.com
            save_dir = config.image.download_dir / domain
            save_dir.mkdir(parents=True, exist_ok=True)
            
            async with ImageDownloader() as downloader:
                for article in full_articles:
                    images = article.get('images', [])
                    if not images:
                        continue
                    
                    total_images += len(images)
                    article_id = article.get('article_id', 'unknown')
                    
                    # 逐个下载图片，使用自定义文件名格式
                    for img_url in images:
                        # 从图片URL提取原始文件名
                        img_filename = _extract_image_filename(img_url)
                        # 生成最终文件名: [article_id]_[原始图片名]
                        final_filename = f"{article_id}_{img_filename}"
                        save_path = save_dir / final_filename
                        
                        # 下载图片
                        metadata = {
                            'article_id': article_id,
                            'title': article.get('title', ''),
                            'article_url': article.get('url', ''),
                            'image_url': img_url
                        }
                        
                        result = await downloader.download_image(img_url, save_path, metadata)
                        if result.get('success'):
                            downloaded_images += 1
                        
                        # 添加延迟
                        await asyncio.sleep(config.crawler.download_delay)
            
            logger.success(f"✅ 图片下载完成: {downloaded_images}/{total_images}")
        
        # 5. 输出统计
        stats = crawler.get_statistics()
        print("\n" + "=" * 60)
        print("📊 爬取统计:")
        print(f"  发现文章: {stats['articles_found']}")
        if args.download_images:
            print(f"  爬取详情: {stats['articles_crawled']}")
            print(f"  爬取失败: {stats['articles_failed']}")
            print(f"  下载图片: {downloaded_images if 'downloaded_images' in locals() else 0}")
        print("=" * 60)


def print_statistics(spider):
    """输出统计信息"""
    stats = spider.get_statistics()
    print("\n" + "=" * 60)
    print("📊 爬取统计:")
    print(f"  帖子数: {stats['threads_crawled']}")
    print(f"  发现图片: {stats['images_found']}")
    print(f"  下载成功: {stats['images_downloaded']}")
    print(f"  下载失败: {stats['images_failed']}")
    print(f"  去重跳过: {stats['duplicates_skipped']}")
    print("=" * 60)
