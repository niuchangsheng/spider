# 检查点功能使用指南

## ✅ 功能状态

**状态**: 🟢 已实现并通过测试  
**版本**: v2.3  
**最后更新**: 2026-02-06

---

## 🎯 功能概述

检查点功能允许爬虫在中断后从上次停止的位置继续爬取，实现断点续传。

### 核心特性

- ✅ **自动保存** - 每爬取一页自动保存检查点
- ✅ **自动恢复** - 再次运行时自动从检查点恢复
- ✅ **手动控制** - 支持手动指定起始页或清除检查点
- ✅ **状态管理** - 支持 running/completed/error 状态
- ✅ **统计信息** - 保存爬取统计信息

---

## 📖 快速开始

### 基本使用

```bash
# 1. 爬取板块（自动保存检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config news

# 2. 如果中断，再次运行会自动恢复
python spider.py crawl-board "https://sxd.xd.com/" --config news
# 输出: 🔄 从检查点恢复: 第 6 页
```

### 查看检查点状态

```bash
# 查看检查点信息
python spider.py checkpoint-status --site sxd.xd.com --board all
```

### 清除检查点

```bash
# 清除检查点（重新开始）
python spider.py checkpoint-status --site sxd.xd.com --board all --clear
```

---

## 🔧 高级用法

### 手动指定起始页

```bash
# 从第5页开始爬取（覆盖检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config news --start-page 5
```

### 不从检查点恢复

```bash
# 重新开始（忽略检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config news --no-resume
```

### 爬取多个板块

```bash
# 每个板块独立检查点
python spider.py crawl-boards --config xindong
```

---

## 📁 检查点文件

### 文件位置

检查点文件保存在 `checkpoints/` 目录：

```
checkpoints/
├── sxd_xd_com_all.json              # sxd.xd.com 网站，all 板块
├── bbs_xd_com_神仙道.json           # bbs.xd.com 网站，神仙道板块
└── ...
```

### 文件命名

- 格式: `{site}_{board}.json`
- 示例: `sxd_xd_com_all.json`
- 支持中文板块名称

### 文件内容

```json
{
  "site": "sxd.xd.com",
  "board": "all",
  "current_page": 10,
  "last_thread_id": "article_50",
  "status": "completed",
  "stats": {
    "total_crawled": 50,
    "total_images": 100
  }
}
```

---

## 🎯 使用场景

### 场景1: 长时间爬取任务

```bash
# 爬取大量页面，可能耗时数小时
python spider.py crawl-board "https://sxd.xd.com/" --config news

# 如果中断，再次运行会自动恢复
python spider.py crawl-board "https://sxd.xd.com/" --config news
```

### 场景2: 网络不稳定

```bash
# 网络中断后，从检查点恢复
python spider.py crawl-board "https://sxd.xd.com/" --config news
# 自动从上次停止的位置继续
```

### 场景3: 分批爬取

```bash
# 第一次：爬取前10页
python spider.py crawl-board "https://sxd.xd.com/" --config news --max-pages 10

# 第二次：继续爬取（从第11页开始）
python spider.py crawl-board "https://sxd.xd.com/" --config news
```

---

## ⚙️ 工作原理

### 检查点保存时机

1. **每页爬取完成后** - 自动保存检查点
2. **发生错误时** - 保存错误状态
3. **任务完成时** - 标记为 `completed`

### 恢复逻辑

1. **检查检查点是否存在**
2. **如果存在且状态为 `completed`** - 跳过爬取
3. **如果存在且状态为 `running`** - 从保存的页码继续
4. **如果不存在** - 从头开始

### 页码跳转

- **从检查点恢复** - 从第一页开始，通过"下一页"链接到达指定页
- **已爬取的帖子** - 通过去重机制自动跳过
- **手动指定起始页** - 覆盖检查点，从指定页开始

---

## 📊 性能影响

| 操作 | 耗时 | 说明 |
|------|------|------|
| 保存检查点 | < 1ms | 每页保存一次 |
| 加载检查点 | < 5ms | 启动时加载一次 |
| **总体影响** | **可忽略** | 对爬取性能影响极小 |

---

## ⚠️ 注意事项

1. **检查点文件是临时的**
   - 存储在本地，重启后仍然有效
   - 可以手动删除或使用 `--clear` 清除

2. **每个板块独立检查点**
   - 不同板块有独立的检查点文件
   - 互不干扰

3. **已完成任务**
   - 如果检查点状态为 `completed`，会跳过爬取
   - 需要清除检查点才能重新爬取

4. **页码跳转限制**
   - 如果论坛不支持URL参数分页，需要从第一页开始跳转
   - 已爬取的帖子通过去重机制自动跳过

---

## 🐛 故障排查

### 问题1: 检查点恢复后重复爬取

**原因**: MongoDB未连接或去重机制失效

**解决**:
```bash
# 确保MongoDB已连接
# 或使用 --no-resume 重新开始
python spider.py crawl-board "..." --no-resume
```

### 问题2: 无法跳转到指定页

**原因**: 论坛不支持URL参数分页

**解决**:
- 检查点会从第一页开始，通过"下一页"链接到达指定页
- 已爬取的帖子会自动跳过（通过去重机制）

### 问题3: 检查点文件损坏

**解决**:
```bash
# 清除检查点，重新开始
python spider.py checkpoint-status --site sxd.xd.com --board all --clear
```

---

## 📚 相关文档

- [检查点使用示例](checkpoint-usage.md)
- [检查点集成说明](checkpoint-integration.md)
- [检查点测试结果](checkpoint-test-results.md)
- [检查点完整测试](checkpoint-complete-test.md)

---

## 🎉 总结

检查点功能已完全实现并通过所有测试，可以投入生产使用。

**核心优势**:
- ✅ 自动保存和恢复
- ✅ 支持长时间爬取任务
- ✅ 网络中断后自动恢复
- ✅ 性能影响可忽略
- ✅ 易于使用和维护
