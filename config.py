"""
配置管理模块 - BBS图片爬虫
统一配置管理，支持多论坛预设
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent


class BBSConfig(BaseModel):
    """BBS论坛配置"""
    # 基础信息
    name: str = Field(default="default", description="配置名称")
    forum_type: str = Field(default="generic", description="论坛类型: discuz/phpbb/vbulletin/generic")
    base_url: str = Field(default="", description="BBS论坛基础URL")
    login_url: Optional[str] = Field(default=None, description="登录URL")
    
    # 认证信息
    login_required: bool = Field(default=False, description="是否需要登录")
    username: Optional[str] = Field(default=None, description="用户名")
    password: Optional[str] = Field(default=None, description="密码")
    
    # 爬取范围
    target_boards: List[str] = Field(default_factory=list, description="目标板块列表")
    start_page: int = Field(default=1, description="起始页码")
    end_page: Optional[int] = Field(default=None, description="结束页码")
    
    # 选择器配置（根据具体BBS调整）
    thread_list_selector: str = Field(default="div.thread-item", description="帖子列表选择器")
    thread_link_selector: str = Field(default="a.thread-link", description="帖子链接选择器")
    image_selector: str = Field(default="img.post-image, img[src*='jpg'], img[src*='png']", description="图片选择器")
    next_page_selector: str = Field(default="a.next-page", description="下一页选择器")


class CrawlerConfig(BaseModel):
    """爬虫配置"""
    # 并发控制
    max_concurrent_requests: int = Field(default=5, description="最大并发请求数")
    download_delay: float = Field(default=1.0, description="下载延迟（秒）")
    request_timeout: int = Field(default=30, description="请求超时时间")
    
    # 重试配置
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: float = Field(default=2.0, description="重试延迟（秒）")
    
    # 代理配置
    use_proxy: bool = Field(default=False, description="是否使用代理")
    proxy_list: List[str] = Field(default_factory=list, description="代理列表")
    
    # User-Agent配置
    rotate_user_agent: bool = Field(default=True, description="是否轮换UA")
    custom_user_agents: List[str] = Field(default_factory=list, description="自定义UA列表")


class ImageConfig(BaseModel):
    """图片配置"""
    # 存储路径
    download_dir: Path = Field(default=BASE_DIR / "downloads", description="下载目录")
    temp_dir: Path = Field(default=BASE_DIR / "temp", description="临时目录")
    
    # 图片过滤
    min_width: int = Field(default=200, description="最小宽度")
    min_height: int = Field(default=200, description="最小高度")
    min_size: int = Field(default=10240, description="最小文件大小（字节）")
    max_size: int = Field(default=20*1024*1024, description="最大文件大小（字节）")
    
    # 图片格式
    allowed_formats: List[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "gif", "webp"],
        description="允许的图片格式"
    )
    
    # 图片处理
    enable_deduplication: bool = Field(default=True, description="启用图片去重")
    compress_images: bool = Field(default=False, description="是否压缩图片")
    convert_to_jpg: bool = Field(default=False, description="转换为JPG格式")
    quality: int = Field(default=85, description="压缩质量")
    
    # 命名规则
    filename_pattern: str = Field(
        default="{board}_{thread_id}_{index}_{timestamp}",
        description="文件命名模式"
    )


class DatabaseConfig(BaseModel):
    """数据库配置"""
    # MongoDB
    mongodb_uri: str = Field(default="mongodb://localhost:27017/", description="MongoDB连接URI")
    mongodb_db: str = Field(default="bbs_spider", description="数据库名称")
    
    # Redis
    redis_host: str = Field(default="localhost", description="Redis主机")
    redis_port: int = Field(default=6379, description="Redis端口")
    redis_db: int = Field(default=0, description="Redis数据库")
    redis_password: Optional[str] = Field(default=None, description="Redis密码")


class LogConfig(BaseModel):
    """日志配置"""
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: Path = Field(default=BASE_DIR / "logs", description="日志目录")
    log_file: str = Field(default="bbs_spider.log", description="日志文件名")
    rotation: str = Field(default="100 MB", description="日志轮转大小")
    retention: str = Field(default="30 days", description="日志保留时间")


class Config(BaseModel):
    """全局配置"""
    bbs: BBSConfig = Field(default_factory=BBSConfig)
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    log: LogConfig = Field(default_factory=LogConfig)
    
    def __init__(self, **data):
        super().__init__(**data)
        # 创建必要的目录
        self._create_directories()
    
    def _create_directories(self):
        """创建必要的目录"""
        self.image.download_dir.mkdir(parents=True, exist_ok=True)
        self.image.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log.log_dir.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 论坛预设配置
# ============================================================================

class ForumPresets:
    """论坛预设配置"""
    
    @staticmethod
    def discuz() -> Config:
        """Discuz论坛通用配置"""
        return Config(
            bbs={
                "name": "Discuz",
                "forum_type": "discuz",
                "thread_list_selector": "tbody[id^='normalthread'], tbody[id^='stickthread']",
                "thread_link_selector": "a.s.xst, a.xst",
                "image_selector": "img.zoom,img[file],img[aid],div.pattl img,div.pcb img",
                "next_page_selector": "a.nxt, div.pg a.nxt",
            },
            crawler={
                "max_concurrent_requests": 3,
                "download_delay": 2.0,
            },
            image={
                "min_width": 300,
                "min_height": 300,
                "min_size": 30000,
            }
        )
    
    @staticmethod
    def phpbb() -> Config:
        """phpBB论坛通用配置"""
        return Config(
            bbs={
                "name": "phpBB",
                "forum_type": "phpbb",
                "thread_list_selector": "li.row",
                "thread_link_selector": "a.topictitle",
                "image_selector": "dl.attachbox img, div.content img",
                "next_page_selector": "a.next",
            }
        )
    
    @staticmethod
    def vbulletin() -> Config:
        """vBulletin论坛通用配置"""
        return Config(
            bbs={
                "name": "vBulletin",
                "forum_type": "vbulletin",
                "thread_list_selector": "li.threadbit",
                "thread_link_selector": "a.title",
                "image_selector": "div.content img, img.attachment",
                "next_page_selector": "a[rel='next']",
            }
        )
    
    @staticmethod
    def xindong() -> Config:
        """心动论坛（Discuz）专用配置"""
        config = ForumPresets.discuz()
        config.bbs.name = "心动论坛"
        config.bbs.base_url = "https://bbs.xd.com"
        config.bbs.login_url = "https://bbs.xd.com/member.php?mod=logging&action=login"
        return config


# 心动论坛板块配置
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


# 示例帖子
EXAMPLE_THREADS = [
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1",
]


# ============================================================================
# 配置加载器
# ============================================================================

class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load(preset: str = "default") -> Config:
        """
        加载配置
        
        Args:
            preset: 预设名称 (default/discuz/phpbb/vbulletin/xindong)
        
        Returns:
            Config实例
        """
        preset = preset.lower()
        
        if preset == "discuz":
            return ForumPresets.discuz()
        elif preset == "phpbb":
            return ForumPresets.phpbb()
        elif preset == "vbulletin":
            return ForumPresets.vbulletin()
        elif preset == "xindong":
            return ForumPresets.xindong()
        else:
            return load_config_from_env()
    
    @staticmethod
    def auto_detect(url: str) -> Config:
        """
        自动检测论坛配置
        
        Args:
            url: 论坛URL
        
        Returns:
            自动检测的Config实例
        """
        from loguru import logger
        from urllib.parse import urlparse
        
        logger.info(f"🔍 自动检测论坛配置: {url}")
        
        try:
            from core.selector_detector import SelectorDetector
            
            detector = SelectorDetector(url)
            asyncio.run(detector.detect_all())
            
            # 提取基础URL
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # 根据检测结果创建配置
            config = Config(
                bbs={
                    "name": f"Auto-{detector.forum_type}",
                    "forum_type": detector.forum_type,
                    "base_url": base_url,
                    "thread_list_selector": detector.detected_selectors.get('thread_list_selector', ''),
                    "thread_link_selector": detector.detected_selectors.get('thread_link_selector', ''),
                    "image_selector": detector.detected_selectors.get('image_selector', ''),
                    "next_page_selector": detector.detected_selectors.get('next_page_selector', ''),
                }
            )
            
            confidence = detector.get_confidence()
            if confidence >= 70:
                logger.success(f"✅ 自动检测成功！置信度: {confidence:.1f}%")
            else:
                logger.warning(f"⚠️  置信度较低: {confidence:.1f}%，建议手动调整配置")
            
            return config
            
        except Exception as e:
            logger.error(f"❌ 自动检测失败: {e}")
            logger.info("→ 使用默认配置")
            return Config()


# 从环境变量加载配置
def load_config_from_env() -> Config:
    """从环境变量加载配置"""
    config_data = {
        "bbs": {
            "base_url": os.getenv("BBS_BASE_URL", ""),
            "login_required": os.getenv("BBS_LOGIN_REQUIRED", "false").lower() == "true",
            "username": os.getenv("BBS_USERNAME"),
            "password": os.getenv("BBS_PASSWORD"),
        },
        "crawler": {
            "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "5")),
            "download_delay": float(os.getenv("DOWNLOAD_DELAY", "1.0")),
            "use_proxy": os.getenv("USE_PROXY", "false").lower() == "true",
        },
        "database": {
            "mongodb_uri": os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
            "redis_host": os.getenv("REDIS_HOST", "localhost"),
        },
        "log": {
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        }
    }
    return Config(**config_data)


# 全局配置实例（默认从环境变量加载）
config = load_config_from_env()
