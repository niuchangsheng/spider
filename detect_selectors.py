#!/usr/bin/env python3
"""
选择器自动检测工具
用法: python detect_selectors.py <URL>
"""
import sys
import asyncio
import aiohttp
from loguru import logger
from pathlib import Path

from core.selector_detector import SelectorDetector


async def fetch_page(url: str) -> str:
    """获取页面内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, timeout=30) as response:
            return await response.text()


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # 获取URL
    if len(sys.argv) < 2:
        print("用法: python detect_selectors.py <URL>")
        print("\n示例:")
        print("  python detect_selectors.py https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21")
        sys.exit(1)
    
    url = sys.argv[1]
    
    print("\n" + "=" * 70)
    print("🔍 智能选择器自动检测工具")
    print("=" * 70)
    print(f"\n目标URL: {url}\n")
    
    try:
        # 获取页面
        logger.info("正在获取页面...")
        html = await fetch_page(url)
        logger.info(f"页面大小: {len(html):,} 字节")
        
        # 检测选择器
        detector = SelectorDetector()
        result = detector.auto_detect_selectors(html, url)
        
        # 显示结果
        print("\n" + "=" * 70)
        print("📋 检测结果")
        print("=" * 70)
        
        print(f"\n论坛类型: {result['forum_type']}")
        print(f"\n选择器配置:")
        print(f"  thread_list_selector  : {result['selectors']['thread_list_selector']}")
        print(f"  thread_link_selector  : {result['selectors']['thread_link_selector']}")
        print(f"  image_selector        : {result['selectors']['image_selector']}")
        print(f"  next_page_selector    : {result['selectors']['next_page_selector']}")
        
        print(f"\n置信度:")
        print(f"  帖子列表: {result['confidence']['thread_list']:.2%}")
        print(f"  帖子链接: {result['confidence']['thread_link']:.2%}")
        print(f"  图片    : {result['confidence']['image']:.2%}")
        print(f"  下一页  : {result['confidence']['next_page']:.2%}")
        print(f"  总体    : {result['confidence']['overall']:.2%}")
        
        # 生成配置代码
        print("\n" + "=" * 70)
        print("📝 生成的配置代码")
        print("=" * 70)
        print(detector.generate_config_code(result))
        
        # 状态评估
        print("\n" + "=" * 70)
        if result['status'] == 'success':
            print("✅ 检测成功! 可以直接使用这些选择器")
        else:
            print("⚠️  检测不确定，建议手动验证选择器")
        print("=" * 70)
        
        # 保存到文件
        output_file = Path("detected_selectors.py")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# 自动检测的选择器配置\n")
            f.write(f"# URL: {url}\n")
            f.write(f"# 检测时间: {__import__('datetime').datetime.now()}\n\n")
            f.write(detector.generate_config_code(result))
        
        print(f"\n💾 配置已保存到: {output_file}")
        
    except Exception as e:
        logger.error(f"检测失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
