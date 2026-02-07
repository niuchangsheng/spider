"""
CLI命令处理函数
"""
import asyncio
from typing import Dict, Any
from urllib.parse import urlparse
from loguru import logger

from config import Config, ConfigLoader, get_example_config, get_forum_boards, get_forum_urls, get_news_urls
from spiders import SpiderFactory
from spiders.dynamic_news_spider import DynamicNewsCrawler
from core.checkpoint import CheckpointManager


async def handle_crawl_bbs(args):
    """BBS：爬取单个帖子或板块，位置参数为 target，--type thread|board 区分；支持 --auto-detect"""
    if getattr(args, 'auto_detect', False):
        if args.config:
            logger.error("❌ crawl-bbs 请只指定 --config 或 --auto-detect 其一")
            return
        logger.info(f"🌐 自动检测配置: {args.target}")
        config = ConfigLoader.auto_detect(args.target)
    else:
        if not args.config:
            logger.error("❌ crawl-bbs 请指定 --config 或 --auto-detect")
            return
        config = get_example_config(args.config)
    if config.crawler_type != "bbs":
        logger.error(f"❌ 配置的 crawler_type 不是 bbs")
        return

    if getattr(args, 'max_workers', None):
        config.crawler.max_concurrent_requests = args.max_workers
    if getattr(args, 'use_adaptive_queue', None) is not None:
        config.crawler.use_adaptive_queue = args.use_adaptive_queue
    if getattr(args, 'use_async_queue', None) is not None:
        config.crawler.use_async_queue = args.use_async_queue

    spider = SpiderFactory.create(config=config)
    async with spider:
        if args.type == "thread":
            print(f"\n📌 命令: crawl-bbs 单帖")
            print(f"URL: {args.target}")
            thread_id = spider.parser._extract_thread_id(args.target)
            await spider.crawl_thread({
                'url': args.target,
                'thread_id': thread_id,
                'title': f'Thread-{thread_id}',
                'board': config.bbs.name,
            })
        else:
            print(f"\n📌 命令: crawl-bbs 单板块")
            print(f"板块URL: {args.target}")
            await spider.crawl_board(
                board_url=args.target,
                board_name=config.bbs.name,
                max_pages=getattr(args, 'max_pages', None),
                resume=getattr(args, 'resume', True),
                start_page=getattr(args, 'start_page', None),
            )
        print_statistics(spider)


async def handle_crawl_news(args):
    """爬取动态新闻单页（必须传 URL）；爬全量用 crawl --config sxd"""
    news_urls = [args.url]
    print(f"\n📌 命令: 爬取动态新闻页面")
    print(f"URL: {args.url}")
    print(f"方式: {args.method}")
    if args.max_pages:
        print(f"最大页数: {args.max_pages}")
    else:
        print(f"最大页数: 不限制（爬取所有页）")
    if hasattr(args, 'max_workers') and args.max_workers:
        print(f"并发数: {args.max_workers} (命令行指定)")
    if hasattr(args, 'use_adaptive_queue') and args.use_adaptive_queue:
        print(f"队列模式: 自适应队列")
    elif hasattr(args, 'use_async_queue') and args.use_async_queue is False:
        print(f"队列模式: 串行模式（禁用异步队列）")
    else:
        print(f"队列模式: 异步队列（默认）")

    if args.config:
        logger.info(f"📁 使用配置文件: {args.config}")
        config = get_example_config(args.config)
    else:
        parsed = urlparse(args.url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        config = Config(
            bbs={"name": "动态新闻网站", "base_url": base_url, "forum_type": "custom"}
        )

    # 应用队列相关配置
    if hasattr(args, 'max_workers') and args.max_workers:
        config.crawler.max_concurrent_requests = args.max_workers
    if hasattr(args, 'use_adaptive_queue') and args.use_adaptive_queue is not None:
        config.crawler.use_adaptive_queue = args.use_adaptive_queue
    if hasattr(args, 'use_async_queue') and args.use_async_queue is not None:
        config.crawler.use_async_queue = args.use_async_queue
    
    crawler = DynamicNewsCrawler(config)
    total_articles = 0
    total_downloaded_images = 0
    async with crawler:
        for url in news_urls:
            articles_count, images_count = await crawler.crawl_news_and_download_images(
                url,
                max_pages=args.max_pages,
                resume=args.resume,
                start_page=args.start_page,
                download_images=args.download_images,
                method=args.method,
            )
            total_articles += articles_count
            total_downloaded_images += images_count
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


async def handle_crawl(args):
    """统一爬取：仅 --config 全量，由 config 决定 BBS/新闻"""
    config_name = args.config
    config = get_example_config(config_name)
    if getattr(args, 'max_workers', None):
        config.crawler.max_concurrent_requests = args.max_workers
    if getattr(args, 'use_adaptive_queue', None) is not None:
        config.crawler.use_adaptive_queue = args.use_adaptive_queue
    if getattr(args, 'use_async_queue', None) is not None:
        config.crawler.use_async_queue = args.use_async_queue

    if config.crawler_type == "news":
        print(f"\n📌 命令: 爬取（由 config 决定）— 类型: 新闻 (crawler_type=news)")
        news_urls = config.get_page_urls() or get_news_urls(config_name)
        if not news_urls:
            logger.error(f"❌ 配置 {config_name} 中未找到 urls")
            return
        logger.info(f"📁 配置: {config_name}，新闻 URL 数: {len(news_urls)}")
        crawler = DynamicNewsCrawler(config)
        total_articles, total_images = 0, 0
        async with crawler:
            for url in news_urls:
                a, i = await crawler.crawl_news_and_download_images(
                    url,
                    max_pages=getattr(args, 'max_pages', None),
                    resume=getattr(args, 'resume', True),
                    start_page=getattr(args, 'start_page', None),
                    download_images=getattr(args, 'download_images', False),
                    method=getattr(args, 'method', 'ajax'),
                )
                total_articles += a
                total_images += i
        stats = crawler.get_statistics()
        print("\n" + "=" * 60)
        print("📊 爬取统计:")
        print(f"  新闻 URL 数: {len(news_urls)}")
        print(f"  发现文章: {total_articles}")
        print(f"  下载图片: {total_images}")
        if getattr(args, 'download_images', False):
            print(f"  爬取详情: {stats.get('articles_crawled', 0)}")
            print(f"  爬取失败: {stats.get('articles_failed', 0)}")
        print("=" * 60)
        return

    # BBS：爬取配置中的板块 + 帖子 URL
    print(f"\n📌 命令: 爬取（由 config 决定）— 类型: BBS (crawler_type=bbs)")
    boards_info = config.get_boards() or get_forum_boards(config_name)
    page_entries = config.get_page_entries() or [{"url": u, "name": None} for u in get_forum_urls(config_name)]
    if not boards_info and not page_entries:
        logger.error("❌ 配置中既无 boards 也无 urls")
        return
    logger.info(f"📁 配置: {config_name}，板块: {len(boards_info)}，帖子 URL: {len(page_entries)}")
    spider = SpiderFactory.create(config=config)
    async with spider:
        tasks = []
        for board in boards_info:
            tasks.append(spider.crawl_board(
                board_url=board["url"],
                board_name=board["name"],
                max_pages=getattr(args, 'max_pages', None),
                resume=getattr(args, 'resume', True),
                start_page=getattr(args, 'start_page', None),
            ))
        for entry in page_entries:
            url = entry["url"]
            thread_id = spider.parser._extract_thread_id(url)
            title = entry.get("name") or f"Thread-{thread_id}"
            tasks.append(spider.crawl_thread({
                "url": url,
                "thread_id": thread_id,
                "title": title,
                "board": config.bbs.name,
            }))
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            ok = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"✅ 完成: 成功 {ok}, 失败 {len(results) - ok}")
        print_statistics(spider)


async def handle_checkpoint_status(args):
    """处理 checkpoint-status 子命令（检查点基于 Storage，需先连接）"""
    from core.storage import storage

    print(f"\n📌 命令: 查看检查点状态")
    print(f"网站: {args.site}")
    print(f"板块: {args.board}")
    storage.connect()
    try:
        checkpoint = CheckpointManager(site=args.site, board=args.board)
        if args.clear:
            if checkpoint.exists():
                checkpoint.clear_checkpoint()
                print("✅ 检查点已清除")
            else:
                print("ℹ️  没有找到检查点")
            return

        if not checkpoint.exists():
            print("ℹ️  没有找到检查点")
            print(f"   存储: {checkpoint.checkpoint_file}")
            return

        data = checkpoint.load_checkpoint()
        if not data:
            print("❌ 无法加载检查点数据")
            return

        print("\n" + "=" * 60)
        print("📂 检查点信息:")
        print(f"  存储: {checkpoint.checkpoint_file}")
        print(f"  状态: {data.get('status', 'unknown')}")
        print(f"  当前页: {data.get('current_page', 0)}")
        print(f"  最后帖子ID: {data.get('last_thread_id', 'N/A')}")
        print(f"  创建时间: {data.get('created_at', 'N/A')}")
        print(f"  更新时间: {data.get('last_update_time', 'N/A')}")

        seen_article_ids = data.get('seen_article_ids', [])
        if seen_article_ids:
            print(f"\n📋 文章ID信息:")
            print(f"  已爬取文章数: {len(seen_article_ids)}")
            if data.get('min_article_id'):
                print(f"  最小文章ID: {data.get('min_article_id')}")
            if data.get('max_article_id'):
                print(f"  最大文章ID: {data.get('max_article_id')}")

        stats = data.get('stats', {})
        if stats:
            print("\n📊 统计信息:")
            print(f"  已爬取帖子: {stats.get('crawled_count', stats.get('articles_found', 0))}")
            print(f"  下载图片: {stats.get('images_downloaded', 0)}")
            print(f"  失败数: {stats.get('failed_count', 0)}")
            if 'last_error' in stats:
                print(f"  最后错误: {stats['last_error']}")

        print("=" * 60)
    finally:
        storage.close()
