# 设计文档：爬虫架构重构 - 统一继承体系

**文档编号**: DESIGN-2026-02-06-001  
**创建日期**: 2026-02-06  
**作者**: Chang (架构师)  
**状态**: ✅ 已实现

---

## 1. 背景与问题

### 1.1 当前架构问题

在实现动态新闻页面爬虫（`DynamicNewsCrawler`）后，发现当前架构存在以下问题：

```
┌─────────────────────────────────────────────────────────────────┐
│                        当前类关系图                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Parser 层:                                                     │
│  ┌──────────────┐                                               │
│  │  BBSParser   │ ◄─── DynamicPageParser (继承)                 │
│  └──────────────┘      ❌ 语义不对！Dynamic不是一种BBS          │
│                                                                 │
│  Crawler 层:                                                    │
│  ┌──────────────┐                                               │
│  │  BBSSpider   │ ◄─── DiscuzSpider (继承)                      │
│  └──────────────┘ ◄─── PhpBBSpider (继承)                       │
│                   ◄─── VBulletinSpider (继承)                   │
│                                                                 │
│  ┌────────────────────┐                                         │
│  │ DynamicNewsCrawler │  ❌ 独立存在，未纳入继承体系            │
│  └────────────────────┘                                         │
│                                                                 │
│  Factory 层:                                                    │
│  ┌────────────────┐                                             │
│  │ SpiderFactory  │ ─── 只管理 BBSSpider 及其子类               │
│  │  _registry:    │     ❌ 不管理 DynamicNewsCrawler            │
│  │  - discuz      │ → DiscuzSpider                              │
│  │  - phpbb       │ → PhpBBSpider                               │
│  │  - vbulletin   │ → VBulletinSpider                           │
│  │  - generic     │ → BBSSpider  ❌ 与子类并列，层级混乱        │
│  └────────────────┘                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| 问题 | 描述 | 影响 |
|------|------|------|
| **Parser继承语义错误** | `DynamicPageParser` 继承 `BBSParser`，但动态页面不是BBS | 概念混淆 |
| **缺少Parser基类** | `BBSParser` 和 `DynamicPageParser` 应该共享基类 | 代码重复 |
| **Crawler继承不一致** | `DynamicNewsCrawler` 不继承 `BBSSpider` | 代码结构混乱 |
| **工厂模式不完整** | `SpiderFactory` 只管理 BBS 爬虫 | 无法统一创建爬虫 |
| **代码重复** | `DynamicNewsCrawler` 有独立的 `fetch_page`、`stats`、`session` | 维护成本高 |
| **Factory层级混乱** | `generic→BBSSpider` 与 `discuz→DiscuzSpider` 并列，但实际是父子关系 | 难以理解 |

### 1.2 重复代码分析

| 功能 | BBSSpider | DynamicNewsCrawler | 重复？ |
|------|-----------|-------------------|--------|
| HTTP Session 管理 | ✅ `self.session` | ✅ `self.session` | 🔴 重复 |
| 页面获取 | ✅ `fetch_page()` | ✅ `fetch_page()` | 🔴 重复 |
| 统计信息 | ✅ `self.stats` | ✅ `self.stats` | 🔴 重复 |
| 异步上下文 | ✅ `__aenter__/__aexit__` | ✅ `__aenter__/__aexit__` | 🔴 重复 |
| 请求头管理 | ✅ `get_headers()` | ✅ `get_headers()` | 🔴 重复 |
| 配置管理 | ✅ `self.config` | ✅ `self.config` | 🔴 重复 |

---

## 2. 设计目标

1. **统一继承体系** - 所有爬虫类共享基类
2. **消除代码重复** - 公共功能抽取到基类
3. **工厂模式完整** - `SpiderFactory` 管理所有爬虫类型
4. **易于扩展** - 新增爬虫类型只需继承和注册
5. **向后兼容** - 现有 API 保持不变

---

## 3. 架构设计

### 3.1 推荐架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        推荐类关系图                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Parser 层 (重构):                                              │
│  ┌──────────────────┐                                           │
│  │   BaseParser     │  ◄── 新增！抽取公共解析功能               │
│  │  - config        │      (HTML解析、URL处理、图片提取)        │
│  │  - parse_images()│                                           │
│  │  - extract_id()  │                                           │
│  └────────┬─────────┘                                           │
│           │                                                     │
│    ┌──────┴──────────────────┐                                  │
│    ▼                         ▼                                  │
│  ┌──────────────┐    ┌────────────────────┐                     │
│  │  BBSParser   │    │ DynamicPageParser  │                     │
│  │  (论坛解析)   │    │ (动态页面解析)      │                     │
│  │  - thread_*  │    │ - article_*        │                     │
│  └──────────────┘    └────────────────────┘                     │
│                                                                 │
│  Crawler 层 (重构):                                             │
│  ┌──────────────────┐                                           │
│  │   BaseSpider     │  ◄── 新增！抽取公共功能                   │
│  │  - config        │      (HTTP请求、统计、session管理)        │
│  │  - session       │                                           │
│  │  - stats         │                                           │
│  │  - fetch_page()  │                                           │
│  │  - get_headers() │                                           │
│  │  - __aenter__()  │                                           │
│  │  - __aexit__()   │                                           │
│  └────────┬─────────┘                                           │
│           │                                                     │
│    ┌──────┴──────────────────┐                                  │
│    ▼                         ▼                                  │
│  ┌──────────────┐    ┌────────────────────┐                     │
│  │  BBSSpider   │    │ DynamicNewsCrawler │                     │
│  │  (论坛爬虫)   │    │ (动态页面爬虫)      │                     │
│  │  - parser    │    │ - parser           │                     │
│  │  - crawl_*   │    │ - crawl_*          │                     │
│  └──────┬───────┘    └────────────────────┘                     │
│         │                                                       │
│  ┌──────┼──────────────┐                                        │
│  ▼      ▼              ▼                                        │
│ Discuz PhpBB      VBulletin                                     │
│ Spider Spider      Spider                                       │
│                                                                 │
│  Factory 层 (扩展):                                             │
│  ┌────────────────────────────────────────────────────┐         │
│  │ SpiderFactory  ─── 统一管理所有爬虫类型             │         │
│  │                                                    │         │
│  │  _registry (类型 → 类):                            │         │
│  │  ┌─────────────────────────────────────────────┐  │         │
│  │  │ BBS类型:                                     │  │         │
│  │  │   'generic'   → BBSSpider (通用BBS)         │  │         │
│  │  │   'discuz'    → DiscuzSpider (继承BBSSpider)│  │         │
│  │  │   'phpbb'     → PhpBBSpider (继承BBSSpider) │  │         │
│  │  │   'vbulletin' → VBulletinSpider (继承BBS)   │  │         │
│  │  ├─────────────────────────────────────────────┤  │         │
│  │  │ 动态页面类型:                                │  │         │
│  │  │   'dynamic'   → DynamicNewsCrawler  🆕      │  │         │
│  │  └─────────────────────────────────────────────┘  │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 继承关系说明

```
继承层级图:

BaseParser (抽象基类)
├── BBSParser (论坛解析器)
└── DynamicPageParser (动态页面解析器)

BaseSpider (抽象基类)
├── BBSSpider (通用BBS爬虫)
│   ├── DiscuzSpider (Discuz专用)
│   ├── PhpBBSpider (phpBB专用)
│   └── VBulletinSpider (vBulletin专用)
└── DynamicNewsCrawler (动态页面爬虫)

注意:
- BBSSpider 是 DiscuzSpider 等的父类，不是并列关系
- 'generic' 类型使用 BBSSpider，适用于未知论坛类型
- 'discuz' 等类型使用专用子类，有特定处理逻辑
```

### 3.3 类设计

#### 3.3.1 BaseParser (新增)

```python
class BaseParser(ABC):
    """
    解析器基类
    
    所有解析器的公共基类，提供：
    - 基础HTML解析
    - URL处理
    - 图片提取
    - ID提取
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
    
    def _extract_id(self, url: str, patterns: List[str]) -> str:
        """
        从URL中提取ID
        
        Args:
            url: 页面URL
            patterns: 正则表达式列表
        
        Returns:
            提取的ID，失败返回MD5哈希
        """
        import re
        import hashlib
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 回退：使用URL的MD5
        return hashlib.md5(url.encode()).hexdigest()[:16]
    
    def _extract_images(self, soup: BeautifulSoup, selectors: List[str], base_url: str) -> List[str]:
        """
        从HTML中提取图片URL
        
        Args:
            soup: BeautifulSoup对象
            selectors: CSS选择器列表
            base_url: 基础URL（用于处理相对路径）
        
        Returns:
            图片URL列表
        """
        images = []
        for selector in selectors:
            for img in soup.select(selector):
                src = self._get_image_url(img)
                if src:
                    if not src.startswith('http'):
                        src = urljoin(base_url, src)
                    if src not in images:
                        images.append(src)
        return images
    
    def _get_image_url(self, img_tag) -> Optional[str]:
        """
        从img标签获取最佳图片URL
        
        优先级: srcset(最大) > data-src > src
        """
        # 子类可重写此方法
        return img_tag.get('src')
    
    @abstractmethod
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        """解析页面（子类实现）"""
        pass
```

#### 3.3.2 BBSParser (修改)

```python
class BBSParser(BaseParser):
    """
    BBS论坛解析器
    
    继承 BaseParser，添加论坛特有功能：
    - 帖子列表解析
    - 帖子详情解析
    - 分页检测
    """
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        # 使用全局config或传入的config
        self.bbs_config = (config or global_config).bbs
    
    def parse_thread_list(self, html: str, base_url: str) -> List[Dict]:
        """解析帖子列表"""
        # 使用基类的 _extract_images 等方法
        ...
    
    def parse_thread_page(self, html: str, thread_url: str) -> Dict:
        """解析帖子详情页"""
        ...
    
    def _extract_thread_id(self, url: str) -> str:
        """提取帖子ID"""
        patterns = [
            r'tid[=_](\d+)',
            r'thread[/-](\d+)',
            r'/(\d+)\.html?$',
        ]
        return self._extract_id(url, patterns)
```

#### 3.3.3 DynamicPageParser (修改)

```python
class DynamicPageParser(BaseParser):
    """
    动态页面解析器
    
    继承 BaseParser，添加动态页面特有功能：
    - 文章列表解析
    - 文章详情解析
    - Ajax分页检测
    - 原图URL提取
    """
    
    def __init__(self, config: Config):
        super().__init__(config)
        # 动态页面特有配置
        self.article_selector = getattr(config.bbs, 'article_selector', '.article')
    
    def parse_articles(self, html: str) -> List[Dict]:
        """解析文章列表"""
        ...
    
    async def parse_article_detail(self, url: str, html: str) -> Dict:
        """解析文章详情页"""
        ...
    
    def _get_image_url(self, img_tag) -> Optional[str]:
        """
        重写：获取原图URL
        
        优先级: srcset(最大尺寸) > data-src > src(去除尺寸后缀)
        """
        # 方法1: srcset
        srcset = img_tag.get('srcset', '')
        if srcset:
            max_url = self._parse_srcset_max(srcset)
            if max_url:
                return max_url
        
        # 方法2: data-src
        if img_tag.get('data-src'):
            return img_tag['data-src']
        
        # 方法3: src (去除尺寸后缀)
        src = img_tag.get('src', '')
        return re.sub(r'-\d+x\d+(\.[a-zA-Z]+)$', r'\1', src) if src else None
    
    def _extract_article_id(self, url: str) -> str:
        """提取文章ID"""
        patterns = [
            r'/(\d+)/?$',
            r'id[=_](\d+)',
            r'article[/-](\d+)',
        ]
        return self._extract_id(url, patterns)
```

#### 3.3.4 BaseSpider (新增)

```python
class BaseSpider(ABC):
    """
    爬虫基类
    
    所有爬虫的公共基类，提供：
    - HTTP Session 管理
    - 页面获取
    - 统计信息
    - 异步上下文管理
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'pages_fetched': 0,
            'requests_failed': 0,
        }
    
    async def __aenter__(self) -> 'BaseSpider':
        """异步上下文管理器入口"""
        await self.init()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def init(self):
        """初始化爬虫（创建session等）"""
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """关闭爬虫（清理资源）"""
        if self.session:
            await self.session.close()
    
    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "User-Agent": self.config.crawler.user_agent or UserAgent().random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    async def fetch_page(self, url: str, headers: Optional[Dict] = None) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 页面URL
            headers: 可选的额外请求头
        
        Returns:
            HTML内容，失败返回None
        """
        try:
            request_headers = self.get_headers()
            if headers:
                request_headers.update(headers)
            
            async with self.session.get(url, headers=request_headers) as response:
                if response.status == 200:
                    self.stats['pages_fetched'] += 1
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status}: {url}")
                    return None
        except Exception as e:
            self.stats['requests_failed'] += 1
            logger.error(f"获取页面失败 {url}: {e}")
            return None
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息（子类实现）"""
        pass
```

#### 3.3.5 BBSSpider (修改)

```python
class BBSSpider(BaseSpider):
    """
    BBS论坛爬虫
    
    继承 BaseSpider，添加论坛特有功能：
    - 帖子列表解析
    - 帖子详情爬取
    - 图片下载
    """
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.parser = BBSParser()
        self.downloader = None
        self.deduplicator = None
        self.storage = None
        
        # BBS特有统计
        self.stats.update({
            'threads_crawled': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_failed': 0,
            'duplicates_skipped': 0,
        })
    
    async def init(self):
        """初始化BBS爬虫"""
        await super().init()  # 调用基类初始化
        # BBS特有初始化
        self.downloader = ImageDownloader(...)
        self.deduplicator = ImageDeduplicator(...)
        self.storage = Storage(...)
    
    async def close(self):
        """关闭BBS爬虫"""
        # BBS特有清理
        if self.downloader:
            await self.downloader.close()
        await super().close()  # 调用基类关闭
    
    # ... 其他BBS特有方法
```

#### 3.3.6 DynamicNewsCrawler (修改)

```python
class DynamicNewsCrawler(BaseSpider):
    """
    动态新闻页面爬虫
    
    继承 BaseSpider，添加动态页面特有功能：
    - Ajax分页处理
    - 文章详情爬取
    - 图片提取
    """
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.parser = DynamicPageParser(config)
        
        # 动态页面特有统计
        self.stats.update({
            'articles_found': 0,
            'articles_crawled': 0,
            'articles_failed': 0,
            'images_downloaded': 0,
            'images_failed': 0,
        })
    
    async def fetch_page(self, url: str, headers: Optional[Dict] = None, is_ajax: bool = False) -> Optional[str]:
        """
        重写 fetch_page，支持 Ajax 请求
        """
        request_headers = headers or {}
        if is_ajax:
            request_headers["X-Requested-With"] = "XMLHttpRequest"
        return await super().fetch_page(url, request_headers)
    
    # ... 其他动态页面特有方法
```

#### 3.3.7 SpiderFactory (扩展)

```python
class SpiderFactory:
    """
    爬虫工厂类
    
    统一管理所有爬虫类型的创建
    """
    
    _registry: Dict[str, Type[BaseSpider]] = {
        # BBS类型
        'discuz': DiscuzSpider,
        'phpbb': PhpBBSpider,
        'vbulletin': VBulletinSpider,
        'generic': BBSSpider,
        # 动态页面类型
        'dynamic': DynamicNewsCrawler,  # 🆕 新增
    }
    
    @classmethod
    def create(cls, 
               config: Optional[Config] = None, 
               url: Optional[str] = None, 
               preset: Optional[str] = None,
               spider_type: Optional[str] = None  # 🆕 新增参数
    ) -> BaseSpider:
        """
        创建爬虫实例
        
        Args:
            config: 配置对象
            url: 论坛URL（用于自动检测）
            preset: 论坛类型预设
            spider_type: 爬虫类型 (bbs/dynamic)
        
        Returns:
            爬虫实例
        """
        # 确定爬虫类型
        if spider_type == 'dynamic':
            return DynamicNewsCrawler(config or Config())
        
        # 原有BBS逻辑...
```

### 3.3 CLI 更新

```bash
# 现有命令（保持不变）
spider.py crawl-url "https://bbs.com/thread/123" --auto-detect
spider.py crawl-urls --config xindong
spider.py crawl-board "https://bbs.com/forum/1" --config xindong
spider.py crawl-boards --config xindong

# 动态页面命令（已实现）
spider.py crawl-news "https://sxd.xd.com/" --download-images --max-pages 5
```

---

## 4. 实现计划

### 4.1 阶段划分

| 阶段 | 内容 | 预计时间 | 风险 |
|------|------|---------|------|
| **阶段1** | 创建 `BaseParser` 基类 | 30分钟 | 低 |
| **阶段2** | 修改 `BBSParser` 继承 `BaseParser` | 30分钟 | 中 |
| **阶段3** | 修改 `DynamicPageParser` 继承 `BaseParser` | 30分钟 | 中 |
| **阶段4** | 创建 `BaseSpider` 基类 | 30分钟 | 低 |
| **阶段5** | 修改 `BBSSpider` 继承 `BaseSpider` | 30分钟 | 中 |
| **阶段6** | 修改 `DynamicNewsCrawler` 继承 `BaseSpider` | 30分钟 | 中 |
| **阶段7** | 扩展 `SpiderFactory` | 15分钟 | 低 |
| **阶段8** | 更新文档和测试 | 30分钟 | 低 |

### 4.2 文件变更

| 文件 | 变更类型 | 内容 | 状态 |
|------|---------|------|------|
| `core/parser.py` | 修改 | 添加 `BaseParser`，修改 `BBSParser` 继承 | ✅ 完成 |
| `core/dynamic_parser.py` | 修改 | 继承 `BaseParser`，删除重复代码 | ✅ 完成 |
| `spider.py` | 修改 | 添加 `BaseSpider`，修改 `BBSSpider` 继承 | ✅ 完成 |
| `core/dynamic_crawler.py` | 修改 | 与 `BaseSpider` 接口一致 | ✅ 完成 |
| `ARCHITECTURE.md` | 修改 | 更新架构图 | ✅ 完成 |
| `README.md` | 修改 | 添加动态页面爬虫文档 | ✅ 完成 |
| `run_spider.sh` | 修改 | 添加 `crawl-news` 示例 | ✅ 完成 |

### 4.3 向后兼容

| API | 兼容性 | 说明 |
|-----|--------|------|
| `SpiderFactory.create()` | ✅ 完全兼容 | 现有参数保持不变 |
| `BBSSpider` | ✅ 完全兼容 | 公共接口不变 |
| `DynamicNewsCrawler` | ✅ 完全兼容 | 公共接口不变 |
| CLI 命令 | ✅ 完全兼容 | 现有命令保持不变 |

---

## 5. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| 继承链过深 | 低 | 中 | 只有2层继承 |
| 接口不兼容 | 中 | 高 | 充分测试，保持公共接口 |
| 性能下降 | 低 | 低 | 基类方法简单，无性能影响 |

---

## 6. 测试计划

### 6.1 单元测试

```python
# 测试 BaseSpider
def test_base_spider_init():
    spider = ConcreteSpider(config)
    assert spider.session is None
    
async def test_base_spider_fetch_page():
    async with ConcreteSpider(config) as spider:
        html = await spider.fetch_page("https://example.com")
        assert html is not None
```

### 6.2 集成测试

```bash
# 测试 BBS 爬虫
python spider.py crawl-url "https://bbs.xd.com/..." --config xindong

# 测试动态页面爬虫
python spider.py crawl-news "https://sxd.xd.com/" --download-images --max-pages 2
```

---

## 7. 审批

| 角色 | 姓名 | 意见 | 日期 |
|------|------|------|------|
| 架构师 | Chang | ✅ 已批准 | 2026-02-06 |
| 开发者 | AI Assistant | ✅ 已实现 | 2026-02-06 |

---

## 8. 附录

### 8.1 参考资料

- [Python ABC 模块文档](https://docs.python.org/3/library/abc.html)
- [设计模式：模板方法模式](https://refactoring.guru/design-patterns/template-method)

### 8.2 相关设计文档

- `docs/designs/2026-02-05-dynamic-news-page-crawler.md` - 动态新闻页面爬虫设计
- `docs/designs/2026-02-04-implement-subcommand-mode.md` - 子命令模式实现
