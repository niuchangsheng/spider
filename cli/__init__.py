"""
CLI模块

包含命令行接口相关功能：
- handlers: 命令处理函数
- commands: argparse 定义
"""
from cli.handlers import (
    handle_crawl_url,
    handle_crawl_urls,
    handle_crawl_board,
    handle_crawl_boards,
    handle_crawl_news,
    handle_checkpoint_status,
    print_statistics,
)
from cli.commands import create_parser

__all__ = [
    'handle_crawl_url',
    'handle_crawl_urls',
    'handle_crawl_board',
    'handle_crawl_boards',
    'handle_crawl_news',
    'handle_checkpoint_status',
    'print_statistics',
    'create_parser',
]
