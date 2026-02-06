"""
BBS图片爬虫 - CLI入口

v2.3 文件结构重构后，spider.py 仅作为CLI入口点。

架构:
- core/base.py: BaseSpider + BaseParser 基类
- parsers/: 解析器模块
- spiders/: 爬虫模块
- cli/: CLI处理模块
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

from cli import (
    create_parser, 
    handle_crawl_url, 
    handle_crawl_urls, 
    handle_crawl_board, 
    handle_crawl_boards, 
    handle_crawl_news,
    handle_checkpoint_status
)


async def main():
    """主函数 - CLI入口"""
    # 创建参数解析器
    parser = create_parser()
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
    print("🕷️  BBS图片爬虫 (v2.3 - 文件结构重构)")
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
    elif args.command == 'crawl-news':
        await handle_crawl_news(args)
    elif args.command == 'checkpoint-status':
        await handle_checkpoint_status(args)


if __name__ == "__main__":
    asyncio.run(main())
