"""
自定义选择器示例
展示如何为不同的BBS论坛配置选择器
"""

# ============ Discuz论坛示例 ============
DISCUZ_SELECTORS = {
    "thread_list_selector": "tbody[id^='normalthread']",
    "thread_link_selector": "a.s.xst",
    "image_selector": "img.zoom, img[file], div.pattl img",
    "next_page_selector": "a.nxt",
}

# 使用方法：
# 在 config.py 的 BBSConfig 类中设置这些值


# ============ phpBB论坛示例 ============
PHPBB_SELECTORS = {
    "thread_list_selector": "li.row",
    "thread_link_selector": "a.topictitle",
    "image_selector": "dl.attachbox img, div.content img",
    "next_page_selector": "li.next a",
}


# ============ vBulletin论坛示例 ============
VBULLETIN_SELECTORS = {
    "thread_list_selector": "li.threadbit",
    "thread_link_selector": "a.title",
    "image_selector": "div.postbody img, div.content img",
    "next_page_selector": "a[rel='next']",
}


# ============ 自定义论坛示例 ============
# 步骤1: 打开目标论坛
# 步骤2: 按F12打开开发者工具
# 步骤3: 找到帖子列表的HTML结构
# 步骤4: 编写CSS选择器

# 例如，如果帖子列表结构是：
# <div class="topics">
#   <div class="topic-item">
#     <a class="topic-title" href="/thread/123">标题</a>
#   </div>
# </div>

CUSTOM_SELECTORS = {
    "thread_list_selector": "div.topic-item",
    "thread_link_selector": "a.topic-title",
    "image_selector": "div.post-content img, img.post-image",
    "next_page_selector": "a.pagination-next",
}


# ============ 如何使用 ============
"""
方法1：直接在 config.py 中修改默认值

class BBSConfig(BaseModel):
    thread_list_selector: str = Field(default="div.topic-item")
    thread_link_selector: str = Field(default="a.topic-title")
    ...

方法2：通过环境变量设置（不推荐，选择器通常很长）

方法3：在运行时动态设置

from config import config

config.bbs.thread_list_selector = "tbody[id^='normalthread']"
config.bbs.thread_link_selector = "a.s.xst"
config.bbs.image_selector = "img.zoom, img[file]"
config.bbs.next_page_selector = "a.nxt"
"""


# ============ 测试选择器工具函数 ============
def test_selectors(html_content: str, selectors: dict):
    """
    测试选择器是否有效
    
    Args:
        html_content: HTML内容（可以从浏览器复制）
        selectors: 选择器字典
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'lxml')
    
    print("测试选择器...")
    for name, selector in selectors.items():
        elements = soup.select(selector)
        print(f"\n{name}: {selector}")
        print(f"  匹配到 {len(elements)} 个元素")
        if elements:
            print(f"  第一个元素: {elements[0].name}")
            print(f"  内容预览: {str(elements[0])[:100]}...")


if __name__ == "__main__":
    print("自定义选择器配置示例")
    print("\n可用的预设配置:")
    print("1. Discuz论坛")
    print("2. phpBB论坛")
    print("3. vBulletin论坛")
    print("4. 自定义论坛")
    
    print("\n使用方法：")
    print("1. 在浏览器中打开目标论坛")
    print("2. 按F12打开开发者工具")
    print("3. 使用元素选择器（Ctrl+Shift+C）选择帖子列表")
    print("4. 查看HTML结构，编写CSS选择器")
    print("5. 在 config.py 中配置选择器")
