# BBS图片爬虫项目

一个功能完善的BBS论坛图片爬虫系统，支持自动化爬取、图片去重、数据存储等功能。

## 📚 文档导航

### 🏗️ 架构与开发
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - 系统架构设计文档（必读）
- **[DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)** - 开发流程规范（⚠️ 强制执行）
- **[TEAM_ROLES.md](TEAM_ROLES.md)** - 团队角色定义
- **[SKILLS.md](SKILLS.md)** - 技术栈与技能清单

### 📖 使用指南
- **[QUICKSTART.md](QUICKSTART.md)** - 快速入门指南
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - 环境配置指南
- **[XINDONG_README.md](XINDONG_README.md)** - 心动论坛专用说明

### ⚠️ 重要提示
> **所有代码变更必须遵循严格流程**：  
> 1️⃣ 先更新设计文档 → 2️⃣ 设计评审 → 3️⃣ 编写代码 → 4️⃣ 代码审查 → 5️⃣ 测试验证  
> 详见 [开发流程规范](DEVELOPMENT_PROCESS.md)

---

## ✨ 核心特性

### 🎯 爬取功能
- **多板块支持** - 支持爬取多个论坛板块
- **自动翻页** - 自动识别并爬取分页内容
- **图片提取** - 智能提取帖子中的所有图片
- **元数据提取** - 自动提取作者、时间、浏览数等信息

### 🛡️ 反爬虫机制
- **User-Agent轮换** - 随机切换浏览器UA
- **请求延迟** - 可配置的请求间隔
- **代理支持** - 支持代理池轮换
- **Cookie管理** - 支持登录状态保持

### 🖼️ 图片处理
- **智能过滤** - 按尺寸、大小、格式过滤图片
- **去重功能** - 基于URL和文件内容的双重去重
- **相似检测** - 使用感知哈希检测相似图片
- **格式转换** - 可选的图片压缩和格式转换
- **命名规范** - 可自定义的文件命名规则

### 💾 数据存储
- **MongoDB** - 存储帖子元数据和爬取记录
- **Redis** - 任务队列和URL去重
- **文件系统** - 本地图片存储

### 📊 监控统计
- **实时统计** - 爬取数量、成功率实时监控
- **日志记录** - 完整的日志记录和轮转
- **进度显示** - 友好的进度条显示

## 🚀 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置文件
vim .env
```

主要配置项：

```env
# BBS论坛地址
BBS_BASE_URL=https://your-bbs-site.com

# 爬虫参数
MAX_CONCURRENT_REQUESTS=5  # 并发请求数
DOWNLOAD_DELAY=1           # 请求延迟（秒）

# 数据库（可选）
MONGODB_URI=mongodb://localhost:27017/
REDIS_HOST=localhost
```

### 3. 修改爬虫代码

编辑 `bbs_spider.py` 的 `main()` 函数：

```python
async def main():
    async with BBSSpider() as spider:
        # 方式1：爬取整个板块
        await spider.crawl_board(
            board_url="https://example.com/forum/板块ID",
            board_name="图片板块",
            max_pages=10  # 爬取前10页
        )
        
        # 方式2：爬取指定帖子
        thread_urls = [
            "https://example.com/thread/12345",
            "https://example.com/thread/67890",
        ]
        await spider.crawl_threads_from_list(thread_urls)
```

### 4. 配置选择器

根据目标BBS的HTML结构，修改 `config.py` 中的选择器：

```python
class BBSConfig(BaseModel):
    # 帖子列表选择器（CSS选择器）
    thread_list_selector: str = "div.thread-item"
    thread_link_selector: str = "a.thread-link"
    
    # 图片选择器
    image_selector: str = "img.post-image, img[src*='jpg']"
    
    # 下一页选择器
    next_page_selector: str = "a.next-page"
```

### 5. 运行爬虫

```bash
python bbs_spider.py
```

## 📁 项目结构

```
spider/
├── bbs_spider.py          # 主爬虫程序
├── config.py              # 配置管理
├── requirements.txt       # 依赖列表
├── .env                   # 环境变量配置
├── core/                  # 核心模块
│   ├── __init__.py
│   ├── downloader.py      # 图片下载器
│   ├── parser.py          # 页面解析器
│   ├── storage.py         # 数据存储
│   └── deduplicator.py    # 图片去重
├── downloads/             # 图片下载目录
│   └── [板块名]/
│       └── [帖子ID]/
│           └── *.jpg
└── logs/                  # 日志目录
    └── bbs_spider.log
```

## ⚙️ 高级配置

### 图片过滤配置

在 `config.py` 中的 `ImageConfig` 类：

```python
class ImageConfig(BaseModel):
    # 图片尺寸过滤
    min_width: int = 200      # 最小宽度
    min_height: int = 200     # 最小高度
    min_size: int = 10240     # 最小文件大小（10KB）
    max_size: int = 20971520  # 最大文件大小（20MB）
    
    # 允许的格式
    allowed_formats: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]
    
    # 图片处理
    enable_deduplication: bool = True  # 启用去重
    compress_images: bool = False      # 压缩图片
    convert_to_jpg: bool = False       # 转换为JPG
    quality: int = 85                  # 压缩质量
```

### 并发控制

```python
class CrawlerConfig(BaseModel):
    max_concurrent_requests: int = 5   # 最大并发数
    download_delay: float = 1.0        # 请求延迟
    request_timeout: int = 30          # 超时时间
    max_retries: int = 3               # 最大重试次数
```

### 选择器配置示例

不同BBS论坛的HTML结构不同，需要根据实际情况调整选择器：

**示例1：Discuz论坛**
```python
thread_list_selector = "tbody[id^='normalthread']"
thread_link_selector = "a.s.xst"
image_selector = "img.zoom, img[file]"
next_page_selector = "a.nxt"
```

**示例2：phpBB论坛**
```python
thread_list_selector = "li.row"
thread_link_selector = "a.topictitle"
image_selector = "dl.attachbox img, div.content img"
next_page_selector = "a.next"
```

**示例3：自定义论坛**
```python
# 使用浏览器开发者工具（F12）查看HTML结构
# 选择合适的CSS选择器
thread_list_selector = "div.topic-item"
thread_link_selector = "h2 a"
image_selector = "div.post-content img"
next_page_selector = "a[rel='next']"
```

## 📊 数据存储

### MongoDB集合结构

**threads集合**（帖子数据）：
```json
{
    "thread_id": "12345",
    "title": "帖子标题",
    "url": "https://example.com/thread/12345",
    "board": "图片板块",
    "images": ["url1", "url2"],
    "metadata": {
        "author": "作者名",
        "post_time": "2024-01-01",
        "views": 1000,
        "replies": 50
    },
    "image_count": 10,
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-01T12:00:00"
}
```

**images集合**（图片记录）：
```json
{
    "url": "https://example.com/image.jpg",
    "save_path": "/downloads/board/thread_id/image_001.jpg",
    "file_size": 102400,
    "metadata": {
        "board": "图片板块",
        "thread_id": "12345",
        "thread_url": "https://example.com/thread/12345"
    },
    "success": true,
    "created_at": "2024-01-01T12:00:00"
}
```

## 🔧 技术栈

- **Python 3.8+**
- **aiohttp** - 异步HTTP客户端
- **BeautifulSoup4** - HTML解析
- **Pillow** - 图片处理
- **imagehash** - 图片去重
- **MongoDB** - 数据存储
- **Redis** - 任务队列
- **loguru** - 日志记录

## 📝 使用示例

### 示例1：爬取单个板块

```python
async with BBSSpider() as spider:
    await spider.crawl_board(
        board_url="https://example.com/forum/photo",
        board_name="摄影板块",
        max_pages=20
    )
```

### 示例2：爬取多个帖子

```python
thread_urls = [
    "https://example.com/thread/1",
    "https://example.com/thread/2",
    "https://example.com/thread/3",
]

async with BBSSpider() as spider:
    await spider.crawl_threads_from_list(thread_urls)
```

### 示例3：获取统计信息

```python
async with BBSSpider() as spider:
    # ... 执行爬取 ...
    
    stats = spider.get_statistics()
    print(f"爬取帖子数: {stats['threads_crawled']}")
    print(f"发现图片数: {stats['images_found']}")
    print(f"下载成功数: {stats['images_downloaded']}")
```

## ⚠️ 注意事项

1. **遵守robots.txt** - 请尊重网站的爬虫协议
2. **合理设置延迟** - 避免对服务器造成压力
3. **版权意识** - 下载的图片仅供学习研究使用
4. **登录状态** - 某些论坛需要登录，请配置用户名密码
5. **选择器适配** - 不同论坛需要调整CSS选择器
6. **数据库可选** - 不配置数据库也可运行，仅保存本地文件

## 🐛 故障排查

### 1. 无法连接数据库

```bash
# 检查MongoDB是否运行
sudo systemctl status mongodb

# 检查Redis是否运行
redis-cli ping
```

数据库是可选的，如果不需要可以注释掉相关代码。

### 2. 图片下载失败

- 检查网络连接
- 检查图片URL是否有效
- 增加重试次数和超时时间
- 检查是否需要登录

### 3. 选择器无法匹配

- 使用浏览器开发者工具检查HTML结构
- 验证CSS选择器是否正确
- 检查页面是否为动态加载（需使用Selenium/Playwright）

### 4. 内存占用过高

- 减少并发数 `MAX_CONCURRENT_REQUESTS`
- 启用图片压缩 `compress_images=True`
- 清理重复文件

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📧 联系方式

如有问题，请创建Issue。
