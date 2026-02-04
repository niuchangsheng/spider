# 实施方案A：子命令模式重构

## 基本信息

- **标题**: 实施子命令模式重构
- **基于设计**: docs/designs/2026-02-04-interface-review.md 方案A
- **提出人**: 架构师
- **日期**: 2026-02-04
- **状态**: ✅ 已实施
- **优先级**: 🟢 高
- **预计工作量**: 2小时

---

## 1. 变更概述

采用子命令模式（类似 git/docker）重构CLI接口，解决以下问题：
1. --url 职责混乱（配置 vs 数据）
2. --mode 语义不清
3. 参数依赖关系隐晦
4. 默认行为不合理

---

## 2. 新的命令结构

### 2.1 子命令概览

```bash
spider.py <subcommand> [options]

子命令:
  crawl-url       爬取单个URL
  crawl-urls      爬取配置中的URL列表
  crawl-board     爬取单个板块
  crawl-boards    爬取配置中的所有板块
```

### 2.2 详细用法

#### crawl-url - 爬取单个URL

```bash
spider.py crawl-url <URL> [--auto-detect | --preset TYPE | --config NAME]

位置参数:
  URL              帖子URL（必需）

配置来源（互斥，三选一）:
  --auto-detect    自动检测论坛类型
  --preset TYPE    论坛类型预设 (discuz/phpbb/vbulletin)
  --config NAME    配置文件名

示例:
  spider.py crawl-url "https://bbs.xd.com/thread/123" --auto-detect
  spider.py crawl-url "https://bbs.xd.com/thread/123" --config xindong
  spider.py crawl-url "https://bbs.xd.com/thread/123" --preset discuz
```

#### crawl-urls - 爬取配置中的URL列表

```bash
spider.py crawl-urls --config NAME

必需参数:
  --config NAME    配置文件名（必需）

示例:
  spider.py crawl-urls --config xindong
```

#### crawl-board - 爬取单个板块

```bash
spider.py crawl-board <BOARD_URL> [--max-pages N] [--auto-detect | --preset TYPE | --config NAME]

位置参数:
  BOARD_URL        板块URL（必需）

可选参数:
  --max-pages N    最大页数（默认：爬取所有页）

配置来源（互斥，三选一）:
  --auto-detect    自动检测论坛类型
  --preset TYPE    论坛类型预设
  --config NAME    配置文件名

示例:
  spider.py crawl-board "https://bbs.xd.com/forum?fid=21" --config xindong
  spider.py crawl-board "https://bbs.xd.com/forum?fid=21" --config xindong --max-pages 5
  spider.py crawl-board "https://bbs.xd.com/forum?fid=21" --auto-detect
```

#### crawl-boards - 爬取配置中的所有板块

```bash
spider.py crawl-boards --config NAME [--max-pages N]

必需参数:
  --config NAME    配置文件名（必需）

可选参数:
  --max-pages N    每个板块最大页数（默认：爬取所有页）

示例:
  spider.py crawl-boards --config xindong
  spider.py crawl-boards --config xindong --max-pages 5
```

---

## 3. 实施细节

### 3.1 argparse 结构

```python
parser = argparse.ArgumentParser(prog='spider.py', ...)
subparsers = parser.add_subparsers(dest='command', required=True)

# 创建4个子解析器
parser_url = subparsers.add_parser('crawl-url', ...)
parser_urls = subparsers.add_parser('crawl-urls', ...)
parser_board = subparsers.add_parser('crawl-board', ...)
parser_boards = subparsers.add_parser('crawl-boards', ...)
```

### 3.2 处理函数分离

```python
async def main():
    args = parser.parse_args()
    
    if args.command == 'crawl-url':
        await handle_crawl_url(args)
    elif args.command == 'crawl-urls':
        await handle_crawl_urls(args)
    # ...

async def handle_crawl_url(args):
    # 处理 crawl-url 子命令
    ...
```

---

## 4. 迁移对照表

| 旧命令 | 新命令 |
|--------|--------|
| `--config xindong --mode 1` | `crawl-urls --config xindong` |
| `--config xindong --mode 2` | `crawl-boards --config xindong` |
| `--url "..." --mode 1` | `crawl-url "..." --auto-detect` |
| `--config xindong --mode 2 --max-pages 5` | `crawl-boards --config xindong --max-pages 5` |

---

## 5. 优势分析

### 5.1 解决的问题

| 问题 | 旧设计 | 新设计 |
|------|--------|--------|
| URL职责混乱 | --url既是配置又是数据 | crawl-url清晰表达意图 |
| mode语义不清 | mode 1/2不直观 | crawl-urls/crawl-boards明确 |
| 参数依赖隐晦 | --max-pages对mode 1无效 | crawl-board/crawl-boards独有 |
| 默认值不合理 | 默认xindong | 必需参数，无默认值 |

### 5.2 用户体验提升

- ✅ **意图明确**: crawl-url vs crawl-board 一目了然
- ✅ **参数清晰**: 只显示相关参数
- ✅ **符合直觉**: 类似git命令
- ✅ **易于扩展**: 可添加crawl-forum等新命令

---

## 6. 测试验证

### 6.1 帮助信息测试

```bash
✅ python spider.py --help
✅ python spider.py crawl-url --help
✅ python spider.py crawl-urls --help
✅ python spider.py crawl-board --help
✅ python spider.py crawl-boards --help
```

### 6.2 功能测试（待执行）

```bash
# 测试1: crawl-url
python spider.py crawl-url "https://bbs.xd.com/thread/123" --config xindong

# 测试2: crawl-urls
python spider.py crawl-urls --config xindong

# 测试3: crawl-board
python spider.py crawl-board "https://bbs.xd.com/forum?fid=21" --config xindong --max-pages 3

# 测试4: crawl-boards
python spider.py crawl-boards --config xindong --max-pages 5
```

---

## 7. 文档更新清单

- [ ] README.md - 更新所有示例命令
- [ ] run_spider.sh - 适配新的子命令
- [ ] configs/README.md - 更新使用说明
- [ ] MIGRATION.md - 创建迁移指南

---

## 8. 向后兼容

### 8.1 破坏性变更

⚠️ 本次重构是破坏性变更，旧命令不再工作：

```bash
# 旧命令（不再工作）
python spider.py --config xindong --mode 1

# 新命令
python spider.py crawl-urls --config xindong
```

### 8.2 迁移策略

1. 保留旧版本代码作为备份
2. 提供详细的迁移文档
3. 更新所有示例脚本
4. 在 README 中突出显示变更

---

## 9. 实施结论

✅ **实施完成**: 2026-02-04  
✅ **测试状态**: 帮助信息验证通过  
⏳ **待办事项**: 功能测试、文档更新、迁移指南

**架构评估**: ⭐⭐⭐⭐⭐ 显著改进

**批准人**: 架构师  
**批准日期**: 2026-02-04

