# 检查点机制详解

## 📋 当前检查点机制

### 1. 检查点记录方式

当前检查点机制**基于页码（page-based）**，适用于传统的分页网站。

#### 检查点数据结构

```json
{
  "site": "sxd.xd.com",
  "board": "all",
  "current_page": 6,              // 当前页码（关键字段）
  "last_thread_id": "article_25", // 最后爬取的文章ID（辅助信息）
  "last_thread_url": "https://...",
  "status": "running",
  "stats": {
    "crawled_count": 25,
    "images_downloaded": 50
  }
}
```

#### 保存时机

```python
# 在 spiders/bbs_spider.py 中
# 每爬取一页后保存检查点
checkpoint.save_checkpoint(
    current_page=page + 1,  # 下一页
    last_thread_id=last_thread_id,
    status="running",
    stats={...}
)
```

#### 恢复逻辑

```python
# 从检查点恢复
checkpoint_data = checkpoint.load_checkpoint()
start_page = checkpoint_data['current_page']  # 从这一页开始

# 继续爬取
for page in range(start_page, max_pages):
    # 爬取逻辑...
```

---

## ⚠️ 问题分析：sxd.xd.com 的特殊情况

### 问题场景

**sxd.xd.com 的文章排列方式**：
- **倒序排列**：第一页是最新的文章（article_id 最大）
- **示例**：
  ```
  第1页: article_id = 15503, 15502, 15501, ... (最大)
  第2页: article_id = 15470, 15469, 15468, ... (中等)
  第3页: article_id = 15450, 15449, 15448, ... (较小)
  ```

### 当前机制的问题

#### 问题1: 基于页码的检查点不适用

**当前实现**：
```python
# 检查点保存：current_page = 6
# 恢复时：从第6页开始爬取
```

**问题**：
- 如果中断在第3页，恢复时从第6页开始
- **会跳过第4、5页的内容** ❌
- 页码和 article_id 没有直接对应关系

#### 问题2: DynamicNewsCrawler 未集成检查点

**当前状态**：
- `BBSSpider.crawl_board()` ✅ 已集成检查点
- `DynamicNewsCrawler.crawl_dynamic_page_ajax()` ❌ **未集成检查点**

**影响**：
- `crawl-news` 命令不支持断点续传
- 中断后需要从头开始

---

## 🔧 解决方案

### 方案1: 基于 article_id 的检查点（推荐）⭐

**核心思路**：记录已爬取的最小 article_id，恢复时跳过已爬取的文章。

#### 改进后的检查点数据结构

```json
{
  "site": "sxd.xd.com",
  "board": "all",
  "current_page": 6,
  "min_article_id": 15450,        // 🆕 已爬取的最小 article_id
  "max_article_id": 15503,        // 🆕 已爬取的最大 article_id
  "last_thread_id": "article_15450",
  "seen_article_ids": [            // 🆕 已爬取的 article_id 集合（可选）
    "15503", "15502", "15501", ...
  ],
  "status": "running",
  "stats": {...}
}
```

#### 恢复逻辑

```python
# 加载检查点
checkpoint_data = checkpoint.load_checkpoint()
min_article_id = checkpoint_data.get('min_article_id')

# 爬取时跳过已爬取的文章
for article in articles:
    article_id = int(article['article_id'])
    
    # 如果 article_id >= min_article_id，说明已爬取
    if min_article_id and article_id >= min_article_id:
        logger.info(f"⏭️  跳过已爬取文章: {article_id}")
        continue
    
    # 爬取新文章
    await crawl_article(article)
    
    # 更新最小 article_id
    if not min_article_id or article_id < min_article_id:
        min_article_id = article_id
        checkpoint.save_checkpoint(
            min_article_id=min_article_id,
            ...
        )
```

#### 优点

- ✅ 适用于倒序排列的网站
- ✅ 不依赖页码，更可靠
- ✅ 自动跳过已爬取的文章
- ✅ 支持文章顺序变化（如新文章插入）

#### 缺点

- ⚠️ 需要 article_id 是数字且可比较
- ⚠️ 如果 article_id 不是数字，需要其他策略

---

### 方案2: 基于 URL 去重的检查点

**核心思路**：记录已爬取的 article_id 集合，恢复时通过去重机制跳过。

#### 实现方式

```python
# 在 DynamicNewsCrawler 中
seen_article_ids = set()

# 从检查点恢复
checkpoint_data = checkpoint.load_checkpoint()
if checkpoint_data:
    seen_article_ids = set(checkpoint_data.get('seen_article_ids', []))

# 爬取时去重
for article in articles:
    article_id = article['article_id']
    
    if article_id in seen_article_ids:
        logger.info(f"⏭️  跳过已爬取文章: {article_id}")
        continue
    
    # 爬取新文章
    await crawl_article(article)
    seen_article_ids.add(article_id)
    
    # 保存检查点
    checkpoint.save_checkpoint(
        seen_article_ids=list(seen_article_ids),
        ...
    )
```

#### 优点

- ✅ 适用于任何类型的 article_id（数字、字符串）
- ✅ 精确去重，不会遗漏
- ✅ 实现简单

#### 缺点

- ⚠️ 如果文章数量很大，seen_article_ids 集合会很大
- ⚠️ 检查点文件会变大

---

### 方案3: 混合方案（最佳实践）⭐

**核心思路**：结合页码和 article_id，提供双重保障。

#### 检查点数据结构

```json
{
  "site": "sxd.xd.com",
  "board": "all",
  "current_page": 6,              // 页码（用于快速定位）
  "min_article_id": 15450,        // 最小 article_id（用于精确去重）
  "last_thread_id": "article_15450",
  "crawl_direction": "desc",      // 🆕 爬取方向：desc(倒序) / asc(正序)
  "status": "running",
  "stats": {...}
}
```

#### 恢复逻辑

```python
# 加载检查点
checkpoint_data = checkpoint.load_checkpoint()
start_page = checkpoint_data.get('current_page', 1)
min_article_id = checkpoint_data.get('min_article_id')
crawl_direction = checkpoint_data.get('crawl_direction', 'desc')

# 从指定页开始爬取
for page in range(start_page, max_pages):
    articles = await fetch_page(page)
    
    for article in articles:
        article_id = int(article['article_id'])
        
        # 根据爬取方向判断是否已爬取
        if crawl_direction == 'desc':
            # 倒序：article_id 越小，越旧
            if min_article_id and article_id <= min_article_id:
                logger.info(f"⏭️  跳过已爬取文章: {article_id} (<= {min_article_id})")
                continue
        else:
            # 正序：article_id 越大，越新
            if min_article_id and article_id >= min_article_id:
                logger.info(f"⏭️  跳过已爬取文章: {article_id} (>= {min_article_id})")
                continue
        
        # 爬取新文章
        await crawl_article(article)
        
        # 更新最小/最大 article_id
        if crawl_direction == 'desc':
            if not min_article_id or article_id < min_article_id:
                min_article_id = article_id
        else:
            if not min_article_id or article_id > min_article_id:
                min_article_id = article_id
        
        # 保存检查点
        checkpoint.save_checkpoint(
            current_page=page + 1,
            min_article_id=min_article_id,
            ...
        )
```

---

## 📊 当前实现状态

### ✅ 已实现

1. **BBSSpider** - 基于页码的检查点
   - 适用于传统分页论坛
   - 页码和内容顺序一致

2. **检查点管理器** - 通用检查点功能
   - 保存/加载检查点
   - 支持多种状态

### ❌ 未实现

1. **DynamicNewsCrawler** - 未集成检查点
   - `crawl-news` 命令不支持断点续传
   - 需要添加检查点支持

2. **基于 article_id 的检查点** - 未实现
   - 当前只支持基于页码
   - 需要添加 article_id 去重逻辑

---

## 🎯 针对 sxd.xd.com 的改进建议

### 改进1: 为 DynamicNewsCrawler 添加检查点支持

```python
# 在 DynamicNewsCrawler.crawl_dynamic_page_ajax() 中
async def crawl_dynamic_page_ajax(self, base_url: str, max_pages: Optional[int] = None):
    # 1. 创建检查点管理器
    checkpoint = CheckpointManager(site=self.config.bbs.base_url, board="news")
    
    # 2. 从检查点恢复
    checkpoint_data = checkpoint.load_checkpoint()
    seen_article_ids = set()
    start_page = 1
    
    if checkpoint_data and checkpoint_data.get('status') != 'completed':
        seen_article_ids = set(checkpoint_data.get('seen_article_ids', []))
        start_page = checkpoint_data.get('current_page', 1)
        logger.info(f"🔄 从检查点恢复: 第 {start_page} 页，已爬取 {len(seen_article_ids)} 篇文章")
    
    # 3. 从 start_page 开始爬取
    page = start_page
    all_articles = []
    
    while True:
        # ... 爬取逻辑 ...
        
        # 4. 过滤已爬取的文章
        new_articles = []
        for article in articles:
            article_id = article['article_id']
            if article_id not in seen_article_ids:
                seen_article_ids.add(article_id)
                new_articles.append(article)
        
        # 5. 保存检查点
        checkpoint.save_checkpoint(
            current_page=page + 1,
            seen_article_ids=list(seen_article_ids),
            last_thread_id=new_articles[-1]['article_id'] if new_articles else None,
            status="running",
            stats={
                "articles_found": len(all_articles),
                "articles_crawled": len(all_articles)
            }
        )
        
        page += 1
```

### 改进2: 添加 article_id 去重逻辑

```python
# 在爬取过程中
for article in articles:
    article_id = article['article_id']
    
    # 检查是否已爬取（通过检查点）
    if article_id in seen_article_ids:
        logger.debug(f"⏭️  跳过已爬取文章: {article_id}")
        continue
    
    # 检查是否已下载（通过文件系统）
    # 如果文件已存在，也跳过
    if article_id in downloaded_article_ids:
        logger.debug(f"⏭️  跳过已下载文章: {article_id}")
        continue
    
    # 爬取新文章
    await crawl_article(article)
    seen_article_ids.add(article_id)
```

---

## 🔍 当前机制的工作流程

### BBS论坛（BBSSpider）

```
1. 开始爬取第1页
   → 爬取帖子1, 2, 3...
   → 保存检查点: current_page = 2

2. 中断

3. 恢复爬取
   → 加载检查点: current_page = 2
   → 从第2页开始爬取
   → ✅ 正常工作（因为页码和内容顺序一致）
```

### 动态新闻（DynamicNewsCrawler）- 当前未支持

```
1. 开始爬取第1页
   → 发现文章: 15503, 15502, 15501 (倒序)
   → ❌ 未保存检查点

2. 中断

3. 恢复爬取
   → ❌ 没有检查点
   → 从头开始爬取
   → ⚠️ 会重复爬取第1页的内容
```

---

## 💡 总结

### 当前检查点机制

- **记录方式**: 基于页码（current_page）
- **适用场景**: 传统分页网站（页码和内容顺序一致）
- **已集成**: BBSSpider ✅
- **未集成**: DynamicNewsCrawler ❌

### sxd.xd.com 的问题

- **文章排列**: 倒序（第一页 article_id 最大）
- **当前机制**: 不适用（基于页码会跳过内容）
- **需要改进**: 基于 article_id 去重

### 改进方向

1. **为 DynamicNewsCrawler 添加检查点支持** ⭐
2. **实现基于 article_id 的去重逻辑** ⭐
3. **支持倒序/正序爬取方向检测**

---

## 🚀 下一步

需要我实现这些改进吗？我可以：
1. 为 `DynamicNewsCrawler` 添加检查点支持
2. 实现基于 `article_id` 的去重逻辑
3. 支持倒序排列的网站
