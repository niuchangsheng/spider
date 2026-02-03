# 快速开始指南 - BBS图片爬虫

## 📌 最快5分钟开始使用

### 第1步：安装依赖（2分钟）

```bash
pip install -r requirements.txt
```

**最小依赖**（如果完整安装失败，可以只安装这些）：
```bash
pip install requests aiohttp beautifulsoup4 lxml Pillow loguru fake-useragent tenacity tqdm aiofiles pydantic python-dotenv imagehash
```

### 第2步：配置选择器（2分钟）

1. 打开目标BBS论坛网页
2. 按 `F12` 打开浏览器开发者工具
3. 按 `Ctrl+Shift+C` 进入元素选择模式
4. 点击一个帖子标题，查看HTML结构

例如，如果帖子的HTML是：
```html
<div class="thread-item">
    <a class="thread-title" href="/t/12345">帖子标题</a>
</div>
```

那么在 `config.py` 中配置：
```python
thread_list_selector = "div.thread-item"
thread_link_selector = "a.thread-title"
```

对于图片，找到帖子内图片的HTML结构：
```html
<img class="post-img" src="https://example.com/image.jpg">
```

配置为：
```python
image_selector = "img.post-img"
```

### 第3步：修改爬取目标（1分钟）

编辑 `bbs_spider.py` 的 `main()` 函数，修改为你的目标URL：

```python
async def main():
    async with BBSSpider() as spider:
        # 爬取单个帖子
        await spider.crawl_thread({
            'url': "https://你的论坛.com/thread/12345",
            'thread_id': "12345",
            'board': '板块名'
        })
```

### 第4步：运行（立即）

```bash
python bbs_spider.py
```

图片会保存到 `downloads/板块名/帖子ID/` 目录。

---

## 🎯 常见BBS论坛配置

### Discuz论坛

```python
# config.py
class BBSConfig(BaseModel):
    thread_list_selector = "tbody[id^='normalthread']"
    thread_link_selector = "a.s.xst"
    image_selector = "img.zoom, img[file]"
    next_page_selector = "a.nxt"
```

### 通用论坛（尝试这些）

```python
# 帖子列表常见选择器
thread_list_selector = "div.thread, li.thread, tr.thread, div.topic"
thread_link_selector = "a.title, a.thread-title, a.topic-title"

# 图片常见选择器
image_selector = "img[src*='jpg'], img[src*='png'], div.content img"

# 下一页常见选择器
next_page_selector = "a.next, a.next-page, a[rel='next']"
```

---

## ⚙️ 可选配置

### 不使用数据库（推荐新手）

数据库是**可选的**，不配置也能正常使用，只是不会记录元数据。

如果不想安装MongoDB和Redis，可以修改代码：

在 `bbs_spider.py` 中注释掉这些行：
```python
# storage.connect()  # 注释这行
# storage.save_thread(thread_data)  # 注释这行
# storage.save_image_record(result)  # 注释这行
```

### 调整下载参数

```python
# config.py
class CrawlerConfig(BaseModel):
    max_concurrent_requests = 3  # 并发数（建议3-5）
    download_delay = 2.0  # 延迟秒数（建议1-3秒）
```

### 图片过滤

```python
# config.py
class ImageConfig(BaseModel):
    min_width = 500  # 只下载宽度>=500px的图片
    min_height = 500  # 只下载高度>=500px的图片
    min_size = 50000  # 只下载>=50KB的图片
```

---

## 🐛 常见问题

### Q: 提示找不到模块？
A: 运行 `pip install -r requirements.txt`

### Q: 没有下载到图片？
A: 检查 `image_selector` 是否正确，使用浏览器F12查看图片的HTML结构

### Q: 报错 MongoDB连接失败？
A: 数据库是可选的，可以注释掉相关代码（见上文）

### Q: 下载速度很慢？
A: 增加并发数 `max_concurrent_requests = 10`，减少延迟 `download_delay = 0.5`

### Q: 被封IP了？
A: 减少并发数，增加延迟时间，或配置代理

### Q: 选择器不知道怎么写？
A: 看 `examples/custom_selectors.py` 中的例子，或使用浏览器的 Copy Selector 功能

---

## 📞 获取帮助

1. 查看 `README.md` 获取详细文档
2. 查看 `examples/` 目录的示例代码
3. 在项目中创建 Issue

---

## 🎉 恭喜！

你已经完成配置，现在可以开始爬取图片了！

**下一步建议：**
- 先爬取1-2个帖子测试
- 确认图片正确下载后，再批量爬取
- 查看 `downloads/` 目录中的图片
- 阅读 `README.md` 了解高级功能
