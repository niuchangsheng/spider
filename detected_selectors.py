# 自动检测的选择器配置
# URL: https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21
# 检测时间: 2026-02-03 23:16:39.307512

# 自动检测的选择器配置
BBSConfig(
    # 论坛类型: discuz
    base_url="需要手动设置",
    
    # 自动检测的选择器（置信度: 95.00%）
    thread_list_selector="tbody[id^='normalthread'], tbody[id^='stickthread']",
    thread_link_selector="a",
    image_selector="div.content img",
    next_page_selector="a.nxt.font-icon",
)