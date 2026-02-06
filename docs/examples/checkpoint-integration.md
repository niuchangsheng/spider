# 检查点功能集成说明

## ✅ 已完成的功能

### 1. 检查点管理器 (`core/checkpoint.py`)
- ✅ 本地文件存储（JSON格式）
- ✅ 保存/加载检查点
- ✅ 标记完成/错误状态
- ✅ 清除检查点

### 2. 爬虫集成 (`spiders/bbs_spider.py`)
- ✅ `crawl_board()` 方法支持断点续传
- ✅ 自动保存检查点（每页保存）
- ✅ 从检查点恢复
- ✅ 手动指定起始页

### 3. CLI 命令支持
- ✅ `--resume` / `--no-resume` 参数
- ✅ `--start-page` 参数
- ✅ `checkpoint-status` 子命令

---

## 📖 使用示例

### 1. 基本爬取（自动保存检查点）

```bash
# 爬取板块，自动保存检查点
python spider.py crawl-board "https://sxd.xd.com/" --config xindong

# 如果中断，再次运行会自动从检查点恢复
python spider.py crawl-board "https://sxd.xd.com/" --config xindong
# 输出: 🔄 从检查点恢复: 第 15 页
```

### 2. 手动指定起始页

```bash
# 从第20页开始爬取（覆盖检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config xindong --start-page 20
```

### 3. 不从检查点恢复（重新开始）

```bash
# 清除检查点，从头开始
python spider.py crawl-board "https://sxd.xd.com/" --config xindong --no-resume
```

### 4. 查看检查点状态

```bash
# 查看检查点信息
python spider.py checkpoint-status --site sxd.xd.com --board all

# 清除检查点
python spider.py checkpoint-status --site sxd.xd.com --board all --clear
```

### 5. 爬取多个板块（支持检查点）

```bash
# 爬取配置中的所有板块，每个板块独立检查点
python spider.py crawl-boards --config xindong

# 从第10页开始爬取所有板块
python spider.py crawl-boards --config xindong --start-page 10
```

---

## 📁 检查点文件位置

检查点文件保存在项目根目录的 `checkpoints/` 目录：

```
checkpoints/
├── sxd_xd_com_all.json          # sxd.xd.com 网站，all 板块
├── bbs_xd_com_神仙道.json       # bbs.xd.com 网站，神仙道板块
└── ...
```

文件命名规则：`{site}_{board}.json`
- `site`: 网站域名（`.` 替换为 `_`）
- `board`: 板块名称（特殊字符替换为 `_`）

---

## 🔍 检查点文件格式

```json
{
  "site": "sxd.xd.com",
  "board": "all",
  "current_page": 15,
  "last_thread_id": "12345",
  "last_thread_url": "https://sxd.xd.com/article/12345",
  "status": "running",
  "created_at": "2026-02-06T10:30:00",
  "last_update_time": "2026-02-06T11:45:00",
  "stats": {
    "crawled_count": 1500,
    "failed_count": 5,
    "images_downloaded": 3000
  }
}
```

---

## 🎯 工作原理

### 检查点保存时机

1. **每页爬取完成后**：自动保存检查点
2. **发生错误时**：保存错误状态
3. **任务完成时**：标记为 `completed`

### 恢复逻辑

1. **检查检查点是否存在**
2. **如果存在且状态为 `completed`**：跳过爬取
3. **如果存在且状态为 `running`**：从保存的页码继续
4. **如果不存在**：从头开始

### 页码跳转

- **从检查点恢复**：从第一页开始，通过"下一页"链接到达指定页
- **已爬取的帖子**：通过 `storage.thread_exists()` 自动跳过
- **手动指定起始页**：覆盖检查点，从指定页开始

---

## ⚠️ 注意事项

1. **检查点文件是临时的**：存储在本地，重启后仍然有效
2. **每个板块独立检查点**：不同板块有独立的检查点文件
3. **页码跳转限制**：如果论坛不支持URL参数分页，需要从第一页开始跳转
4. **已爬帖子跳过**：通过MongoDB的 `thread_exists()` 检查，确保不重复爬取

---

## 🐛 故障排查

### 问题1：检查点恢复后重复爬取

**原因**：MongoDB未连接或 `thread_exists()` 失效

**解决**：
```bash
# 确保MongoDB已连接
# 或使用 --no-resume 重新开始
python spider.py crawl-board "..." --no-resume
```

### 问题2：无法跳转到指定页

**原因**：论坛不支持URL参数分页

**解决**：
- 检查点会从第一页开始，通过"下一页"链接到达指定页
- 已爬取的帖子会自动跳过（通过去重机制）

### 问题3：检查点文件损坏

**解决**：
```bash
# 清除检查点，重新开始
python spider.py checkpoint-status --site sxd.xd.com --board all --clear
```

---

## 📊 性能影响

- **检查点保存**：每页保存一次，开销很小（<1ms）
- **检查点加载**：启动时加载一次，开销很小（<5ms）
- **总体影响**：几乎可以忽略不计

---

## 🔮 未来改进

1. **支持URL参数分页**：直接跳转到指定页（如 `?page=20`）
2. **检查点压缩**：定期清理旧检查点
3. **检查点备份**：自动备份到其他位置
4. **分布式检查点**：支持多机器共享检查点（Redis/MongoDB）
