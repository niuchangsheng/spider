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
  
  # 爬取动态新闻页面（单个URL）
  python spider.py crawl-news "https://sxd.xd.com/" --download-images --max-pages 5
  
  # 爬取配置文件中的所有新闻URL
  python spider.py crawl-news --config news --download-images
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
    parser_board = subparsers.add_parser('crawl-board', help='爬取单个板块（支持断点续传）')
    parser_board.add_argument('board_url', type=str, help='板块URL')
    parser_board.add_argument('--max-pages', type=int, default=None,
                             help='最大页数（默认：爬取所有页）')
    parser_board.add_argument('--resume', action='store_true', default=True,
                             help='从检查点恢复（默认：启用）')
    parser_board.add_argument('--no-resume', dest='resume', action='store_false',
                             help='不从检查点恢复（从头开始）')
    parser_board.add_argument('--start-page', type=int, default=None,
                             help='起始页码（覆盖检查点）')
    
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
    parser_boards.add_argument('--resume', action='store_true', default=True,
                              help='从检查点恢复（默认：启用）')
    parser_boards.add_argument('--no-resume', dest='resume', action='store_false',
                              help='不从检查点恢复（从头开始）')
    parser_boards.add_argument('--start-page', type=int, default=None,
                              help='起始页码（覆盖检查点，适用于所有板块）')
    
    # ============================================================================
    # 子命令5: crawl-news - 爬取动态新闻页面
    # ============================================================================
    parser_news = subparsers.add_parser('crawl-news', help='爬取动态新闻页面（支持Ajax加载更多）')
    parser_news.add_argument('url', type=str, nargs='?', default=None,
                            help='新闻页面URL（可选，如果使用--config则从配置文件读取）')
    parser_news.add_argument('--max-pages', type=int, default=None,
                            help='最大页数（默认：爬取所有页）')
    parser_news.add_argument('--method', type=str, default='ajax',
                            choices=['ajax', 'selenium'],
                            help='爬取方式：ajax(快速) 或 selenium(可靠)，默认ajax')
    parser_news.add_argument('--download-images', action='store_true',
                            help='是否下载文章中的图片')
    parser_news.add_argument('--config', type=str,
                            help='配置文件名（可选，用于从配置文件读取news_urls并全部爬取）')
    
    # ============================================================================
    # 子命令6: checkpoint-status - 查看检查点状态
    # ============================================================================
    parser_checkpoint = subparsers.add_parser('checkpoint-status', 
                                             help='查看检查点状态')
    parser_checkpoint.add_argument('--site', type=str, required=True,
                                  help='网站域名（如 sxd.xd.com）')
    parser_checkpoint.add_argument('--board', type=str, default='all',
                                  help='板块名称（默认：all）')
    parser_checkpoint.add_argument('--clear', action='store_true',
                                  help='清除检查点')
    
    return parser
