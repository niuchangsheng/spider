"""
CLI命令处理函数
"""
import asyncio
import re
import os
from typing import Dict, Any
from urllib.parse import urlparse
from loguru import logger

from config import Config, ConfigLoader, get_example_config, get_forum_boards, get_forum_urls, get_news_urls
from spiders import SpiderFactory
from spiders.dynamic_news_spider import DynamicNewsCrawler
from core.downloader import ImageDownloader
from core.checkpoint import CheckpointManager


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
            max_pages=args.max_pages,
            resume=args.resume,
            start_page=args.start_page
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
                max_pages=args.max_pages,
                resume=args.resume,
                start_page=args.start_page
            ))
        
        # 使用 asyncio.gather 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = len(results) - success_count
        logger.info(f"✅ 完成: 成功 {success_count}, 失败 {failed_count}")
        
        # 输出统计
        print_statistics(spider)


async def _crawl_single_news_url(crawler, url, args, config):
    """爬取单个新闻URL的辅助函数"""
    logger.info(f"🚀 开始爬取动态新闻页面: {url}")
    
    # 选择爬取方式
    if args.method == 'ajax':
        articles = await crawler.crawl_dynamic_page_ajax(
            url,
            max_pages=args.max_pages
        )
    else:  # selenium
        articles = await crawler.crawl_dynamic_page_selenium(
            url,
            max_clicks=args.max_pages
        )
    
    if not articles:
        logger.warning(f"⚠️  {url} 没有找到文章")
        return 0, 0
    
    logger.info(f"✅ {url} 发现 {len(articles)} 篇文章")
    
    downloaded_images = 0
    total_images = 0
    
    # 是否下载文章详情和图片
    if args.download_images:
        logger.info(f"🚀 开始下载文章详情和图片...")
        
        # 爬取文章详情
        full_articles = await crawler.crawl_articles_batch(articles)
        
        # 从URL提取域名作为存储目录
        domain = urlparse(url).netloc  # 如 sxd.xd.com
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
        
        logger.success(f"✅ {url} 图片下载完成: {downloaded_images}/{total_images}")
    
    return len(articles), downloaded_images


async def handle_crawl_news(args):
    """处理 crawl-news 子命令"""
    print(f"\n📌 命令: 爬取动态新闻页面")
    print(f"方式: {args.method}")
    if args.max_pages:
        print(f"最大页数: {args.max_pages}")
    else:
        print(f"最大页数: 不限制（爬取所有页）")
    
    # 确定要爬取的URL列表
    news_urls = []
    
    if args.config:
        # 从配置文件读取news URLs
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
        news_urls = get_news_urls(args.config)
        
        if not news_urls:
            logger.error(f"❌ 配置文件 {args.config} 中没有找到 news_urls！")
            return
        
        logger.info(f"📝 从配置文件加载 {len(news_urls)} 个新闻URL")
        for url in news_urls:
            print(f"  - {url}")
    elif args.url:
        # 使用命令行提供的单个URL
        news_urls = [args.url]
        print(f"URL: {args.url}")
        
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
    else:
        logger.error("❌ 请提供URL或使用--config参数指定配置文件！")
        return
    
    # 创建爬虫
    crawler = DynamicNewsCrawler(config)
    
    # 爬取所有URL
    async with crawler:
        total_articles = 0
        total_downloaded_images = 0
        
        for url in news_urls:
            articles_count, images_count = await _crawl_single_news_url(
                crawler, url, args, config
            )
            total_articles += articles_count
            total_downloaded_images += images_count
        
        # 输出统计
        stats = crawler.get_statistics()
        print("\n" + "=" * 60)
        print("📊 爬取统计:")
        print(f"  爬取URL数: {len(news_urls)}")
        print(f"  发现文章: {total_articles}")
        if args.download_images:
            print(f"  爬取详情: {stats['articles_crawled']}")
            print(f"  爬取失败: {stats['articles_failed']}")
            print(f"  下载图片: {total_downloaded_images}")
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


async def handle_checkpoint_status(args):
    """处理 checkpoint-status 子命令"""
    print(f"\n📌 命令: 查看检查点状态")
    print(f"网站: {args.site}")
    print(f"板块: {args.board}")
    
    # 创建检查点管理器
    checkpoint = CheckpointManager(site=args.site, board=args.board)
    
    # 如果指定清除
    if args.clear:
        if checkpoint.exists():
            checkpoint.clear_checkpoint()
            print("✅ 检查点已清除")
        else:
            print("ℹ️  没有找到检查点")
        return
    
    # 查看检查点状态
    if not checkpoint.exists():
        print("ℹ️  没有找到检查点")
        print(f"   检查点文件: {checkpoint.checkpoint_file}")
        return
    
    # 加载检查点数据
    data = checkpoint.load_checkpoint()
    if not data:
        print("❌ 无法加载检查点数据")
        return
    
    # 显示检查点信息
    print("\n" + "=" * 60)
    print("📂 检查点信息:")
    print(f"  文件路径: {checkpoint.checkpoint_file}")
    print(f"  状态: {data.get('status', 'unknown')}")
    print(f"  当前页: {data.get('current_page', 0)}")
    print(f"  最后帖子ID: {data.get('last_thread_id', 'N/A')}")
    print(f"  创建时间: {data.get('created_at', 'N/A')}")
    print(f"  更新时间: {data.get('last_update_time', 'N/A')}")
    
    # 显示统计信息
    stats = data.get('stats', {})
    if stats:
        print("\n📊 统计信息:")
        print(f"  已爬取帖子: {stats.get('crawled_count', 0)}")
        print(f"  下载图片: {stats.get('images_downloaded', 0)}")
        print(f"  失败数: {stats.get('failed_count', 0)}")
        if 'last_error' in stats:
            print(f"  最后错误: {stats['last_error']}")
    
    print("=" * 60)
