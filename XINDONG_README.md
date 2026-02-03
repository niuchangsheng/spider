# 心动论坛爬虫使用指南

专门针对心动论坛（https://bbs.xd.com）优化的配置和使用说明。

## 🎯 论坛信息

- **论坛名称**: 心动网络社区
- **论坛地址**: https://bbs.xd.com
- **论坛系统**: Discuz! X3.4
- **主要板块**: 神仙道、仙境传说、其他游戏讨论区

## 🚀 快速开始

### 步骤1：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤2：直接运行

```bash
python crawl_xindong.py
```

选择功能：
- **选项1**: 爬取示例帖子（神仙道怀旧服公测帖）
- **选项2**: 爬取神仙道板块（前3页）
- **选项3**: 批量爬取多个帖子

### 步骤3：查看结果

图片会保存到：
```
downloads/
└── 神仙道/
    └── 3479145/
        ├── 神仙道_3479145_001_20240126_143000.jpg
        ├── 神仙道_3479145_002_20240126_143005.jpg
        └── ...
```

## 📋 心动论坛特点

### 1. Discuz论坛结构

心动论坛使用Discuz X3.4系统，具有以下特点：

**帖子列表页**：
- URL格式: `forum.php?mod=forumdisplay&fid=21`
- 帖子元素: `<tbody id="normalthread_3479145">`
- 帖子链接: `<a class="s xst">`

**帖子详情页**：
- URL格式: `forum.php?mod=viewthread&tid=3479145`
- 图片附件: `forum.php?mod=attachment&aid=xxx`
- 需要添加 `&nothumb=yes` 参数获取原图

### 2. 图片链接特点

心动论坛的图片主要有两种形式：

**A. 附件形式**（需要特殊处理）：
```html
<a href="forum.php?mod=attachment&aid=1120620">
    <img src="static/image/common/none.gif" file="...">
</a>
```

**B. 外链图片**：
```html
<img src="https://example.com/image.jpg">
```

### 3. 反爬虫机制

- **登录检测**: 部分板块需要登录才能查看
- **访问频率限制**: 建议设置延迟2秒以上
- **Cookie验证**: 可能需要保持会话

## ⚙️ 配置说明

### 选择器配置（已优化）

```python
# 帖子列表（Discuz专用）
thread_list_selector = "tbody[id^='normalthread'], tbody[id^='stickthread']"
thread_link_selector = "a.s.xst, a.xst"

# 图片选择器（覆盖多种情况）
image_selector = "img.zoom, img[file], img[aid], div.pattl img, div.pcb img"

# 下一页
next_page_selector = "a.nxt, div.pg a.nxt"
```

### 爬虫参数（针对心动论坛）

```python
max_concurrent_requests = 3  # 并发数（建议3-5）
download_delay = 2.0         # 延迟2秒（重要！）
request_timeout = 30         # 超时30秒
max_retries = 3              # 重试3次
```

### 图片过滤（针对游戏论坛）

```python
min_width = 300      # 游戏宣传图一般较大
min_height = 300
min_size = 30000     # 30KB以上
```

## 📝 使用示例

### 示例1：爬取示例帖子

```python
python crawl_xindong.py
# 选择 1
```

会爬取这个帖子：
- URL: https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145
- 标题: 神仙道怀旧服11月28日公测
- 包含: 3张宣传大图

### 示例2：自定义爬取

编辑 `crawl_xindong.py`：

```python
# 修改 EXAMPLE_THREADS 列表
EXAMPLE_THREADS = [
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=你的帖子ID",
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=另一个帖子ID",
]
```

### 示例3：爬取整个板块

```python
async def main():
    async with XindongSpider() as spider:
        await spider.crawl_board(
            board_url="https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21",
            board_name="神仙道",
            max_pages=10  # 爬取前10页
        )
```

## 🔍 常见板块ID

从心动论坛找到的主要板块：

| 板块名称 | FID | URL |
|---------|-----|-----|
| 神仙道玩家交流 | 21 | forum.php?mod=forumdisplay&fid=21 |
| 仙境传说RO | 具体查看 | 访问论坛查看 |
| 综合讨论区 | 具体查看 | 访问论坛查看 |

查找方法：
1. 访问 https://bbs.xd.com
2. 点击感兴趣的板块
3. 查看URL中的 `fid=数字` 参数

## ⚠️ 注意事项

### 1. 遵守论坛规则

- **爬取频率**: 建议延迟2秒以上
- **并发数**: 不要超过5个并发
- **访问时间**: 避开高峰期（晚上7-10点）
- **版权意识**: 下载的图片仅供学习研究

### 2. 登录相关

某些板块可能需要登录，配置方法：

```python
# 在 config_xindong.py 中
"login_required": True,
"username": "你的用户名",
"password": "你的密码",
```

### 3. 附件处理

心动论坛的附件链接格式特殊，脚本已自动处理：
- 自动添加 `&nothumb=yes` 获取原图
- 自动转换相对路径为绝对路径
- 处理Discuz特殊的图片懒加载

### 4. 反爬虫应对

如果遇到访问受限：
1. **增加延迟**: 将 `download_delay` 改为 3-5秒
2. **减少并发**: 将 `max_concurrent_requests` 改为 1-2
3. **使用代理**: 配置代理池
4. **登录账号**: 使用论坛账号登录

## 🐛 故障排查

### 问题1：无法下载图片

**可能原因**：
- 图片是附件，需要登录
- 图片链接格式特殊

**解决方案**：
- 配置登录信息
- 检查日志中的图片URL格式

### 问题2：被论坛限制访问

**症状**：返回403或需要验证码

**解决方案**：
- 增加 `download_delay` 到 3秒
- 减少 `max_concurrent_requests` 到 2
- 配置代理

### 问题3：图片尺寸太小

**解决方案**：
修改 `config_xindong.py` 中的过滤条件：
```python
"min_width": 500,   # 只要大图
"min_height": 500,
"min_size": 100000, # 100KB以上
```

## 📊 预期效果

以示例帖子为例：
- **帖子**: 神仙道怀旧服公测
- **图片数量**: 3张（KV宣传图 + 2张截图）
- **图片大小**: 1.45MB + 1.82MB + 1.39MB
- **下载时间**: 约10-15秒（包含延迟）

## 🎉 开始使用

```bash
# 1. 运行爬虫
python crawl_xindong.py

# 2. 选择选项1（爬取示例帖子）

# 3. 查看结果
ls downloads/神仙道/3479145/
```

图片会自动下载到 `downloads` 目录，文件名包含板块、帖子ID、序号和时间戳。

---

**提示**: 这是一个专门为心动论坛优化的配置，开箱即用！
