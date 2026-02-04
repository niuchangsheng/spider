# 这是新的 main 函数 - 子命令模式
# 完成测试后将替换 spider.py 中的 main 函数

import asyncio
import argparse
from pathlib import Path
import sys
from loguru import logger

# 导入必要的模块（实际使用时需要）
# from config import Config, ConfigLoader, ForumPresets, get_example_config, get_forum_boards, get_forum_urls
# from spider import SpiderFactory

async def main():
    """主函数 - 子命令模式 (v2.1)"""
    # 主解析器
    parser = argparse.ArgumentParser(
        prog='spider.py',
        description='BBS图片爬虫 (v2.1 - 子命令模式)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 爬取单个URL（自动检测配置）
  python spider.py crawl-url "https://bbs.xd.com/thread/123" --auto-detect
  
  # 爬取单个URL（使用配置）
  python spider.py crawl-url "https://bbs.xd.com/thread/123" --config xindong
  
  # 爬取配置中的所有URLs
  python spider.py crawl-urls --config xindong
  
  # 爬取板块（前5页）
  python spider.py crawl-board "https://bbs.xd.com/forum?fid=21" --config xindong --max-pages 5
  
  # 爬取配置中的所有板块
  python spider.py crawl-boards --config xindong
        '''
    )
    
    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令', required=True)
    
    # ============================================================================
    # 子命令1: crawl-url - 爬取单个URL
    # ============================================================================
    parser_url = subparsers.add_parser('crawl-url', help='爬取单个URL')
    parser_url.add_argument('url', type=str, help='帖子URL')
    
    config_group_url = parser_url.add_mutually_exclusive_group()
    config_group_url.add_argument('--auto-detect', action='store_true',
                                  help='自动检测论坛类型')
    config_group_url.add_argument('--preset', type=str,
                                  help='论坛类型预设 (discuz/phpbb/vbulletin)')
    config_group_url.add_argument('--config', type=str,
                                  help='配置文件名 (从 configs/ 加载)')
    
    # ============================================================================
    # 子命令2: crawl-urls - 爬取配置中的URL列表
    # ============================================================================
    parser_urls = subparsers.add_parser('crawl-urls', help='爬取配置中的URL列表')
    parser_urls.add_argument('--config', type=str, required=True,
                            help='配置文件名 (必需)')
    
    # ============================================================================
    # 子命令3: crawl-board - 爬取单个板块
    # ============================================================================
    parser_board = subparsers.add_parser('crawl-board', help='爬取单个板块')
    parser_board.add_argument('board_url', type=str, help='板块URL')
    parser_board.add_argument('--max-pages', type=int, default=None,
                             help='最大页数（默认：爬取所有页）')
    
    config_group_board = parser_board.add_mutually_exclusive_group()
    config_group_board.add_argument('--auto-detect', action='store_true',
                                   help='自动检测论坛类型')
    config_group_board.add_argument('--preset', type=str,
                                   help='论坛类型预设 (discuz/phpbb/vbulletin)')
    config_group_board.add_argument('--config', type=str,
                                   help='配置文件名 (从 configs/ 加载)')
    
    # ============================================================================
    # 子命令4: crawl-boards - 爬取配置中的所有板块
    # ============================================================================
    parser_boards = subparsers.add_parser('crawl-boards', help='爬取配置中的所有板块')
    parser_boards.add_argument('--config', type=str, required=True,
                              help='配置文件名 (必需)')
    parser_boards.add_argument('--max-pages', type=int, default=None,
                              help='每个板块最大页数（默认：爬取所有页）')
    
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
    print("🕷️  BBS图片爬虫 (v2.1 - 子命令模式)")
    print("=" * 60)
    
    # 根据子命令执行相应操作
    if args.command == 'crawl-url':
        await handle_crawl_url(args)
    elif args.command == 'crawl-urls':
        await handle_crawl_urls(args)
    elif args.command == 'crawl-board':
        await handle_crawl_board(args)
    elif args.command == 'crawl-boards':
        await handle_crawl_boards(args)


async def handle_crawl_url(args):
    """处理 crawl-url 子命令"""
    from config import ConfigLoader, get_example_config
    from spider import SpiderFactory
    
    print(f"\n📌 命令: 爬取单个URL")
    print(f"URL: {args.url}")
    
    # 1. 加载配置
    if args.auto_detect:
        logger.info(f"🌐 自动检测配置: {args.url}")
        config = await ConfigLoader.auto_detect_config(args.url)
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
    from config import get_example_config, get_forum_urls
    from spider import SpiderFactory
    
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
    from config import ConfigLoader, get_example_config
    from spider import SpiderFactory
    
    print(f"\n📌 命令: 爬取单个板块")
    print(f"板块URL: {args.board_url}")
    if args.max_pages:
        print(f"最大页数: {args.max_pages}")
    else:
        print(f"最大页数: 不限制（爬取所有页）")
    
    # 1. 加载配置
    if args.auto_detect:
        logger.info(f"🌐 自动检测配置: {args.board_url}")
        config = await ConfigLoader.auto_detect_config(args.board_url)
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
    from config import get_example_config, get_forum_boards
    from spider import SpiderFactory
    
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


if __name__ == "__main__":
    asyncio.run(main())
