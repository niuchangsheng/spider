"""
爬虫模块

包含各种爬虫类：
- BaseSpider: 爬虫基类
- BBSSpider: BBS论坛爬虫基类
- DiscuzSpider: Discuz论坛爬虫
- PhpBBSpider: phpBB论坛爬虫
- VBulletinSpider: vBulletin论坛爬虫
- DynamicNewsCrawler: 动态页面爬虫
- SpiderFactory: 爬虫工厂
"""
from spiders.base import BaseSpider
from spiders.bbs_spider import BBSSpider, DiscuzSpider, PhpBBSpider, VBulletinSpider
from spiders.dynamic_crawler import DynamicNewsCrawler
from spiders.spider_factory import SpiderFactory

__all__ = [
    'BaseSpider',
    'BBSSpider',
    'DiscuzSpider',
    'PhpBBSpider',
    'VBulletinSpider',
    'DynamicNewsCrawler',
    'SpiderFactory',
]
