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

  # 爬取单个 URL（自动检测配置，替代原 crawl-url --auto-detect）
  python spider.py crawl --url "https://bbs.xd.com/thread/123" --auto-detect

  # 爬取单个 URL / 板块（用 --url 或 --board 替换 config 内的 urls）
  python spider.py crawl --url "https://bbs.xd.com/thread/123" --config xindong
  python spider.py crawl --board "https://bbs.xd.com/forum?fid=21" --config xindong --max-pages 5

  # BBS：单帖 / 单板块（必须指定 --url 或 --board；可选 --config）
  python spider.py crawl-bbs --url "https://bbs.xd.com/thread/123" --config xindong
  python spider.py crawl-bbs --board "https://bbs.xd.com/forum?fid=21" --config xindong --max-pages 5

  # 新闻：单 URL（必须指定 URL；可选 --config）
  python spider.py crawl-news "https://sxd.xd.com/" --download-images --max-pages 5
  python spider.py crawl-news --url "https://sxd.xd.com/" --config sxd --download-images
        '''
    )

    # 创建子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令', required=True)

    # ============================================================================
    # 子命令: crawl - 统一爬取（支持 --config 全量 / --url 或 --board 单目标 / --auto-detect）
    # ============================================================================
    parser_crawl = subparsers.add_parser('crawl', help='统一爬取：--config 爬全量，--url/--board 爬单目标，--url + --auto-detect 自动检测')
    parser_crawl.add_argument('--config', type=str,
                              help='配置文件名 (configs/ 下，如 sxd / xindong)；与 --url/--board 同用时仅提供配置，目标以参数为准')
    parser_crawl.add_argument('--url', type=str,
                              help='单个 URL（帖子或新闻页）；与 --auto-detect 同用则自动检测 BBS 配置')
    parser_crawl.add_argument('--board', type=str,
                              help='单个板块 URL（仅 BBS）；需配合 --config')
    parser_crawl.add_argument('--auto-detect', action='store_true',
                              help='从 --url 自动检测论坛类型（仅 BBS）')
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
    # 子命令: crawl-bbs - BBS 单帖/单板块（合并原 crawl-url 与 crawl-board）
    # ============================================================================
    parser_bbs = subparsers.add_parser('crawl-bbs', help='BBS：爬取单个帖子(--url)或单个板块(--board)；可选 --config 提供配置')
    parser_bbs.add_argument('--url', type=str, help='帖子 URL')
    parser_bbs.add_argument('--board', type=str, help='板块 URL')
    parser_bbs.add_argument('--config', type=str, help='配置文件名（可选）')
    parser_bbs.add_argument('--max-pages', type=int, default=None, help='最大页数（仅 --board 时有效）')
    parser_bbs.add_argument('--resume', action='store_true', default=True, help='从检查点恢复')
    parser_bbs.add_argument('--no-resume', dest='resume', action='store_false', help='不从检查点恢复')
    parser_bbs.add_argument('--start-page', type=int, default=None, help='起始页码')
    parser_bbs.add_argument('--max-workers', type=int, default=None, help='最大并发数')
    parser_bbs.add_argument('--use-adaptive-queue', action='store_true', default=None, help='使用自适应队列')
    parser_bbs.add_argument('--no-async-queue', dest='use_async_queue', action='store_false', help='禁用异步队列')

    # ============================================================================
    # 子命令: crawl-news - 爬取动态新闻（必须指定 URL，不再支持仅 --config）
    # ============================================================================
    parser_news = subparsers.add_parser('crawl-news', help='爬取动态新闻页面（必须指定 URL；爬全量请用 crawl --config sxd）')
    parser_news.add_argument('url', type=str, nargs='?', default=None, help='新闻页面 URL')
    parser_news.add_argument('--url', type=str, dest='news_url', help='新闻页面 URL（与 positional 二选一）')
    parser_news.add_argument('--config', type=str, help='配置文件名（可选，仅提供爬虫参数）')
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
