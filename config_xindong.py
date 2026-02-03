"""
心动论坛（Discuz系统）专用配置
针对 https://bbs.xd.com 进行优化
"""
from config import Config

# 心动论坛配置
xindong_config = Config(
    bbs={
        # 基础配置
        "base_url": "https://bbs.xd.com",
        "login_url": "https://bbs.xd.com/member.php?mod=logging&action=login",
        "login_required": False,  # 如需爬取更多内容，可设置为True并配置账号
        
        # 选择器配置（Discuz论坛专用）
        # 帖子列表页选择器
        "thread_list_selector": "tbody[id^='normalthread'], tbody[id^='stickthread']",
        "thread_link_selector": "a.s.xst, a.xst",
        
        # 帖子详情页图片选择器
        # Discuz的图片通常在附件或帖子内容中
        "image_selector": """
            img.zoom,
            img[file],
            img[aid],
            div.pattl img,
            div.pcb img,
            td.t_f img,
            div.content img,
            ignore.t_attach img
        """.replace('\n', '').replace(' ', ''),
        
        # 下一页选择器
        "next_page_selector": "a.nxt, div.pg a.nxt",
    },
    
    crawler={
        # 爬虫参数（针对心动论坛优化）
        "max_concurrent_requests": 3,  # 降低并发，避免被封
        "download_delay": 2.0,  # 增加延迟
        "request_timeout": 30,
        "max_retries": 3,
        "rotate_user_agent": True,
    },
    
    image={
        # 图片过滤配置
        "min_width": 300,  # 心动论坛的宣传图一般较大
        "min_height": 300,
        "min_size": 30000,  # 30KB以上
        "max_size": 10 * 1024 * 1024,  # 10MB
        
        # 图片处理
        "enable_deduplication": True,
        "compress_images": False,
        "convert_to_jpg": False,
        
        # 允许的格式
        "allowed_formats": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
    }
)


# 具体的爬取配置示例
XINDONG_BOARDS = {
    "神仙道": {
        "url": "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21",
        "board_name": "神仙道",
    },
    "玩家交流区": {
        "url": "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21",
        "board_name": "神仙道玩家交流",
    }
}


# 特定帖子示例
EXAMPLE_THREADS = [
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1",
]
