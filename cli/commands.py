"""
CLI命令定义（argparse）
"""
import argparse


def create_parser() -> argparse.ArgumentParser:
    """
    创建命令行参数解析器

    Returns:
        ArgumentParser 实例
    """
    parser = argparse.ArgumentParser(
        prog='spider.py',
        description='BBS图片爬虫 (v2.3 - 子命令模式)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 统一爬取（由 config 决定 BBS 或 新闻；爬取 config 内全部 urls）
  python spider.py crawl --config sxd --download-images
  python spider.py crawl --config xindong --max-pages 5

  # BBS：单帖 / 单板块（位置参数 + --type thread|board；--config 或 --auto-detect）
  python spider.py crawl-bbs "https://bbs.xd.com/thread/123" --type thread --config xindong
  python spider.py crawl-bbs "https://bbs.xd.com/forum?fid=21" --type board --config xindong --max-pages 5
  python spider.py crawl-bbs "https://bbs.xd.com/thread/123" --type thread --auto-detect

  # 新闻：单 URL（爬全量用 crawl --config sxd）
  python spider.py crawl-news "https://sxd.xd.com/" --config sxd --download-images --max-pages 5
        '''
    )

    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令', required=True)

    # ============================================================================
    # 子命令: crawl - 统一爬取（仅 --config 全量）
    # ============================================================================
    parser_crawl = subparsers.add_parser('crawl', help='按 config 爬取全部 urls（BBS/新闻由 config 决定）')
    parser_crawl.add_argument('--config', type=str, required=True,
                              help='配置文件名 (configs/ 下，如 sxd / xindong)')
    parser_crawl.add_argument('--max-pages', type=int, default=None,
                              help='最大页数（BBS 板块/新闻列表）')
    parser_crawl.add_argument('--resume', action='store_true', default=True,
                              help='从检查点恢复（默认：启用）')
    parser_crawl.add_argument('--no-resume', dest='resume', action='store_false',
                              help='不从检查点恢复')
    parser_crawl.add_argument('--start-page', type=int, default=None,
                              help='起始页码（覆盖检查点）')
    parser_crawl.add_argument('--max-workers', type=int, default=None,
                              help='最大并发数')
    parser_crawl.add_argument('--use-adaptive-queue', action='store_true', default=None,
                              help='使用自适应队列')
    parser_crawl.add_argument('--no-async-queue', dest='use_async_queue', action='store_false',
                              help='禁用异步队列')
    parser_crawl.add_argument('--download-images', action='store_true',
                              help='（仅新闻）下载文章中的图片')
    parser_crawl.add_argument('--method', type=str, default='ajax',
                              choices=['ajax', 'selenium'],
                              help='（仅新闻）爬取方式：ajax 或 selenium')

    # ============================================================================
    # 子命令: crawl-bbs - BBS 单帖/单板块（位置参数 + --type thread|board）
    # ============================================================================
    parser_bbs = subparsers.add_parser('crawl-bbs', help='BBS：爬取单个帖子或板块，位置参数为 URL，--type thread|board 区分')
    parser_bbs.add_argument('target', type=str, help='帖子 URL 或板块 URL')
    parser_bbs.add_argument('--type', type=str, required=True, choices=['thread', 'board'],
                            help='thread=单帖，board=单板块')
    parser_bbs.add_argument('--config', type=str, help='配置文件名（与 --auto-detect 二选一）')
    parser_bbs.add_argument('--auto-detect', action='store_true', help='从 target URL 自动检测论坛类型（仅 crawl-bbs 支持）')
    parser_bbs.add_argument('--max-pages', type=int, default=None, help='最大页数（仅 --board 时有效）')
    parser_bbs.add_argument('--resume', action='store_true', default=True, help='从检查点恢复')
    parser_bbs.add_argument('--no-resume', dest='resume', action='store_false', help='不从检查点恢复')
    parser_bbs.add_argument('--start-page', type=int, default=None, help='起始页码')
    parser_bbs.add_argument('--max-workers', type=int, default=None, help='最大并发数')
    parser_bbs.add_argument('--use-adaptive-queue', action='store_true', default=None, help='使用自适应队列')
    parser_bbs.add_argument('--no-async-queue', dest='use_async_queue', action='store_false', help='禁用异步队列')

    # ============================================================================
    # 子命令: crawl-news - 爬取动态新闻单页（必须传 URL；爬全量用 crawl --config sxd）
    # ============================================================================
    parser_news = subparsers.add_parser('crawl-news', help='爬取动态新闻单页（传 URL）；爬全量用 crawl --config sxd')
    parser_news.add_argument('url', type=str, help='新闻页面 URL')
    parser_news.add_argument('--config', type=str, help='配置文件名（可选，提供爬虫参数）')
    parser_news.add_argument('--max-pages', type=int, default=None, help='最大页数')
    parser_news.add_argument('--method', type=str, default='ajax', choices=['ajax', 'selenium'], help='爬取方式')
    parser_news.add_argument('--download-images', action='store_true', help='是否下载文章中的图片')
    parser_news.add_argument('--resume', action='store_true', default=True, help='从检查点恢复')
    parser_news.add_argument('--no-resume', dest='resume', action='store_false', help='不从检查点恢复')
    parser_news.add_argument('--start-page', type=int, default=None, help='起始页码')
    parser_news.add_argument('--max-workers', type=int, default=None, help='最大并发数')
    parser_news.add_argument('--use-adaptive-queue', action='store_true', default=None, help='使用自适应队列')
    parser_news.add_argument('--no-async-queue', dest='use_async_queue', action='store_false', help='禁用异步队列')

    # ============================================================================
    # 子命令: checkpoint-status - 查看检查点状态
    # ============================================================================
    parser_checkpoint = subparsers.add_parser('checkpoint-status', help='查看检查点状态')
    parser_checkpoint.add_argument('--site', type=str, required=True, help='网站域名（如 sxd.xd.com）')
    parser_checkpoint.add_argument('--board', type=str, default='all', help='板块名称（默认：all）')
    parser_checkpoint.add_argument('--clear', action='store_true', help='清除检查点')

    return parser
