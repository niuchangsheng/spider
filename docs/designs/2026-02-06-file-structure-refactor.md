# 设计文档：代码文件结构重构

**文档编号**: DESIGN-2026-02-06-002  
**创建日期**: 2026-02-06  
**作者**: Chang (架构师)  
**状态**: ✅ 已实现

---

## 1. 背景与问题

### 1.1 当前文件结构

```
spider/
├── spider.py           # 🔴 过大！包含所有爬虫类、工厂、CLI (1100+行)
├── config.py           # 配置管理
├── core/
│   ├── parser.py       # BaseParser + BBSParser
│   ├── dynamic_parser.py    # DynamicPageParser
│   ├── dynamic_crawler.py   # DynamicNewsCrawler
│   ├── downloader.py        # ImageDownloader
│   ├── deduplicator.py      # ImageDeduplicator
│   ├── storage.py           # Storage
│   └── selector_detector.py # SelectorDetector
├── configs/            # JSON配置文件
├── docs/               # 文档
└── downloads/          # 下载目录
```

### 1.2 问题分析

| 问题 | 描述 | 影响 |
|------|------|------|
| **spider.py 过大** | 1100+ 行，包含多个类和CLI | 难以维护 |
| **层级不清晰** | core/ 混合了不同层级的组件 | 架构模糊 |
| **职责不分离** | 爬虫逻辑和CLI混在一起 | 耦合度高 |
| **基类位置不明** | BaseSpider 在 spider.py，BaseParser 在 core/parser.py | 不一致 |

---

## 2. 目标结构

### 2.1 推荐结构（方案A：按层级组织）

```
spider/
├── spider.py              # CLI入口（精简版，只包含main和参数解析）
├── config.py              # 配置管理（保持不变）
│
├── core/                  # 核心层 - 基础组件
│   ├── __init__.py
│   ├── downloader.py      # ImageDownloader
│   ├── deduplicator.py    # ImageDeduplicator
│   ├── storage.py         # Storage
│   └── selector_detector.py # SelectorDetector
│
├── parsers/               # 🆕 解析器层
│   ├── __init__.py
│   ├── base.py            # 🆕 BaseParser（解析器基类）
│   ├── bbs_parser.py      # BBSParser
│   └── dynamic_parser.py  # DynamicPageParser
│
├── spiders/               # 🆕 爬虫层
│   ├── __init__.py
│   ├── base.py            # 🆕 BaseSpider（爬虫基类）
│   ├── bbs_spider.py      # BBSSpider
│   ├── discuz_spider.py   # DiscuzSpider
│   ├── phpbb_spider.py    # PhpBBSpider
│   ├── vbulletin_spider.py # VBulletinSpider
│   ├── dynamic_crawler.py # DynamicNewsCrawler
│   └── factory.py         # SpiderFactory
│
├── cli/                   # 🆕 CLI层
│   ├── __init__.py
│   ├── handlers.py        # 命令处理函数
│   └── commands.py        # argparse 定义
│
├── detector/              # 🆕 检测器（可选，保持在core也行）
│   ├── __init__.py
│   └── selector_detector.py
│
├── configs/               # 配置文件
├── docs/                  # 文档
└── downloads/             # 下载目录
```

### 2.2 备选结构（方案B：最小改动）

```
spider/
├── spider.py              # CLI入口（精简）
├── config.py              # 配置管理
│
├── core/
│   ├── __init__.py
│   ├── base.py            # 🆕 BaseSpider + BaseParser
│   ├── parser.py          # BBSParser（继承base.BaseParser）
│   ├── dynamic_parser.py  # DynamicPageParser
│   ├── bbs_spider.py      # 🆕 BBSSpider + 子类（从spider.py移出）
│   ├── dynamic_crawler.py # DynamicNewsCrawler
│   ├── factory.py         # 🆕 SpiderFactory（从spider.py移出）
│   ├── downloader.py
│   ├── deduplicator.py
│   ├── storage.py
│   └── selector_detector.py
│
├── cli/                   # 🆕 CLI处理
│   ├── __init__.py
│   └── handlers.py
│
├── configs/
├── docs/
└── downloads/
```

---

## 3. 选定方案

**选定方案A（按层级组织）**，理由：
1. 结构清晰，完全体现4层架构
2. 每个目录职责单一
3. 便于团队协作和代码导航
4. 为未来扩展预留空间

---

## 4. 文件变更详情

### 4.1 新增文件

| 文件 | 内容 | 来源 |
|------|------|------|
| `core/base.py` | BaseSpider, BaseParser | spider.py, core/parser.py |
| `core/bbs_spider.py` | BBSSpider, DiscuzSpider, PhpBBSpider, VBulletinSpider | spider.py |
| `core/factory.py` | SpiderFactory | spider.py |
| `cli/__init__.py` | 包初始化 | 新建 |
| `cli/handlers.py` | handle_crawl_url, handle_crawl_urls 等 | spider.py |

### 4.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `spider.py` | 精简为CLI入口，只保留main()和argparse |
| `core/parser.py` | 移除BaseParser，改为从core.base导入 |
| `core/dynamic_parser.py` | 更新导入路径 |
| `core/dynamic_crawler.py` | 更新导入路径 |

### 4.3 删除文件

无

---

## 5. 实现步骤

| 步骤 | 内容 | 风险 |
|------|------|------|
| 1 | 创建 `core/base.py`，移入 BaseSpider + BaseParser | 低 |
| 2 | 创建 `core/bbs_spider.py`，移入 BBSSpider 及子类 | 中 |
| 3 | 创建 `core/factory.py`，移入 SpiderFactory | 低 |
| 4 | 创建 `cli/handlers.py`，移入命令处理函数 | 中 |
| 5 | 精简 `spider.py` 为CLI入口 | 中 |
| 6 | 更新所有导入路径 | 高 |
| 7 | 测试验证 | - |

---

## 6. 向后兼容

```python
# spider.py 保留兼容导入
from core.base import BaseSpider, BaseParser
from core.bbs_spider import BBSSpider, DiscuzSpider
from core.factory import SpiderFactory

# 用户代码无需修改
from spider import SpiderFactory  # 仍然有效
```

---

## 7. 审批

| 角色 | 姓名 | 意见 | 日期 |
|------|------|------|------|
| 架构师 | Chang | 待审批 | - |

