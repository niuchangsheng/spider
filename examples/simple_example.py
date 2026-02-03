"""
简单示例 - BBS图片爬虫
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from bbs_spider import BBSSpider
from loguru import logger


async def example_1_crawl_single_thread():
    """示例1：爬取单个帖子"""
    print("\n" + "="*60)
    print("示例1：爬取单个帖子")
    print("="*60)
    
    async with BBSSpider() as spider:
        # 修改为实际的帖子URL
        thread_url = "https://example.com/thread/12345"
        
        thread_info = {
            'url': thread_url,
            'thread_id': spider.parser._extract_thread_id(thread_url),
            'board': 'example_board'
        }
        
        await spider.crawl_thread(thread_info)
        
        # 显示统计
        stats = spider.get_statistics()
        print(f"\n下载完成！")
        print(f"图片数量: {stats['images_downloaded']}")


async def example_2_crawl_board():
    """示例2：爬取板块（前3页）"""
    print("\n" + "="*60)
    print("示例2：爬取板块")
    print("="*60)
    
    async with BBSSpider() as spider:
        # 修改为实际的板块URL
        board_url = "https://example.com/forum/photos"
        board_name = "图片板块"
        
        await spider.crawl_board(
            board_url=board_url,
            board_name=board_name,
            max_pages=3  # 只爬取前3页
        )


async def example_3_crawl_multiple_threads():
    """示例3：批量爬取多个帖子"""
    print("\n" + "="*60)
    print("示例3：批量爬取帖子")
    print("="*60)
    
    # 准备要爬取的帖子列表
    thread_urls = [
        "https://example.com/thread/12345",
        "https://example.com/thread/23456",
        "https://example.com/thread/34567",
    ]
    
    async with BBSSpider() as spider:
        await spider.crawl_threads_from_list(thread_urls)


def main():
    """主函数"""
    print("BBS图片爬虫 - 使用示例")
    print("\n请选择要运行的示例：")
    print("1. 爬取单个帖子")
    print("2. 爬取板块（前3页）")
    print("3. 批量爬取多个帖子")
    print("\n注意：运行前请先修改代码中的URL为实际的BBS地址！")
    
    choice = input("\n请输入选项 (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(example_1_crawl_single_thread())
    elif choice == "2":
        asyncio.run(example_2_crawl_board())
    elif choice == "3":
        asyncio.run(example_3_crawl_multiple_threads())
    else:
        print("无效的选项！")


if __name__ == "__main__":
    main()
