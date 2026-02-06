#!/usr/bin/env python3
"""
测试 crawl-news 性能的脚本

测试异步队列的性能提升效果
"""
import asyncio
import time
from loguru import logger
from spiders.dynamic_news_spider import DynamicNewsCrawler
from config import Config, ConfigLoader

# 测试URL（使用一个简单的测试页面）
TEST_URL = "https://sxd.xd.com/"  # 可以根据实际情况修改


async def test_performance(url: str, max_pages: int = 3, use_queue: bool = True, max_workers: int = 5):
    """
    测试爬取性能
    
    Args:
        url: 测试URL
        max_pages: 最大页数
        use_queue: 是否使用异步队列
        max_workers: 并发数
    """
    logger.info("=" * 60)
    logger.info(f"🚀 开始性能测试")
    logger.info(f"   URL: {url}")
    logger.info(f"   最大页数: {max_pages}")
    logger.info(f"   使用异步队列: {use_queue}")
    logger.info(f"   并发数: {max_workers}")
    logger.info("=" * 60)
    
    # 创建配置
    config = Config(
        bbs={
            "name": "测试网站",
            "base_url": url,
            "forum_type": "custom"
        },
        crawler={
            "max_concurrent_requests": max_workers,
            "use_async_queue": use_queue,
            "use_adaptive_queue": False,
            "download_delay": 0.5  # 较短的延迟用于测试
        }
    )
    
    # 创建爬虫
    crawler = DynamicNewsCrawler(config)
    
    start_time = time.time()
    
    async with crawler:
        # 爬取文章列表
        articles = await crawler.crawl_dynamic_page_ajax(
            url,
            max_pages=max_pages,
            resume=False,  # 不使用检查点
            start_page=1
        )
        
        logger.info(f"✅ 发现 {len(articles)} 篇文章")
        
        # 测试爬取文章详情（使用队列）
        if articles:
            logger.info(f"🚀 开始爬取文章详情（使用队列: {use_queue}）...")
            detail_start = time.time()
            
            full_articles = await crawler.crawl_articles_batch(
                articles[:10],  # 只测试前10篇
                use_queue=use_queue,
                max_workers=max_workers,
                use_adaptive=False
            )
            
            detail_time = time.time() - detail_start
            logger.info(f"✅ 完成文章详情爬取: {len(full_articles)} 篇")
            logger.info(f"⏱️  耗时: {detail_time:.2f} 秒")
            logger.info(f"📊 速度: {len(full_articles)/detail_time:.2f} 篇/秒")
    
    total_time = time.time() - start_time
    
    # 获取统计信息
    stats = crawler.get_statistics()
    
    logger.info("=" * 60)
    logger.info("📊 性能测试结果:")
    logger.info(f"   总耗时: {total_time:.2f} 秒")
    logger.info(f"   发现文章: {stats.get('articles_found', 0)}")
    logger.info(f"   爬取文章: {stats.get('articles_crawled', 0)}")
    logger.info(f"   失败文章: {stats.get('articles_failed', 0)}")
    logger.info(f"   获取页面: {stats.get('pages_fetched', 0)}")
    logger.info(f"   请求失败: {stats.get('requests_failed', 0)}")
    logger.info("=" * 60)
    
    return {
        'total_time': total_time,
        'articles_found': stats.get('articles_found', 0),
        'articles_crawled': stats.get('articles_crawled', 0),
        'articles_failed': stats.get('articles_failed', 0),
        'pages_fetched': stats.get('pages_fetched', 0),
        'requests_failed': stats.get('requests_failed', 0)
    }


async def compare_performance(url: str, max_pages: int = 3):
    """对比串行和并行的性能"""
    logger.info("\n" + "=" * 60)
    logger.info("📊 性能对比测试")
    logger.info("=" * 60)
    
    # 测试1: 串行模式（不使用队列）
    logger.info("\n🔹 测试1: 串行模式（不使用异步队列）")
    result_serial = await test_performance(url, max_pages, use_queue=False, max_workers=1)
    
    # 等待一下，避免影响
    await asyncio.sleep(2)
    
    # 测试2: 并行模式（使用队列，5个并发）
    logger.info("\n🔹 测试2: 并行模式（使用异步队列，5个并发）")
    result_parallel_5 = await test_performance(url, max_pages, use_queue=True, max_workers=5)
    
    # 等待一下
    await asyncio.sleep(2)
    
    # 测试3: 并行模式（使用队列，10个并发）
    logger.info("\n🔹 测试3: 并行模式（使用异步队列，10个并发）")
    result_parallel_10 = await test_performance(url, max_pages, use_queue=True, max_workers=10)
    
    # 对比结果
    logger.info("\n" + "=" * 60)
    logger.info("📈 性能对比总结")
    logger.info("=" * 60)
    
    if result_serial['articles_crawled'] > 0:
        serial_speed = result_serial['articles_crawled'] / result_serial['total_time']
        parallel_5_speed = result_parallel_5['articles_crawled'] / result_parallel_5['total_time']
        parallel_10_speed = result_parallel_10['articles_crawled'] / result_parallel_10['total_time']
        
        logger.info(f"\n串行模式:")
        logger.info(f"  耗时: {result_serial['total_time']:.2f} 秒")
        logger.info(f"  速度: {serial_speed:.2f} 篇/秒")
        
        logger.info(f"\n并行模式（5并发）:")
        logger.info(f"  耗时: {result_parallel_5['total_time']:.2f} 秒")
        logger.info(f"  速度: {parallel_5_speed:.2f} 篇/秒")
        logger.info(f"  提升: {parallel_5_speed/serial_speed:.2f}x")
        
        logger.info(f"\n并行模式（10并发）:")
        logger.info(f"  耗时: {result_parallel_10['total_time']:.2f} 秒")
        logger.info(f"  速度: {parallel_10_speed:.2f} 篇/秒")
        logger.info(f"  提升: {parallel_10_speed/serial_speed:.2f}x")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    import sys
    
    # 从命令行获取URL（可选）
    test_url = sys.argv[1] if len(sys.argv) > 1 else TEST_URL
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    logger.info(f"🎯 测试URL: {test_url}")
    logger.info(f"📄 最大页数: {max_pages}")
    
    # 运行性能对比测试
    asyncio.run(compare_performance(test_url, max_pages))
