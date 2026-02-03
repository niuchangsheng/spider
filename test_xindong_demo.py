"""
心动论坛爬虫 - 演示版本（仅使用Python标准库）
用于测试配置是否正确
"""
import urllib.request
import urllib.parse
from html.parser import HTMLParser
import re
import sys

# 心动论坛配置
XINDONG_BASE_URL = "https://bbs.xd.com"
EXAMPLE_THREAD = "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1"


class ImageExtractor(HTMLParser):
    """简单的HTML图片提取器"""
    
    def __init__(self):
        super().__init__()
        self.images = []
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            attrs_dict = dict(attrs)
            # 提取图片URL
            src = attrs_dict.get('src') or attrs_dict.get('file') or attrs_dict.get('data-src')
            if src and not src.startswith('static/'):
                self.images.append(src)
        
        # 检查附件链接
        if tag == 'a':
            attrs_dict = dict(attrs)
            href = attrs_dict.get('href', '')
            if 'mod=attachment' in href:
                self.images.append(href)


def fetch_page(url):
    """获取页面内容"""
    print(f"\n正在获取页面: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            print(f"✓ 页面获取成功，大小: {len(html)} 字节")
            return html
    except Exception as e:
        print(f"✗ 页面获取失败: {e}")
        return None


def extract_images(html):
    """提取图片链接"""
    parser = ImageExtractor()
    try:
        parser.feed(html)
    except:
        pass
    
    images = []
    for img in parser.images:
        # 处理相对路径
        if img.startswith('forum.php') or img.startswith('/forum.php'):
            img = f"{XINDONG_BASE_URL}/{img.lstrip('/')}"
        
        # 添加参数获取原图
        if 'mod=attachment' in img and 'nothumb' not in img:
            img += '&nothumb=yes'
        
        # 过滤无效链接
        if img.startswith('http') or img.startswith('//'):
            if img.startswith('//'):
                img = 'https:' + img
            images.append(img)
    
    return list(set(images))  # 去重


def extract_thread_info(html):
    """提取帖子信息"""
    info = {}
    
    # 提取标题（简单正则匹配）
    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        info['title'] = title_match.group(1).strip()
    
    # 提取作者
    author_match = re.search(r'class="author"[^>]*>(.*?)</a>', html)
    if author_match:
        info['author'] = re.sub(r'<[^>]+>', '', author_match.group(1)).strip()
    
    # 提取查看数
    view_match = re.search(r'查看:\s*(\d+)', html)
    if view_match:
        info['views'] = view_match.group(1)
    
    # 提取回复数
    reply_match = re.search(r'回复:\s*(\d+)', html)
    if reply_match:
        info['replies'] = reply_match.group(1)
    
    return info


def main():
    """主函数"""
    print("=" * 70)
    print("心动论坛爬虫 - 演示版本")
    print("=" * 70)
    print("\n📌 目标帖子:")
    print(f"   {EXAMPLE_THREAD}")
    print("\n⚠️  这是一个演示版本，仅使用Python标准库")
    print("   完整功能请安装依赖后使用 crawl_xindong.py")
    
    # 获取页面
    html = fetch_page(EXAMPLE_THREAD)
    if not html:
        print("\n❌ 无法获取页面，请检查网络连接")
        return
    
    # 提取帖子信息
    print("\n" + "=" * 70)
    print("📋 帖子信息:")
    print("=" * 70)
    
    info = extract_thread_info(html)
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # 提取图片
    print("\n" + "=" * 70)
    print("🖼️  图片链接:")
    print("=" * 70)
    
    images = extract_images(html)
    
    if images:
        print(f"\n发现 {len(images)} 张图片:\n")
        for i, img_url in enumerate(images, 1):
            print(f"{i:2d}. {img_url}")
            
            # 检查是否是附件
            if 'mod=attachment' in img_url:
                print(f"    └─ [附件] 需要下载才能查看")
            
        print("\n" + "=" * 70)
        print("✅ 图片提取完成！")
        print("=" * 70)
        
        print("\n💡 下一步:")
        print("   1. 安装完整依赖: pip3 install -r requirements.txt")
        print("   2. 运行完整版本: python3 crawl_xindong.py")
        print("   3. 图片将自动下载到 downloads/ 目录")
    else:
        print("\n❌ 未发现图片链接")
        print("   可能原因:")
        print("   - 页面结构已变化")
        print("   - 需要登录才能查看")
        print("   - 网络问题")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
