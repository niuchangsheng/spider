# 设计变更：重构命令行参数，分离配置类型

## 基本信息

- **标题**: 重构命令行参数，分离配置类型
- **提出人**: 架构师 Chang
- **日期**: 2026-02-04
- **状态**: 已批准
- **关联Issue**: N/A
- **优先级**: 🟡 中
- **预计工作量**: 1小时

---

## 1. 变更概述

### 1.1 问题描述

当前命令行参数混淆了"论坛类型预设"和"配置文件名"：

```bash
# 当前设计（混乱）
--preset xindong  # 是配置文件还是论坛类型？不清晰
--preset discuz   # 是论坛类型
```

同时，mode 设计不合理：
- mode 1: 单个帖子（太简单，用处不大）
- mode 2: 板块（需要指定URL）
- mode 3: 批量（需要URL列表）

### 1.2 变更目标

1. 分离配置类型参数：`--preset` (论坛类型) 和 `--config` (配置文件)
2. 重新设计 mode：专注于批量处理
3. 优化配置文件结构

---

## 2. 设计方案

### 2.1 新的命令行参数

```bash
python spider.py [配置来源] [处理模式] [其他选项]

配置来源（三选一）：
  --preset TYPE    论坛类型预设 (discuz/phpbb/vbulletin)
  --config NAME    配置文件名 (从 configs/ 加载)
  --url URL        自动检测配置

处理模式（二选一）：
  --mode 1         批量爬取URL列表
  --mode 2         批量爬取板块列表
```

### 2.2 使用示例

```bash
# 示例1: 使用配置文件 + URL列表模式
python spider.py --config xindong --mode 1

# 示例2: 使用配置文件 + 板块模式
python spider.py --config xindong --mode 2

# 示例3: 使用论坛类型预设 + 自定义URL
python spider.py --preset discuz --mode 1 --urls "url1,url2,url3"

# 示例4: 自动检测 + URL列表
python spider.py --url "https://forum.com/board" --mode 1
```

### 2.3 配置文件结构调整

**configs/xindong.json**:

```json
{
  "name": "心动论坛",
  "forum_type": "discuz",
  "base_url": "https://bbs.xd.com",
  
  "selectors": { ... },
  "crawler": { ... },
  "image": { ... },
  
  "urls": [
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145"
  ],
  
  "boards": [
    {
      "name": "神仙道玩家交流",
      "url": "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21"
    }
  ]
}
```

**变更点**：
- `example_threads` → `urls` (更简洁)
- `boards` 从字典改为列表（更规范）
- 移除重复的"神仙道"板块

---

## 3. 技术方案

### 3.1 命令行参数更新

```python
parser = argparse.ArgumentParser(
    description='BBS图片爬虫 (v2.0)',
    epilog='示例: python spider.py --config xindong --mode 1'
)

# 配置来源（互斥组）
config_group = parser.add_mutually_exclusive_group(required=True)
config_group.add_argument('--preset', type=str, 
                         help='论坛类型预设 (discuz/phpbb/vbulletin)')
config_group.add_argument('--config', type=str,
                         help='配置文件名 (从 configs/ 加载，如: xindong)')
config_group.add_argument('--url', type=str,
                         help='论坛URL（自动检测配置）')

# 处理模式
parser.add_argument('--mode', type=int, default=1, choices=[1, 2],
                   help='处理模式: 1=URL列表, 2=板块列表')

# 可选参数
parser.add_argument('--urls', type=str,
                   help='URL列表，逗号分隔（覆盖配置文件）')
parser.add_argument('--boards', type=str,
                   help='板块URL列表，逗号分隔（覆盖配置文件）')
parser.add_argument('--max-pages', type=int, default=3,
                   help='每个板块最大爬取页数')
```

### 3.2 配置加载逻辑

```python
async def main():
    args = parser.parse_args()
    
    # 1. 加载配置
    if args.config:
        config = get_example_config(args.config)
    elif args.preset:
        config = ForumPresets.load(args.preset)
    elif args.url:
        config = await ConfigLoader.auto_detect_config(args.url)
    
    # 2. 创建爬虫
    spider = await SpiderFactory.create(config=config)
    
    # 3. 获取任务列表
    if args.mode == 1:
        # URL列表模式
        urls = args.urls.split(',') if args.urls else get_example_threads(args.config)
        await crawl_urls(spider, urls)
    
    elif args.mode == 2:
        # 板块列表模式
        if args.boards:
            board_urls = args.boards.split(',')
        else:
            boards = get_forum_boards(args.config)
            board_urls = [b['url'] for b in boards]
        await crawl_boards(spider, board_urls, args.max_pages)
```

### 3.3 多线程实现

```python
async def crawl_urls(spider, urls):
    """并发爬取URL列表"""
    tasks = [spider.crawl_thread_from_url(url) for url in urls]
    await asyncio.gather(*tasks, return_exceptions=True)

async def crawl_boards(spider, board_urls, max_pages):
    """并发爬取板块列表"""
    tasks = [
        spider.crawl_board(url, max_pages=max_pages) 
        for url in board_urls
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 4. 影响分析

### 4.1 API变更

| 场景 | 旧命令 | 新命令 |
|------|--------|--------|
| 心动论坛示例 | `--preset xindong --mode 1` | `--config xindong --mode 1` |
| Discuz类型 | `--preset discuz --mode 1` | `--preset discuz --mode 1` ✅ 不变 |
| 自动检测 | `--url "..." --mode 1` | `--url "..." --mode 1` ✅ 不变 |

### 4.2 配置文件变更

| 字段 | 旧格式 | 新格式 |
|------|--------|--------|
| URL列表 | `example_threads: [...]` | `urls: [...]` |
| 板块列表 | `boards: {name: {...}}` | `boards: [{name, url}, ...]` |

### 4.3 向后兼容

- ⚠️ `--preset xindong` 不再工作，需改为 `--config xindong`
- ✅ `--preset discuz/phpbb` 仍然工作
- ⚠️ `--mode 3` 已移除，使用 `--mode 1` 替代

---

## 5. 实施计划

### 阶段1: 更新配置文件
- [ ] 修改 `configs/xindong.json`
  - [ ] `example_threads` → `urls`
  - [ ] `boards` 字典 → 列表
  - [ ] 移除重复板块
- [ ] 修改 `configs/example.json`

### 阶段2: 更新命令行参数
- [ ] 添加 `--config` 参数
- [ ] `--preset` 限制为论坛类型
- [ ] 简化 `--mode` (1=URLs, 2=boards)
- [ ] 添加 `--urls` 和 `--boards` 可选参数

### 阶段3: 更新主函数逻辑
- [ ] 实现新的配置加载逻辑
- [ ] 实现 `crawl_urls()` 函数
- [ ] 实现 `crawl_boards()` 函数
- [ ] 使用 `asyncio.gather()` 实现并发

### 阶段4: 更新文档
- [ ] 更新 `README.md`
- [ ] 更新 `run_spider.sh`
- [ ] 更新 `configs/README.md`

### 阶段5: 测试验证
- [ ] 测试 `--config xindong --mode 1`
- [ ] 测试 `--config xindong --mode 2`
- [ ] 测试 `--preset discuz --mode 1`
- [ ] 测试 `--url "..." --mode 1`

---

## 6. 决策

- [x] ✅ **批准实施** - 架构更清晰，职责分离

**批准人**: 架构师 Chang  
**批准日期**: 2026-02-04

---

**文档状态**: 已批准  
**版本**: v1.0
