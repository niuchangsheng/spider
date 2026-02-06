# 设计文档：断点续传与性能优化架构

**文档编号**: DESIGN-2026-02-06-003  
**创建日期**: 2026-02-06  
**作者**: Chang (架构师)  
**状态**: 📋 设计提案

---

## 1. 问题背景

针对大规模爬取任务（如爬取 https://sxd.xd.com/ 所有帖子），存在三个核心挑战：

1. **断点续传** - 爬取过程中断后如何恢复
2. **性能优化** - 如何提高爬取速度
3. **反封禁** - 如何避免被网站管理员封禁

---

## 2. 问题1：断点续传机制

### 2.1 当前状态

✅ **已有基础**：
- Redis 存储 `visited_urls`（已访问URL集合）
- MongoDB 存储 `threads`（帖子数据）
- `storage.thread_exists()` 检查帖子是否已爬取

❌ **缺失功能**：
- 没有检查点（checkpoint）机制
- 没有爬取进度持久化
- 无法从指定位置恢复

### 2.2 架构设计

#### 方案A：基于Redis的检查点机制（推荐）

```python
# Redis 数据结构设计
checkpoint:{site}:{board} = {
    "current_page": 15,           # 当前爬取页数
    "last_thread_id": "12345",    # 最后爬取的帖子ID
    "last_crawl_time": "2026-02-06T10:30:00",
    "status": "running",          # running/paused/completed
    "total_pages": 100,           # 总页数（如果已知）
    "crawled_count": 1500,        # 已爬取帖子数
    "failed_count": 5             # 失败数
}

# 使用示例
checkpoint_key = f"checkpoint:sxd.xd.com:all"
```

**优点**：
- 轻量级，查询快速
- 支持多任务并行
- 易于实现

**缺点**：
- Redis 重启会丢失（可配合持久化）

#### 方案B：基于MongoDB的检查点机制

```python
# MongoDB 集合: checkpoints
{
    "_id": ObjectId,
    "site": "sxd.xd.com",
    "board": "all",
    "current_page": 15,
    "last_thread_id": "12345",
    "last_crawl_time": ISODate,
    "status": "running",
    "metadata": {
        "total_pages": 100,
        "crawled_count": 1500,
        "failed_count": 5
    },
    "created_at": ISODate,
    "updated_at": ISODate
}
```

**优点**：
- 持久化存储，更可靠
- 支持复杂查询和统计
- 可以记录历史记录

**缺点**：
- 查询速度略慢于Redis
- 需要额外的集合管理

#### 方案C：混合方案（最佳实践）⭐

**设计思路**：
- **Redis**：存储实时检查点（快速读写）
- **MongoDB**：定期同步检查点（持久化备份）
- **本地文件**：紧急备份（JSON格式）

```python
class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, site: str, board: str):
        self.site = site
        self.board = board
        self.checkpoint_key = f"checkpoint:{site}:{board}"
        self.backup_file = Path(f"checkpoints/{site}_{board}.json")
    
    async def save_checkpoint(self, page: int, thread_id: str, stats: dict):
        """保存检查点（三级存储）"""
        checkpoint = {
            "current_page": page,
            "last_thread_id": thread_id,
            "last_crawl_time": datetime.now().isoformat(),
            "status": "running",
            **stats
        }
        
        # 1. Redis（实时）
        storage.redis_client.hset(self.checkpoint_key, mapping=checkpoint)
        
        # 2. MongoDB（定期同步，每10个检查点同步一次）
        if page % 10 == 0:
            storage.save_checkpoint(checkpoint)
        
        # 3. 本地文件（每100个检查点备份一次）
        if page % 100 == 0:
            self._save_to_file(checkpoint)
    
    async def load_checkpoint(self) -> Optional[dict]:
        """加载检查点（优先级：Redis > MongoDB > 本地文件）"""
        # 1. 尝试从Redis加载
        checkpoint = storage.redis_client.hgetall(self.checkpoint_key)
        if checkpoint:
            return checkpoint
        
        # 2. 尝试从MongoDB加载
        checkpoint = storage.load_checkpoint(self.site, self.board)
        if checkpoint:
            # 恢复到Redis
            storage.redis_client.hset(self.checkpoint_key, mapping=checkpoint)
            return checkpoint
        
        # 3. 尝试从本地文件加载
        if self.backup_file.exists():
            checkpoint = json.loads(self.backup_file.read_text())
            # 恢复到Redis和MongoDB
            storage.redis_client.hset(self.checkpoint_key, mapping=checkpoint)
            storage.save_checkpoint(checkpoint)
            return checkpoint
        
        return None
    
    def mark_completed(self):
        """标记任务完成"""
        checkpoint = self.load_checkpoint()
        checkpoint['status'] = 'completed'
        checkpoint['completed_at'] = datetime.now().isoformat()
        self.save_checkpoint(**checkpoint)
```

### 2.3 实现方案

#### 修改 `spiders/bbs_spider.py`

```python
class BBSSpider(BaseSpider):
    def __init__(self, ...):
        # ... 现有代码 ...
        self.checkpoint_manager = CheckpointManager(
            site=self.config.bbs.base_url,
            board=board_name
        )
    
    async def crawl_board(self, board_url: str, board_name: str, max_pages: Optional[int] = None):
        """爬取板块（支持断点续传）"""
        # 1. 加载检查点
        checkpoint = await self.checkpoint_manager.load_checkpoint()
        start_page = checkpoint['current_page'] if checkpoint else 1
        
        if checkpoint:
            logger.info(f"🔄 从检查点恢复: 第 {start_page} 页")
        
        # 2. 从检查点位置继续爬取
        page_count = 0
        current_url = board_url
        
        for page in range(start_page, max_pages or float('inf')):
            # ... 爬取逻辑 ...
            
            # 3. 每爬取一页，保存检查点
            await self.checkpoint_manager.save_checkpoint(
                page=page,
                thread_id=last_thread_id,
                stats={
                    "crawled_count": self.stats['threads_crawled'],
                    "failed_count": self.stats['images_failed']
                }
            )
            
            # 4. 检查是否有下一页
            next_url = self.parser.find_next_page(html, current_url)
            if not next_url:
                break
            
            current_url = next_url
            page_count += 1
        
        # 5. 标记完成
        self.checkpoint_manager.mark_completed()
```

### 2.4 使用示例

```bash
# 第一次运行（从头开始）
python spider.py crawl-board "https://sxd.xd.com/" --config xindong

# 中断后，再次运行（自动从检查点恢复）
python spider.py crawl-board "https://sxd.xd.com/" --config xindong
# 输出: 🔄 从检查点恢复: 第 15 页

# 手动指定起始页（覆盖检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config xindong --start-page 20
```

---

## 3. 问题2：性能优化

### 3.1 当前性能瓶颈

| 瓶颈 | 当前值 | 优化目标 |
|------|--------|---------|
| 并发数 | 5 | 10-20 |
| 请求延迟 | 1.0秒 | 0.3-0.5秒（智能延迟） |
| 图片下载 | 串行 | 批量并发 |
| 数据库写入 | 逐条 | 批量写入 |

### 3.2 优化策略

#### 策略1：智能并发控制

```python
class AdaptiveConcurrencyController:
    """自适应并发控制器"""
    
    def __init__(self, initial_concurrent=5, max_concurrent=20):
        self.current_concurrent = initial_concurrent
        self.max_concurrent = max_concurrent
        self.min_concurrent = 1
        self.error_rate = 0.0
        self.success_count = 0
        self.error_count = 0
    
    def adjust_concurrency(self):
        """根据错误率调整并发数"""
        total = self.success_count + self.error_count
        if total == 0:
            return
        
        self.error_rate = self.error_count / total
        
        if self.error_rate > 0.1:  # 错误率>10%，降低并发
            self.current_concurrent = max(
                self.min_concurrent,
                int(self.current_concurrent * 0.8)
            )
        elif self.error_rate < 0.01:  # 错误率<1%，提高并发
            self.current_concurrent = min(
                self.max_concurrent,
                int(self.current_concurrent * 1.2)
            )
        
        logger.info(f"📊 并发数调整: {self.current_concurrent} (错误率: {self.error_rate:.2%})")
```

#### 策略2：批量数据库写入

```python
class BatchStorage:
    """批量存储管理器"""
    
    def __init__(self, batch_size=100):
        self.batch_size = batch_size
        self.thread_buffer = []
        self.image_buffer = []
    
    async def save_thread_batch(self, thread_data: dict):
        """批量保存帖子"""
        self.thread_buffer.append(thread_data)
        
        if len(self.thread_buffer) >= self.batch_size:
            await self._flush_threads()
    
    async def _flush_threads(self):
        """刷新帖子缓冲区"""
        if not self.thread_buffer:
            return
        
        try:
            collection = storage.mongo_db['threads']
            # 批量插入（使用 insert_many + upsert）
            operations = [
                UpdateOne(
                    {'thread_id': t['thread_id']},
                    {'$set': t},
                    upsert=True
                )
                for t in self.thread_buffer
            ]
            collection.bulk_write(operations)
            
            logger.info(f"💾 批量保存 {len(self.thread_buffer)} 条帖子")
            self.thread_buffer.clear()
        except Exception as e:
            logger.error(f"批量保存失败: {e}")
    
    async def flush_all(self):
        """刷新所有缓冲区"""
        await self._flush_threads()
        await self._flush_images()
```

#### 策略3：连接池优化

```python
# 在 BaseSpider 中优化 HTTP 连接
class BaseSpider:
    def __init__(self, config):
        # 使用连接池，复用连接
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(
                limit=100,  # 连接池大小
                limit_per_host=20,  # 每个主机最大连接数
                ttl_dns_cache=300,  # DNS缓存时间
                force_close=False,  # 保持连接
            ),
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': self._get_user_agent()}
        )
```

#### 策略4：异步任务队列

```python
# 使用 asyncio.Queue 实现生产者-消费者模式
class CrawlQueue:
    """爬取任务队列"""
    
    def __init__(self, max_workers=10):
        self.queue = asyncio.Queue(maxsize=1000)
        self.max_workers = max_workers
    
    async def producer(self, urls: List[str]):
        """生产者：添加URL到队列"""
        for url in urls:
            await self.queue.put(url)
    
    async def consumer(self, spider: BBSSpider):
        """消费者：从队列取URL并爬取"""
        while True:
            try:
                url = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await spider.crawl_thread(url)
                self.queue.task_done()
            except asyncio.TimeoutError:
                break
    
    async def run(self, urls: List[str], spider: BBSSpider):
        """运行爬取任务"""
        # 启动生产者
        producer_task = asyncio.create_task(self.producer(urls))
        
        # 启动多个消费者（并发）
        consumer_tasks = [
            asyncio.create_task(self.consumer(spider))
            for _ in range(self.max_workers)
        ]
        
        await producer_task
        await self.queue.join()  # 等待所有任务完成
        
        # 取消消费者
        for task in consumer_tasks:
            task.cancel()
```

### 3.3 性能优化效果预估

| 优化项 | 优化前 | 优化后 | 提升 |
|--------|--------|--------|------|
| 并发数 | 5 | 15 | 3x |
| 请求延迟 | 1.0s | 0.4s | 2.5x |
| 数据库写入 | 逐条 | 批量100条 | 10x |
| **总体速度** | **150图/分** | **500+图/分** | **3.3x** |

---

## 4. 问题3：反封禁策略

### 4.1 封禁风险分析

| 风险 | 触发条件 | 影响 |
|------|----------|------|
| IP封禁 | 请求频率过高 | 🔴 严重 |
| 账号封禁 | 异常行为模式 | 🔴 严重 |
| 验证码 | 频繁请求 | 🟡 中等 |
| 限流 | 超过QPS限制 | 🟡 中等 |

### 4.2 反封禁架构设计

#### 策略1：智能延迟（Human-like Behavior）

```python
class HumanLikeDelay:
    """人类行为模拟延迟"""
    
    def __init__(self, base_delay=1.0):
        self.base_delay = base_delay
        self.last_request_time = 0
    
    async def wait(self):
        """智能延迟（模拟人类行为）"""
        # 基础延迟 + 随机抖动（±30%）
        delay = self.base_delay * (1 + random.uniform(-0.3, 0.3))
        
        # 考虑时间间隔（如果距离上次请求>5秒，减少延迟）
        time_since_last = time.time() - self.last_request_time
        if time_since_last > 5:
            delay *= 0.5
        
        # 夜间降低延迟（假设服务器压力小）
        hour = datetime.now().hour
        if 2 <= hour <= 6:
            delay *= 0.7
        
        await asyncio.sleep(delay)
        self.last_request_time = time.time()
```

#### 策略2：User-Agent轮换

```python
class UserAgentRotator:
    """User-Agent轮换器"""
    
    def __init__(self):
        self.ua_generator = UserAgent()
        self.ua_list = [
            # Chrome
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            # Firefox
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101',
            # Safari
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Version/17.0 Safari/605.1.15',
        ]
        self.current_index = 0
    
    def get_ua(self) -> str:
        """获取下一个UA"""
        ua = self.ua_list[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.ua_list)
        return ua
    
    def get_random_ua(self) -> str:
        """获取随机UA"""
        return random.choice(self.ua_list)
```

#### 策略3：请求频率控制

```python
class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self, max_requests_per_minute=60):
        self.max_rpm = max_requests_per_minute
        self.request_times = deque(maxlen=max_requests_per_minute)
    
    async def acquire(self):
        """获取请求许可"""
        now = time.time()
        
        # 移除1分钟前的记录
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()
        
        # 如果超过限制，等待
        if len(self.request_times) >= self.max_rpm:
            wait_time = 60 - (now - self.request_times[0])
            logger.warning(f"⏳ 频率限制，等待 {wait_time:.1f} 秒")
            await asyncio.sleep(wait_time)
            return await self.acquire()
        
        self.request_times.append(now)
```

#### 策略4：代理池（可选）

```python
class ProxyPool:
    """代理池管理器"""
    
    def __init__(self, proxy_list: List[str]):
        self.proxies = proxy_list
        self.current_index = 0
        self.failed_proxies = set()
    
    def get_proxy(self) -> Optional[str]:
        """获取可用代理"""
        if not self.proxies:
            return None
        
        # 轮询代理
        for _ in range(len(self.proxies)):
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            
            if proxy not in self.failed_proxies:
                return proxy
        
        # 所有代理都失败，重置
        logger.warning("⚠️  所有代理都失败，重置代理池")
        self.failed_proxies.clear()
        return self.proxies[0]
    
    def mark_failed(self, proxy: str):
        """标记代理失败"""
        self.failed_proxies.add(proxy)
        logger.warning(f"❌ 代理失败: {proxy}")
```

#### 策略5：错误处理与降级

```python
class AntiBanManager:
    """反封禁管理器"""
    
    def __init__(self):
        self.consecutive_errors = 0
        self.last_error_time = 0
    
    async def handle_error(self, error: Exception):
        """处理错误，自动降级"""
        self.consecutive_errors += 1
        self.last_error_time = time.time()
        
        # 连续错误>5次，触发降级
        if self.consecutive_errors > 5:
            logger.error("🚨 连续错误过多，触发降级策略")
            await self._degrade()
    
    async def _degrade(self):
        """降级策略"""
        # 1. 增加延迟
        config.crawler.download_delay *= 2
        
        # 2. 减少并发
        config.crawler.max_concurrent_requests = max(1, config.crawler.max_concurrent_requests // 2)
        
        # 3. 等待一段时间
        wait_time = min(300, self.consecutive_errors * 60)  # 最多等待5分钟
        logger.info(f"⏸️  降级等待 {wait_time} 秒")
        await asyncio.sleep(wait_time)
        
        # 4. 重置错误计数
        self.consecutive_errors = 0
```

### 4.3 反封禁配置建议

针对 https://sxd.xd.com/ 的推荐配置：

```python
# configs/sxd.json
{
    "crawler": {
        "max_concurrent_requests": 3,      # 保守并发数
        "download_delay": 2.0,             # 2秒延迟（安全）
        "request_timeout": 30,
        "max_retries": 3,
        "rotate_user_agent": true,
        "use_proxy": false                 # 如果被封，启用代理
    },
    "anti_ban": {
        "max_requests_per_minute": 30,     # 每分钟最多30请求
        "human_like_delay": true,          # 启用人类行为模拟
        "error_threshold": 5,              # 错误阈值
        "degrade_on_error": true           # 错误时自动降级
    }
}
```

---

## 5. 综合实施方案

### 5.1 优先级排序

| 优先级 | 功能 | 预计工作量 | 影响 |
|--------|------|-----------|------|
| P0 | 断点续传（检查点） | 2天 | 🔴 关键 |
| P0 | 批量数据库写入 | 1天 | 🔴 关键 |
| P1 | 智能延迟 | 1天 | 🟡 重要 |
| P1 | 自适应并发 | 2天 | 🟡 重要 |
| P2 | 代理池 | 3天 | 🟢 可选 |
| P2 | 错误降级 | 1天 | 🟢 可选 |

### 5.2 实施步骤

**阶段1：断点续传（1周）**
1. 实现 `CheckpointManager` 类
2. 修改 `crawl_board()` 支持检查点
3. 添加 CLI 参数 `--resume` / `--start-page`
4. 测试验证

**阶段2：性能优化（1周）**
1. 实现批量数据库写入
2. 优化连接池配置
3. 实现自适应并发控制
4. 性能测试

**阶段3：反封禁（1周）**
1. 实现智能延迟
2. 实现频率限制器
3. 实现错误降级
4. 压力测试

### 5.3 使用示例

```bash
# 1. 首次运行（自动保存检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config sxd

# 2. 中断后恢复（自动从检查点继续）
python spider.py crawl-board "https://sxd.xd.com/" --config sxd --resume

# 3. 指定起始页（覆盖检查点）
python spider.py crawl-board "https://sxd.xd.com/" --config sxd --start-page 50

# 4. 查看检查点状态
python spider.py checkpoint-status --site sxd.xd.com
```

---

## 6. 风险评估

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|---------|
| 检查点丢失 | 低 | 中 | 三级存储（Redis+MongoDB+文件） |
| 性能优化过度 | 中 | 高 | 自适应并发，自动降级 |
| 被封禁 | 中 | 高 | 智能延迟，频率限制，代理池 |
| 数据不一致 | 低 | 中 | 事务处理，幂等性设计 |

---

## 7. 审批

| 角色 | 姓名 | 意见 | 日期 |
|------|------|------|------|
| 架构师 | Chang | 待审批 | - |

---

## 8. 参考资料

- [Redis 持久化](https://redis.io/docs/management/persistence/)
- [MongoDB 批量操作](https://www.mongodb.com/docs/manual/core/bulk-write-operations/)
- [aiohttp 连接池](https://docs.aiohttp.org/en/stable/client_reference.html#aiohttp.ClientSession)
