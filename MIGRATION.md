# 架构迁移指南 (v1.x → v2.0)

## 概述

项目已升级为统一架构（v2.0），整合了原有的 `bbs_spider.py`、`crawl_xindong.py` 和 `config_xindong.py`。

**升级日期**: 2026-02-03  
**设计文档**: `docs/designs/2026-02-03-refactor-spider-architecture.md`

---

## 主要变更

### 1. 文件变更

| 旧文件 | 新文件 | 状态 |
|--------|--------|------|
| `bbs_spider.py` | `spider.py` | ✅ 已整合 |
| `crawl_xindong.py` | `spider.py` | ✅ 已整合 |
| `config_xindong.py` | `config.py` (ForumPresets) | ✅ 已整合 |

### 2. API变更

#### 创建爬虫实例

**旧方式**:
```python
# 方式1
from bbs_spider import BBSSpider
spider = BBSSpider()

# 方式2
from crawl_xindong import XindongSpider
spider = XindongSpider()
```

**新方式**:
```python
# 使用预设配置
from spider import SpiderFactory
spider = SpiderFactory.create(preset="xindong")

# 自动检测
spider = SpiderFactory.create(url="https://bbs.xd.com/forum")

# 手动配置
from config import Config
spider = SpiderFactory.create(config=my_config)
```

#### 配置管理

**旧方式**:
```python
from config_xindong import xindong_config
import config as config_module
config_module.config = xindong_config
```

**新方式**:
```python
from config import ForumPresets

# 直接使用预设
config = ForumPresets.xindong()
config = ForumPresets.discuz()
config = ForumPresets.phpbb()
```

---

## 迁移步骤

### 步骤1: 更新导入语句

```python
# 旧代码
from bbs_spider import BBSSpider
from crawl_xindong import XindongSpider
from config_xindong import xindong_config

# 新代码
from spider import BBSSpider, DiscuzSpider, SpiderFactory
from config import Config, ForumPresets, ConfigLoader
```

### 步骤2: 更新爬虫创建

```python
# 旧代码
async with BBSSpider() as spider:
    await spider.crawl_board(...)

# 新代码
async with SpiderFactory.create(preset="discuz") as spider:
    await spider.crawl_board(...)
```

### 步骤3: 更新配置

```python
# 旧代码
from config_xindong import xindong_config, XINDONG_BOARDS

# 新代码
from config import ForumPresets, XINDONG_BOARDS

config = ForumPresets.xindong()
```

### 步骤4: 测试验证

```bash
# 运行新的统一脚本
python spider.py --preset xindong --mode 1

# 验证功能正常
```

---

## 功能对照表

| 功能 | 旧API | 新API |
|------|-------|-------|
| 创建通用爬虫 | `BBSSpider()` | `SpiderFactory.create()` |
| 创建Discuz爬虫 | `XindongSpider()` | `SpiderFactory.create(preset="xindong")` |
| 获取配置 | `config_xindong.xindong_config` | `ForumPresets.xindong()` |
| 自动检测 | 手动运行 `detect_selectors.py` | `ConfigLoader.auto_detect(url)` |
| 爬取帖子 | `spider.crawl_thread()` | `spider.crawl_thread()` ✅ 不变 |
| 爬取板块 | `spider.crawl_board()` | `spider.crawl_board()` ✅ 不变 |

---

## 兼容性说明

### ✅ 保持兼容

以下功能保持不变，可无缝迁移：

- `spider.crawl_thread(thread_info)` 
- `spider.crawl_board(board_url, board_name, max_pages)`
- `spider.crawl_threads_from_list(thread_urls)`
- `spider.get_statistics()`

### ⚠️ 需要调整

以下功能需要更新：

- 爬虫实例创建方式
- 配置加载方式
- 自定义爬虫继承

---

## 常见问题

### Q1: 旧代码还能用吗？

**A**: 可以。旧文件（`bbs_spider.py`、`crawl_xindong.py`）仍然保留，但标记为已弃用。建议迁移到新架构。

### Q2: 迁移需要多久？

**A**: 小型项目约10-30分钟，主要是更新导入和初始化代码。

### Q3: 新架构有什么优势？

**A**: 
- 代码量减少25%
- 统一的配置管理
- 支持自动检测选择器
- 更清晰的架构分层
- 易于扩展新的论坛类型

### Q4: 如何添加自定义论坛支持？

**新架构**:
```python
from spider import BBSSpider, SpiderFactory

class MyForumSpider(BBSSpider):
    async def process_images(self, images):
        # 自定义处理逻辑
        return processed_images

# 注册到工厂
SpiderFactory.register('myforum', MyForumSpider)

# 使用
spider = SpiderFactory.create(preset="myforum")
```

---

## 完整示例

### 旧代码示例

```python
# old_crawler.py
import asyncio
from crawl_xindong import XindongSpider

async def main():
    async with XindongSpider() as spider:
        thread_info = {
            'url': "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145",
            'thread_id': "3479145",
            'board': '神仙道'
        }
        await spider.crawl_thread(thread_info)

if __name__ == "__main__":
    asyncio.run(main())
```

### 新代码示例

```python
# new_crawler.py
import asyncio
from spider import SpiderFactory

async def main():
    async with SpiderFactory.create(preset="xindong") as spider:
        thread_info = {
            'url': "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145",
            'thread_id': "3479145",
            'board': '神仙道'
        }
        await spider.crawl_thread(thread_info)

if __name__ == "__main__":
    asyncio.run(main())
```

**差异**: 只需更改导入和实例创建方式，核心爬取逻辑完全相同！

---

## 获取帮助

- 设计文档: `docs/designs/2026-02-03-refactor-spider-architecture.md`
- 架构文档: `ARCHITECTURE.md`
- 使用文档: `README.md`
- 示例代码: `spider.py` 中的 `main()` 函数

---

**迁移状态**: ✅ 建议迁移  
**兼容性**: 🟢 向后兼容（旧文件保留）  
**截止日期**: 无（可逐步迁移）
