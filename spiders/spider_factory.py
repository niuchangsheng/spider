"""
爬虫工厂模块

提供统一的爬虫创建接口
"""
from typing import Dict, Type, Optional
from loguru import logger

from config import Config, ConfigLoader


class SpiderFactory:
    """
    爬虫工厂类
    
    统一管理所有爬虫类型的创建：
    - BBS类型: generic, discuz, phpbb, vbulletin
    - 动态页面类型: dynamic
    
    继承关系:
    - BaseSpider (抽象基类)
      ├── BBSSpider (通用BBS爬虫)
      │   ├── DiscuzSpider
      │   ├── PhpBBSpider
      │   └── VBulletinSpider
      └── DynamicNewsCrawler (动态页面爬虫)
    """
    
    # 延迟初始化注册表（避免循环导入）
    _bbs_registry = None
    _registry = None  # 兼容别名
    
    @classmethod
    def _init_registry(cls):
        """延迟初始化注册表"""
        if cls._bbs_registry is None:
            from spiders.bbs_spider import BBSSpider, DiscuzSpider, PhpBBSpider, VBulletinSpider
            cls._bbs_registry = {
                'generic': BBSSpider,
                'discuz': DiscuzSpider,
                'phpbb': PhpBBSpider,
                'vbulletin': VBulletinSpider,
            }
            cls._registry = cls._bbs_registry
    
    @classmethod
    def register(cls, forum_type: str, spider_class):
        """
        注册新的BBS爬虫类型
        
        Args:
            forum_type: 论坛类型标识
            spider_class: 爬虫类（必须继承 BBSSpider）
        
        Examples:
            SpiderFactory.register('mybb', MyBBSpider)
        """
        cls._init_registry()
        cls._bbs_registry[forum_type] = spider_class
        logger.info(f"✅ 注册爬虫类型: {forum_type} -> {spider_class.__name__}")
    
    @classmethod
    def create(
        cls, 
        config: Optional[Config] = None, 
        url: Optional[str] = None, 
        preset: Optional[str] = None,
        spider_type: str = 'bbs'
    ):
        """
        创建爬虫实例（工厂方法）
        
        Args:
            config: 配置对象（优先级最高）
            url: 论坛URL，自动检测配置
            preset: 论坛类型预设 (discuz/phpbb/vbulletin)
            spider_type: 爬虫类型 ('bbs' 或 'dynamic')
        
        Returns:
            爬虫实例:
            - spider_type='bbs': BBSSpider 或其子类
            - spider_type='dynamic': DynamicNewsCrawler
        
        Examples:
            # ✅ 方式1: 使用配置文件（推荐）
            from config import get_example_config
            config = get_example_config("xindong")
            spider = SpiderFactory.create(config=config)
            
            # ✅ 方式2: 使用论坛类型预设
            spider = SpiderFactory.create(preset="discuz")
            
            # ✅ 方式3: 自动检测论坛类型
            spider = SpiderFactory.create(url="https://forum.com/board")
            
            # ✅ 方式4: 创建动态页面爬虫
            spider = SpiderFactory.create(config=config, spider_type='dynamic')
        """
        cls._init_registry()
        
        # 先获取配置
        if config:
            final_config = config
        elif preset:
            final_config = ConfigLoader.load(preset)
        elif url:
            final_config = ConfigLoader.auto_detect(url)
        else:
            raise ValueError("必须提供 config、preset 或 url 参数之一")
        
        # 根据 spider_type 选择爬虫类型
        if spider_type == 'dynamic':
            from spiders.dynamic_news_spider import DynamicNewsCrawler
            logger.info(f"🏭 创建爬虫: DynamicNewsCrawler")
            return DynamicNewsCrawler(config=final_config)
        
        # BBS爬虫：根据 forum_type 选择具体子类
        from spiders.bbs_spider import BBSSpider
        forum_type = final_config.bbs.forum_type.lower()
        spider_class = cls._bbs_registry.get(forum_type, BBSSpider)
        
        logger.info(f"🏭 创建爬虫: {spider_class.__name__}")
        
        return spider_class(config=final_config)
    
    @classmethod
    def create_dynamic(cls, config: Config):
        """
        创建动态页面爬虫（便捷方法）
        
        Args:
            config: 配置对象
        
        Returns:
            DynamicNewsCrawler 实例
        """
        return cls.create(config=config, spider_type='dynamic')
