"""
动态新闻页面爬虫
用于爬取使用Ajax异步加载内容的新闻/公告页面
"""
import asyncio
import aiohttp
from typing import List, Dict, Optional
from loguru import logger
from pathlib import Path
from fake_useragent import UserAgent

from config import Config
from parsers.dynamic_parser import DynamicPageParser
from core.checkpoint import CheckpointManager


class DynamicNewsCrawler:
    """
    动态新闻页面爬虫
    
    与 BBSSpider 并列，继承相同的设计理念：
    - 异步上下文管理
    - 统一的统计信息接口
    - 可配置的请求头
    
    特点：
    - 支持Ajax方式快速爬取
    - 支持Selenium方式备用（可靠性高）
    - 自动处理"查看更多"分页
    - 支持批量下载文章详情和图片
    
    Example:
        config = Config(bbs={"base_url": "https://example.com"})
        crawler = DynamicNewsCrawler(config)
        
        async with crawler:
            articles = await crawler.crawl_dynamic_page_ajax(
                "https://example.com/news",
                max_pages=5
            )
    """
    
    def __init__(self, config: Config):
        """
        初始化动态新闻爬虫
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.parser = DynamicPageParser(config)
        self.session = None
        self.ua = None
        
        # 统计信息（与 BaseSpider 保持一致的结构）
        self.stats = {
            'pages_fetched': 0,       # 基础统计
            'requests_failed': 0,     # 基础统计
            'articles_found': 0,      # 发现的文章数
            'articles_crawled': 0,    # 成功爬取的文章数
            'articles_failed': 0,     # 失败的文章数
            'images_downloaded': 0,   # 下载的图片数
            'images_failed': 0,       # 失败的图片数
        }
        
        logger.info(f"🚀 初始化动态新闻爬虫: {config.bbs.name}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init(self):
        """初始化爬虫"""
        logger.info("⚙️  初始化爬虫组件...")
        
        self.ua = UserAgent()
        
        # 创建HTTP会话
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        logger.debug("✓ HTTP会话已创建")
    
    async def close(self):
        """关闭爬虫"""
        logger.info("🔒 关闭爬虫...")
        
        if self.session:
            await self.session.close()
            logger.debug("✓ HTTP会话已关闭")
        
        logger.info(f"📊 爬虫统计: {self.get_statistics()}")
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": self.ua.random if self.config.crawler.rotate_user_agent else self.ua.chrome,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }
    
    async def fetch_page(self, url: str, headers: Optional[Dict] = None, is_ajax: bool = False) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            headers: 可选的HTTP头
            is_ajax: 是否为Ajax请求（会添加X-Requested-With头）
        
        Returns:
            HTML内容，失败返回None
        """
        try:
            logger.debug(f"📄 获取页面: {url} (Ajax: {is_ajax})")
            
            # 获取基础请求头
            request_headers = self.get_headers()
            
            # 合并自定义 headers
            if headers:
                request_headers.update(headers)
            
            # Ajax请求需要特殊头
            if is_ajax:
                request_headers["X-Requested-With"] = "XMLHttpRequest"
            
            async with self.session.get(url, headers=request_headers) as response:
                if response.status == 200:
                    self.stats['pages_fetched'] += 1
                    html = await response.text()
                    await asyncio.sleep(self.config.crawler.download_delay)
                    return html
                else:
                    logger.warning(f"⚠️  HTTP {response.status}: {url}")
                    return None
        
        except asyncio.TimeoutError:
            self.stats['requests_failed'] += 1
            logger.error(f"❌ 超时: {url}")
            return None
        except Exception as e:
            self.stats['requests_failed'] += 1
            logger.error(f"❌ 获取失败 {url}: {e}")
            return None
    
    async def crawl_dynamic_page_ajax(
        self, 
        base_url: str, 
        max_pages: Optional[int] = None,
        resume: bool = True,
        start_page: Optional[int] = None
    ) -> List[Dict]:
        """
        使用Ajax方式爬取动态页面（支持断点续传）
        
        通过直接请求分页URL（如 ?page=2）来获取更多内容。
        这种方式速度快、资源占用少。
        
        Args:
            base_url: 基础URL
            max_pages: 最大页数，None表示不限制
            resume: 是否从检查点恢复（默认True）
            start_page: 起始页码（如果指定，会覆盖检查点）
        
        Returns:
            文章列表
        """
        logger.info(f"🚀 开始爬取动态页面（Ajax方式）")
        logger.info(f"   URL: {base_url}")
        logger.info(f"   最大页数: {max_pages if max_pages else '不限制'}")
        
        # 1. 创建检查点管理器
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        site = parsed.netloc or self.config.bbs.base_url
        checkpoint = CheckpointManager(site=site, board="news")
        
        # 2. 从检查点恢复
        seen_article_ids = set()
        start_page_num = 1
        min_article_id = None
        max_article_id = None
        
        if start_page is not None:
            # 手动指定起始页（覆盖检查点）
            start_page_num = start_page
            logger.info(f"📌 手动指定起始页: {start_page_num}")
            if checkpoint.exists():
                logger.info("⚠️  将覆盖现有检查点")
        elif resume and checkpoint.exists():
            # 从检查点恢复
            checkpoint_data = checkpoint.load_checkpoint()
            if checkpoint_data:
                status = checkpoint_data.get('status', 'running')
                if status == 'completed':
                    logger.info("✅ 该任务已完成爬取，跳过")
                    return []
                
                start_page_num = checkpoint_data.get('current_page', 1)
                seen_article_ids = checkpoint.get_seen_article_ids()
                min_article_id = checkpoint.get_min_article_id()
                max_article_id = checkpoint.get_max_article_id()
                
                logger.info(f"🔄 从检查点恢复: 第 {start_page_num} 页")
                logger.info(f"   已爬取文章数: {len(seen_article_ids)}")
                if min_article_id:
                    logger.info(f"   最小文章ID: {min_article_id} (已爬取的最旧文章)")
                if max_article_id:
                    logger.info(f"   最大文章ID: {max_article_id} (已爬取的最新文章)")
                logger.info(f"   策略: 跳过 {min_article_id}~{max_article_id} 之间的文章")
                logger.info(f"   策略: 爬取 > {max_article_id} 的新文章（如果网站有更新）")
                logger.info(f"   策略: 继续爬取 < {min_article_id} 的旧文章")
        
        page = start_page_num
        all_articles = []
        
        try:
            while True:
                # 构造分页URL
                if page == 1:
                    page_url = base_url
                else:
                    # 尝试多种分页URL格式
                    separator = '&' if '?' in base_url else '?'
                    page_url = f"{base_url}{separator}page={page}"
                
                logger.info(f"\n📄 爬取第 {page} 页: {page_url}")
                
                # 获取页面内容（分页请求需要Ajax头）
                html = await self.fetch_page(page_url, is_ajax=(page > 1))
                
                if not html:
                    logger.warning(f"⚠️  第{page}页获取失败，停止爬取")
                    break
                
                # 解析文章列表
                articles = self.parser.parse_articles(html)
                
                if not articles:
                    logger.info(f"✅ 第{page}页没有文章，停止爬取")
                    break
            
                # 过滤重复文章（基于 article_id 去重）
                # 策略：
                # 1. article_id > max_article_id: 新文章（网站有更新），应该爬取
                # 2. min_article_id <= article_id <= max_article_id: 中间范围（已爬取），应该跳过
                # 3. article_id < min_article_id: 更旧的文章（未爬取），应该继续爬取
                new_articles = []
                has_new_articles_beyond_max = False  # 标记是否有超过 max_article_id 的新文章
                
                for article in articles:
                    article_id = article['article_id']
                    
                    # 方式1: 通过集合去重（精确）
                    if article_id in seen_article_ids:
                        logger.debug(f"⏭️  跳过已爬取文章: {article_id} (在集合中)")
                        continue
                    
                    # 方式2: 通过最小/最大ID判断（快速，适用于倒序/正序）
                    should_skip = False
                    try:
                        article_id_int = int(article_id)
                        
                        if max_article_id and min_article_id:
                            max_id_int = int(max_article_id)
                            min_id_int = int(min_article_id)
                            
                            # 情况1: 新文章（ID > max_article_id）- 网站有更新
                            if article_id_int > max_id_int:
                                logger.info(f"🆕 发现新文章: {article_id} (>{max_article_id})，网站有更新！")
                                has_new_articles_beyond_max = True
                                # 新文章应该爬取，不跳过
                            
                            # 情况2: 中间范围（min_article_id <= ID <= max_article_id）- 已爬取，跳过
                            elif min_id_int <= article_id_int <= max_id_int:
                                logger.debug(f"⏭️  跳过中间范围文章: {article_id} ({min_article_id} <= {article_id} <= {max_article_id})")
                                seen_article_ids.add(article_id)  # 添加到集合，避免重复判断
                                should_skip = True
                            
                            # 情况3: 更旧的文章（ID < min_article_id）- 未爬取，应该继续爬取
                            # 不跳过，继续处理
                        
                        elif max_article_id:
                            # 只有 max_article_id，没有 min_article_id
                            max_id_int = int(max_article_id)
                            if article_id_int > max_id_int:
                                logger.info(f"🆕 发现新文章: {article_id} (>{max_article_id})，网站有更新！")
                                has_new_articles_beyond_max = True
                        
                        elif min_article_id:
                            # 只有 min_article_id，没有 max_article_id
                            min_id_int = int(min_article_id)
                            # 对于倒序排列，如果 ID < min_article_id，说明是更旧的文章，应该继续爬取
                            # 不跳过，继续处理
                    
                    except (ValueError, TypeError):
                        # article_id 不是数字，只能通过集合去重
                        pass
                    
                    if should_skip:
                        continue
                    
                    # 新文章，添加到列表
                    seen_article_ids.add(article_id)
                    new_articles.append(article)
                    
                    # 更新最小/最大 article_id
                    try:
                        article_id_int = int(article_id)
                        if not min_article_id or article_id_int < int(min_article_id):
                            min_article_id = article_id
                        if not max_article_id or article_id_int > int(max_article_id):
                            old_max = max_article_id
                            max_article_id = article_id
                            if old_max:
                                logger.info(f"📈 更新最大文章ID: {old_max} -> {max_article_id}")
                    except (ValueError, TypeError):
                        pass
                
                # 如果发现新文章，记录日志
                if has_new_articles_beyond_max:
                    logger.info(f"✨ 检测到网站有新文章发布，已开始爬取新内容")
                
                if not new_articles:
                    logger.info(f"✅ 第{page}页没有新文章（全部重复），停止爬取")
                    break
                
                logger.info(f"   ✓ 发现 {len(new_articles)} 篇新文章 (本页共 {len(articles)} 篇)")
                all_articles.extend(new_articles)
                self.stats['articles_found'] += len(new_articles)
                
                # 3. 保存检查点（每页保存一次）
                checkpoint.save_checkpoint(
                    current_page=page + 1,
                    last_thread_id=new_articles[-1]['article_id'] if new_articles else None,
                    last_thread_url=new_articles[-1].get('url') if new_articles else None,
                    status="running",
                    stats={
                        "articles_found": len(all_articles),
                        "articles_crawled": self.stats.get('articles_crawled', 0),
                        "images_downloaded": self.stats.get('images_downloaded', 0)
                    },
                    seen_article_ids=list(seen_article_ids),
                    min_article_id=min_article_id,
                    max_article_id=max_article_id
                )
                
                # 检查页数限制
                if max_pages and page >= max_pages:
                    logger.info(f"✅ 达到最大页数限制: {max_pages}")
                    break
                
                # 检查是否还有"查看更多"按钮 (辅助判断)
                has_more = self.parser.has_load_more_button(html)
                if not has_more:
                    logger.info("✅ 没有更多内容标识，停止爬取")
                    break
                
                page += 1
            
            # 4. 标记完成
            checkpoint.mark_completed(final_stats={
                "total_articles": len(all_articles),
                "total_images": self.stats.get('images_downloaded', 0)
            })
            
            logger.success(f"🎉 完成爬取！总共发现 {len(all_articles)} 篇新文章")
            
            return all_articles
            
        except Exception as e:
            # 发生错误时保存检查点
            logger.error(f"❌ 爬取过程中发生错误: {e}")
            checkpoint.mark_error(str(e))
            raise
    
    async def crawl_dynamic_page_selenium(
        self, 
        url: str, 
        max_clicks: Optional[int] = None
    ) -> List[Dict]:
        """
        使用Selenium方式爬取动态页面（备用方案）
        
        通过模拟浏览器点击"查看更多"按钮来加载内容。
        这种方式更可靠，但速度较慢、资源占用大。
        
        Args:
            url: 页面URL
            max_clicks: 最大点击次数，None表示不限制
        
        Returns:
            文章列表
        """
        logger.info(f"🚀 开始爬取动态页面（Selenium方式）")
        logger.info(f"   URL: {url}")
        logger.info(f"   最大点击次数: {max_clicks if max_clicks else '不限制'}")
        
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
        except ImportError:
            logger.error("❌ 缺少Selenium依赖，请安装: pip install selenium")
            return []
        
        # 配置Selenium
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = None
        
        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            logger.info("✓ 浏览器已启动")
            
            clicks = 0
            last_article_count = 0
            
            while True:
                html = driver.page_source
                current_articles = self.parser.parse_articles(html)
                current_count = len(current_articles)
                logger.debug(f"当前文章数: {current_count}")
                
                if clicks == 0:
                    last_article_count = current_count
                
                if max_clicks and clicks >= max_clicks:
                    logger.info(f"✅ 达到最大点击次数: {max_clicks}")
                    break
                
                try:
                    load_more = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((
                            By.CSS_SELECTOR, 
                            'a.more, .load-more, .btn-more'
                        ))
                    )
                    
                    if not load_more.is_displayed():
                        logger.info("⚠️  '查看更多'按钮不可见，可能已加载完毕")
                        break
                    
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", load_more)
                    await asyncio.sleep(1)
                    
                    driver.execute_script("arguments[0].click();", load_more)
                    clicks += 1
                    logger.info(f"🔄 点击'查看更多' 第{clicks}次")
                    
                    wait_time = 0
                    loaded = False
                    while wait_time < 10:
                        await asyncio.sleep(1)
                        wait_time += 1
                        
                        new_html = driver.page_source
                        new_articles = self.parser.parse_articles(new_html)
                        new_count = len(new_articles)
                        
                        if new_count > last_article_count:
                            logger.info(f"   ✓ 加载成功！新增 {new_count - last_article_count} 篇文章")
                            last_article_count = new_count
                            loaded = True
                            break
                    
                    if not loaded:
                        logger.warning(f"⚠️  等待10秒后文章数量未增加")
                        
                except TimeoutException:
                    logger.info("✅ 没有找到'查看更多'按钮，停止加载")
                    break
                except Exception as e:
                    logger.error(f"❌ 点击过程出错: {e}")
                    break
            
            html = driver.page_source
            articles = self.parser.parse_articles(html)
            self.stats['articles_found'] = len(articles)
            
            logger.success(f"🎉 完成爬取！总共发现 {len(articles)} 篇文章")
            
            return articles
            
        except Exception as e:
            logger.error(f"❌ Selenium爬取失败: {e}")
            return []
        
        finally:
            if driver:
                driver.quit()
                logger.debug("✓ 浏览器已关闭")
    
    async def crawl_article_detail(self, article: Dict) -> Optional[Dict]:
        """爬取单篇文章详情"""
        url = article.get('url')
        if not url:
            logger.warning("⚠️  文章缺少URL，跳过")
            return None
        
        logger.info(f"📝 爬取文章详情: {article.get('title', 'N/A')[:50]}")
        
        try:
            html = await self.fetch_page(url)
            
            if not html:
                logger.error(f"❌ 无法获取文章详情: {url}")
                self.stats['articles_failed'] += 1
                return None
            
            detail = self.parser.parse_article_detail(html, url)
            full_article = {**article, **detail}
            
            self.stats['articles_crawled'] += 1
            logger.success(f"   ✓ 成功，发现 {len(detail.get('images', []))} 张图片")
            
            return full_article
            
        except Exception as e:
            logger.error(f"❌ 爬取文章详情失败: {e}")
            self.stats['articles_failed'] += 1
            return None
    
    async def crawl_articles_batch(self, articles: List[Dict]) -> List[Dict]:
        """批量爬取文章详情"""
        logger.info(f"🚀 开始批量爬取 {len(articles)} 篇文章详情")
        
        tasks = [self.crawl_article_detail(article) for article in articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        full_articles = [r for r in results if r and not isinstance(r, Exception)]
        
        logger.success(f"✅ 成功爬取 {len(full_articles)}/{len(articles)} 篇文章详情")
        
        return full_articles
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.stats.copy()
