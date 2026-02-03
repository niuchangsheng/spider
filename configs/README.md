# 论坛配置文件说明

## 📁 目录结构

```
configs/
├── README.md           # 本文档
├── example.json        # 配置模板
└── xindong.json        # 心动论坛配置（示例）
```

---

## 🚀 快速开始

### 1. 复制模板

```bash
cp configs/example.json configs/myforum.json
```

### 2. 编辑配置

```bash
vim configs/myforum.json
```

### 3. 使用配置

```python
from config import get_example_config
from spider import SpiderFactory

# 自动加载 myforum.json
config = get_example_config("myforum")
spider = SpiderFactory.create(config=config)
```

---

## 📝 配置文件格式

### 基本信息

```json
{
  "name": "论坛名称",
  "forum_type": "discuz|phpbb|vbulletin|custom",
  "base_url": "https://forum.com",
  "login_url": "https://forum.com/login"
}
```

### 选择器配置

```json
{
  "selectors": {
    "thread_list": "CSS选择器 - 帖子列表容器",
    "thread_link": "CSS选择器 - 帖子标题链接",
    "image": "CSS选择器 - 图片元素（支持多个，逗号分隔）",
    "next_page": "CSS选择器 - 下一页按钮"
  }
}
```

**如何获取选择器**：
1. 使用自动检测：`python spider.py --url "论坛URL"`
2. 手动分析：浏览器F12 → 选择元素 → Copy selector

### 爬虫参数

```json
{
  "crawler": {
    "max_concurrent_requests": 5,    // 最大并发数（建议3-5）
    "download_delay": 1.0,            // 请求延迟（秒，建议1-3）
    "request_timeout": 30,            // 超时时间（秒）
    "max_retries": 3                  // 最大重试次数
  }
}
```

### 图片过滤

```json
{
  "image": {
    "min_width": 200,      // 最小宽度（像素）
    "min_height": 200,     // 最小高度（像素）
    "min_size": 10240      // 最小文件大小（字节，10KB）
  }
}
```

### 板块配置（可选）

```json
{
  "boards": {
    "板块1": {
      "url": "https://forum.com/board1",
      "board_name": "板块显示名称"
    },
    "板块2": {
      "url": "https://forum.com/board2",
      "board_name": "另一个板块"
    }
  }
}
```

### 示例帖子（可选）

```json
{
  "example_threads": [
    "https://forum.com/thread/123",
    "https://forum.com/thread/456"
  ]
}
```

---

## 🎯 完整示例

参考 `xindong.json`：

```json
{
  "name": "心动论坛",
  "forum_type": "discuz",
  "base_url": "https://bbs.xd.com",
  "login_url": "https://bbs.xd.com/member.php?mod=logging&action=login",
  
  "selectors": {
    "thread_list": "tbody[id^='normalthread'], tbody[id^='stickthread']",
    "thread_link": "a.s.xst, a.xst",
    "image": "img.zoom,img[file],img[aid],div.pattl img,div.pcb img",
    "next_page": "a.nxt, div.pg a.nxt"
  },
  
  "crawler": {
    "max_concurrent_requests": 3,
    "download_delay": 2.0,
    "request_timeout": 30,
    "max_retries": 3
  },
  
  "image": {
    "min_width": 300,
    "min_height": 300,
    "min_size": 30000
  },
  
  "boards": {
    "神仙道": {
      "url": "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21",
      "board_name": "神仙道"
    }
  },
  
  "example_threads": [
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145"
  ]
}
```

---

## 🔍 常见问题

### Q1: 如何找到正确的选择器？

**A**: 三种方法：

1. **自动检测（推荐）**:
```bash
python spider.py --url "https://your-forum.com/board"
```

2. **浏览器工具**:
- 打开论坛页面
- 按F12打开开发者工具
- 按Ctrl+Shift+C选择元素
- 右键 → Copy → Copy selector

3. **参考预设**: 查看 `xindong.json` 或使用论坛类型预设

### Q2: 配置文件放在哪里？

**A**: 放在 `configs/` 目录下，文件名即为配置名称。

例如：
- `configs/myforum.json` → 使用 `get_example_config("myforum")`
- `configs/test.json` → 使用 `get_example_config("test")`

### Q3: 如何测试我的配置？

**A**: 
```bash
# 测试配置加载
python -c "from config import get_example_config; print(get_example_config('myforum'))"

# 运行爬虫测试
python spider.py --preset myforum --mode 1

# 自动检测并测试
python spider.py --url "https://your-forum.com/board" --mode 1
```

### Q4: 支持哪些论坛类型？

**A**:
- ✅ Discuz (如心动论坛)
- ✅ phpBB
- ✅ vBulletin
- ✅ 自定义 (custom)

### Q5: 如何共享我的配置？

**A**: 直接分享 JSON 文件即可，其他用户放到 `configs/` 目录下就能使用。

---

## 📚 相关文档

- [ARCHITECTURE.md](../ARCHITECTURE.md) - 系统架构
- [README.md](../README.md) - 使用指南
- [config.py](../config.py) - 配置管理（含自动检测功能）

---

**最后更新**: 2026-02-04  
**维护状态**: 🟢 活跃维护
