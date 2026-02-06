# 检查点管理器使用示例

## 基本使用

### 1. 创建检查点管理器

```python
from core.checkpoint import CheckpointManager

# 方式1: 直接创建
checkpoint = CheckpointManager(
    site="https://sxd.xd.com/",
    board="all"
)

# 方式2: 使用便捷函数
from core.checkpoint import get_checkpoint_manager
checkpoint = get_checkpoint_manager("sxd.xd.com", "all")
```

### 2. 保存检查点

```python
# 在爬取过程中保存检查点
checkpoint.save_checkpoint(
    current_page=15,
    last_thread_id="12345",
    last_thread_url="https://sxd.xd.com/article/12345",
    status="running",
    stats={
        "crawled_count": 1500,
        "failed_count": 5,
        "images_downloaded": 3000
    }
)
```

### 3. 加载检查点（断点续传）

```python
# 检查是否有检查点
if checkpoint.exists():
    checkpoint_data = checkpoint.load_checkpoint()
    
    if checkpoint_data:
        start_page = checkpoint_data['current_page']
        last_thread_id = checkpoint_data.get('last_thread_id')
        
        print(f"🔄 从检查点恢复: 第 {start_page} 页")
        print(f"   最后爬取的帖子ID: {last_thread_id}")
        
        # 从 start_page 继续爬取
        # ...
```

### 4. 标记完成

```python
# 爬取完成后标记
checkpoint.mark_completed(final_stats={
    "total_crawled": 2000,
    "total_images": 5000
})
```

### 5. 清除检查点

```python
# 清除检查点（重新开始）
checkpoint.clear_checkpoint()
```

## 在爬虫中集成

### 修改 `spiders/bbs_spider.py`

```python
from core.checkpoint import CheckpointManager

class BBSSpider(BaseSpider):
    async def crawl_board(self, board_url: str, board_name: str, max_pages: Optional[int] = None):
        """爬取板块（支持断点续传）"""
        # 1. 创建检查点管理器
        checkpoint = CheckpointManager(
            site=self.config.bbs.base_url,
            board=board_name
        )
        
        # 2. 加载检查点
        checkpoint_data = checkpoint.load_checkpoint()
        start_page = checkpoint_data['current_page'] if checkpoint_data else 1
        
        if checkpoint_data:
            logger.info(f"🔄 从检查点恢复: 第 {start_page} 页")
            if checkpoint_data.get('status') == 'completed':
                logger.info("✅ 该板块已完成爬取")
                return
        
        # 3. 从检查点位置继续爬取
        page_count = 0
        current_url = board_url
        
        for page in range(start_page, max_pages or float('inf')):
            logger.info(f"📄 爬取第 {page} 页...")
            
            # 获取页面
            html = await self.fetch_page(current_url)
            if not html:
                checkpoint.mark_error("无法获取页面")
                break
            
            # 解析帖子列表
            threads = self.parser.parse_thread_list(html, current_url)
            if not threads:
                logger.warning(f"⚠️  第 {page} 页没有找到帖子")
                break
            
            # 爬取每个帖子
            last_thread_id = None
            for thread_info in threads:
                await self.crawl_thread(thread_info)
                last_thread_id = thread_info.get('thread_id')
            
            # 4. 保存检查点（每页保存一次）
            checkpoint.save_checkpoint(
                current_page=page + 1,  # 下一页
                last_thread_id=last_thread_id,
                last_thread_url=threads[-1].get('url') if threads else None,
                status="running",
                stats={
                    "crawled_count": self.stats['threads_crawled'],
                    "failed_count": self.stats['images_failed'],
                    "images_downloaded": self.stats['images_downloaded']
                }
            )
            
            # 查找下一页
            next_url = self.parser.find_next_page(html, current_url)
            if not next_url:
                logger.info("✅ 已到达最后一页")
                break
            
            current_url = next_url
            page_count += 1
        
        # 5. 标记完成
        checkpoint.mark_completed(final_stats={
            "total_crawled": self.stats['threads_crawled'],
            "total_images": self.stats['images_downloaded']
        })
        
        logger.success(f"🎉 板块爬取完成: {board_name}")
```

## 检查点文件格式

检查点文件保存在 `checkpoints/` 目录下，格式为 JSON：

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

## 命令行使用

### 查看检查点状态

```python
# 查看检查点
from core.checkpoint import CheckpointManager

checkpoint = CheckpointManager("sxd.xd.com", "all")
if checkpoint.exists():
    data = checkpoint.load_checkpoint()
    print(f"状态: {data['status']}")
    print(f"当前页: {data['current_page']}")
    print(f"已爬取: {data['stats'].get('crawled_count', 0)}")
else:
    print("没有检查点")
```

### 清除检查点

```python
checkpoint = CheckpointManager("sxd.xd.com", "all")
checkpoint.clear_checkpoint()
print("检查点已清除")
```

## 注意事项

1. **检查点文件位置**: 默认保存在项目根目录的 `checkpoints/` 目录
2. **文件命名**: `{site}_{board}.json`，特殊字符会被替换为下划线
3. **自动创建目录**: 如果 `checkpoints/` 目录不存在，会自动创建
4. **编码**: 文件使用 UTF-8 编码，支持中文
5. **线程安全**: 当前实现不是线程安全的，多进程/多线程使用时需要加锁

## 故障恢复

如果爬取过程中断：

1. **自动恢复**: 下次运行时会自动从检查点恢复
2. **手动恢复**: 可以手动编辑 JSON 文件修改 `current_page`
3. **重新开始**: 删除检查点文件或调用 `clear_checkpoint()`
