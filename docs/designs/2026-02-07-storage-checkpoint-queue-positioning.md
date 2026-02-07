# 设计讨论：MongoDB/Redis 与 Checkpoint、生产消费队列的定位与重叠

**文档类型**: 设计讨论（先讨论清楚设计，不涉及代码实现）  
**日期**: 2026-02-07  
**角色**: 架构师视角  

---

## 1. 文档目的

在决定技术选型（如是否用 SQLite 替代 MongoDB/Redis）或做组件整合（如 Checkpoint 是否基于 Storage）之前，先把**各存储/队列组件的设计定位**说清楚，并分析**是否存在职责重叠**，避免「多套存储、多套队列、多套去重」带来的概念混乱和实现冗余。

---

## 2. 当前（或原设计）各组件的定位

以下按「在架构里承担的角色」来定义，不绑定具体技术（MongoDB/Redis 只是实现手段）。

### 2.1 MongoDB 的定位

在原架构文档与实现中，MongoDB 被用来：

- **持久化爬取结果**  
  - 帖子元数据：thread_id、title、url、board、images、metadata、created_at 等（threads 集合）。  
  - 图片记录：url、save_path、file_size、success、metadata、created_at 等（images 集合）。  
- **基于结果的统计查询**  
  - 总帖子数、总图片数、成功/失败数、按板块聚合等（get_statistics）。  
- **「已爬帖子」的权威判断**  
  - 通过 `thread_exists(thread_id)` 判断某帖是否已爬过并入库，用于去重与跳过。

**一句话**：MongoDB 是「爬取结果 + 基于结果的统计」的**唯一持久化层**，也是「帖子级是否已处理」的**权威数据源**。

---

### 2.2 Redis 的定位

在原架构与实现中，Redis 被用来：

- **URL 级「已访问」集合（visited_urls）**  
  - 用 Set 存「已访问过的 URL」，做 O(1) 存在性判断。  
  - 用途：避免同一 URL 被重复抓取（与「帖子是否已爬」不同：一个帖子页可能对应多条 URL，如列表页、详情页）。  
- **任务队列（List）**  
  - `add_to_queue` / `get_from_queue`（含 blpop 阻塞消费）、`get_queue_size`、`clear_queue`。  
  - 设计上可做「待爬 URL/任务」的持久化队列，支持跨进程/跨重启消费。

**一句话**：Redis 同时承担「URL 级已访问标记」和「（可持久化的）任务队列」两种能力。

---

### 2.3 Checkpoint（CheckpointManager）的定位

在原实现中，Checkpoint 使用**本地 JSON 文件**（如 `checkpoints/{site}_{board}.json`），负责：

- **单次爬取任务的进度**  
  - 当前页码（current_page）、最后爬取的帖子 ID/URL（last_thread_id、last_thread_url）。  
- **任务状态**  
  - status：running / completed / error。  
- **本次任务内的「已处理」信息**  
  - seen_article_ids：已爬取的文章 ID 列表（用于动态新闻等场景的恢复后去重）。  
  - min_article_id / max_article_id：用于正序/倒序分页的边界。  
- **本次任务的统计快照**  
  - stats：如 crawled_count、images_downloaded 等，随进度一起保存，用于断点恢复后展示或累计。

**一句话**：Checkpoint 是「单次任务的进度与运行期状态」的持久化，用于**断点续传**和**恢复后不重复下发**，不负责长期结果存储。

---

### 2.4 生产消费队列（CrawlQueue）的定位

在当前实现中，CrawlQueue 使用**内存中的 asyncio.Queue**：

- **单次运行内的任务调度**  
  - 生产者把待爬 URL/thread_info 放入队列，多个 worker 并发从队列取任务并执行。  
- **不持久化**  
  - 进程结束队列即清空；不支持跨进程、跨重启消费。

**一句话**：CrawlQueue 是「本次进程内」的**内存任务队列**，只做调度，不做持久化。

---

## 3. 重叠分析

### 3.1 「已处理条目」的重叠

| 能力           | 谁提供           | 粒度     | 持久化 | 用途                     |
|----------------|------------------|----------|--------|--------------------------|
| 帖子是否已爬   | MongoDB（Storage） | 帖子 ID  | 是     | 权威去重、跳过已爬帖子   |
| URL 是否已访问 | Redis            | URL      | 是     | URL 级去重               |
| 文章 ID 是否已爬（本次任务） | Checkpoint       | 文章 ID  | 是（JSON） | 断点恢复后不重复下发     |

- **重叠点**：  
  - 「已处理」既可以用「结果库里有没有」（MongoDB thread_exists）表达，也可以用「进度里记一笔」（Checkpoint seen_article_ids）表达。  
  - Redis 的 visited_urls 与 Checkpoint 的 seen_article_ids 在**概念上**都是「已处理标识集合」，只是粒度不同（URL vs 文章 ID）和生命周期不同（Redis 可长期 vs Checkpoint 按任务）。  
- **当前实现事实**：  
  - BBS 爬虫实际只用 Storage.thread_exists 做帖子级去重，**没有**使用 Storage 的 is_url_visited / mark_url_visited。  
  - 动态新闻用 Checkpoint 的 seen_article_ids 做「本次任务内」去重。  
- **结论**：  
  - 设计上存在「多套已处理标识」的潜在重叠；若未来启用 Redis visited_urls，就需要在架构上明确：**帖子级权威 = Storage，URL/文章级 = 谁主、谁辅、是否合并到同一存储**，否则容易双写或口径不一致。

---

### 3.2 「任务队列」的重叠

| 能力     | 谁提供    | 持久化 | 使用方           |
|----------|-----------|--------|------------------|
| 待爬任务队列 | Redis（Storage） | 是     | 当前代码未使用   |
| 待爬任务队列 | CrawlQueue | 否（内存） | 爬虫实际使用     |

- **重叠点**：  
  - 两处都能表达「待爬任务列表」：Redis 的 List 可做持久化队列，CrawlQueue 的 asyncio.Queue 做进程内队列。  
  - 若将来用 Redis 做跨进程/持久化队列，则「任务从哪来、从哪取」会与 CrawlQueue 的职责重叠，需要约定：**谁负责生产、谁负责消费、队列的唯一出口/入口是谁**。  
- **当前实现事实**：  
  - 爬虫只使用 CrawlQueue（内存），没有调用 Storage.add_to_queue / get_from_queue。  
- **结论**：  
  - **设计上**存在「双队列」的重叠；**实现上**目前只有 CrawlQueue 在用，Storage 的队列是预留能力，容易造成「到底用哪套队列」的困惑。

---

### 3.3 「统计」的轻度重叠

| 能力     | 谁提供           | 内容                         |
|----------|------------------|------------------------------|
| 全局统计 | MongoDB（Storage） | 总帖子/图片、成功失败、按板块 |
| 本次任务统计 | Checkpoint       | stats 快照（crawled_count 等）|

- **重叠点**：  
  - 都是「统计」，但目标不同：Storage 是长期累计事实，Checkpoint 是单次任务进度的一部分。  
  - 若业务上把「本次任务统计」最终汇总进 Storage，就存在「统计写两处」的边界问题；若只写 Checkpoint，则与 Storage 的统计是互补而非重复。  
- **结论**：  
  - 重叠较轻，主要需约定：**本次任务 stats 的归属与是否回写 Storage**，避免双写或口径不一致。

---

## 4. 小结：定位是否重叠？

- **MongoDB**：定位清晰，即「结果 + 统计 + 帖子级权威去重」；与 Checkpoint 不重叠（Checkpoint 不存结果），与队列不重叠。  
- **Redis**：  
  - **visited_urls** 与 Checkpoint 的 **seen_article_ids** 在「已处理标识集合」上有概念重叠；当前实现上未同时使用，但设计上应明确「谁主、谁辅、是否统一到同一存储」。  
  - **任务队列** 与 **CrawlQueue** 在「待爬任务列表」上重叠；当前只有 CrawlQueue 在用，Storage 的队列是预留，需在设计中明确「持久化队列由谁提供、是否保留 Storage 队列接口」。  
- **Checkpoint**：定位是「进度 + 本次任务状态」；与 MongoDB 的「结果」不重叠，但与 Redis 的「已处理集合」有概念重叠，与「统计快照」和 Storage 的统计有轻度边界问题。  
- **CrawlQueue**：定位是「本次运行内的内存任务队列」；与 Redis 的「持久化任务队列」在设计上重叠，实现上目前只用了 CrawlQueue。

因此，**从设计上看，确实存在重叠**：主要是（1）已处理条目的多套标识（Redis vs Checkpoint），（2）任务队列的双轨（Redis vs CrawlQueue），（3）统计的归属与是否双写。讨论清楚这些，再决定「是否用 SQLite 替代 MongoDB/Redis」「Checkpoint 是否基于 Storage」「是否保留/移除 Redis 队列与 visited_urls」等实现方案，会更稳。  
**改造范围**：上述收敛与 Storage/Checkpoint 改造需同时覆盖 **BBSSpider** 与 **DynamicNewsCrawler**；后者当前未接入 Storage，需一并纳入（见 **§7**）。

---

## 5. 建议的收敛方向（供讨论）

以下仅为架构层面的收敛建议，不写代码，仅作讨论输入：

1. **单一持久化层**  
   - 结果（threads/images）+ 进度（checkpoints）+ 统计（基于结果与进度计算）统一到一个存储（如 SQLite），避免「结果在 MongoDB、进度在 JSON」的双轨。  
   - Checkpoint 变为「基于该存储的薄封装」：对外 API 不变，内部只读写存储中的 checkpoints 表/集合。  
   - 具体设计要点见下文 **§6 Checkpoint 薄封装详解**。

2. **已处理条目的单一权威**  
   - 帖子级：以「结果库中是否存在该 thread」为唯一权威（thread_exists），不另存一份「已爬帖子列表」。  
   - URL/文章级：若只需「本次运行内」去重，用内存 Set 即可；若需「跨运行/跨任务」去重，可考虑纳入同一存储（如 checkpoints 表里 seen_article_ids，或单独表），避免 Redis 与 Checkpoint 各存一套。

3. **任务队列单一出口**  
   - 明确「任务队列」只由 CrawlQueue 提供；若未来需要持久化队列，单独设计（如独立服务或独立表），不与「结果/进度」混在 Storage 的 Redis 接口里。  
   - Storage 的 add_to_queue / get_from_queue 可标记为废弃或仅作兼容保留，避免与 CrawlQueue 职责混淆。

4. **统计归属**  
   - 全局统计：仅由 Storage（基于结果与进度）提供。  
   - 本次任务统计：作为 Checkpoint 进度的一部分写入同一存储；若需展示「本次任务统计」，从 Checkpoint 读即可，不必再写回结果表。

以上四点可与「是否用 SQLite + 内存结构替代 MongoDB/Redis」一起讨论，先定设计再落实现。

### 5.1 方案 B（已采纳）：Checkpoint 仅作进度与状态

- **已爬权威**：**仅由 Storage 负责**。BBS 用 `storage.thread_exists(thread_id)`，动态新闻用 `storage.article_exists(article_id)`；不再用 Checkpoint 的 seen_article_ids 作为「是否已爬」的权威依据。
- **Checkpoint 仅负责**：  
  - **进度**：current_page、last_thread_id、last_thread_url，用于「从上次页码续爬」，减少列表页重复请求。  
  - **任务状态**：status（running / completed / error），用于判断是否需重跑、是否已完成。  
  - **可选**：stats（本次任务统计快照）、seen_article_ids / min/max_article_id（仅作「本轮 + 断点恢复」的**缓存**，减少对 Storage 的查询，**非权威**）。
- **效果**：续跑从上次页开始、有任务完成/错误状态；「是否已爬」统一看 Storage，职责清晰，无重叠。

---

## 6. Checkpoint 薄封装详解（如何「基于该存储的薄封装」）

本节展开说明：当采用「单一持久化层」后，**Checkpoint 如何变成仅依赖该存储的薄封装**，而不自己维护 JSON 文件或其它持久化。

### 6.1 什么是「薄封装」

- **对外**：CheckpointManager 的公开 API 不变。调用方仍然使用 `save_checkpoint(...)`、`load_checkpoint()`、`get_current_page()`、`get_seen_article_ids()`、`mark_completed()`、`mark_error()`、`clear_checkpoint()`、`exists()` 等，无需改调用方式。
- **对内**：CheckpointManager 不再拥有自己的持久化介质（不再写 `checkpoints/{site}_{board}.json`），所有「读/写进度」都通过**存储层**完成。也就是说：
  - **写进度**：内部把当前参数组装成一条「检查点数据」字典，调用存储的「保存检查点」接口（例如 `storage.save_checkpoint(site, board, data)`）。
  - **读进度**：内部调用存储的「加载检查点」接口（例如 `storage.load_checkpoint(site, board)`），得到字典后再按需提供给 `get_current_page()`、`get_seen_article_ids()` 等方法。
- **薄** 体现在：CheckpointManager 不再解析/生成文件、不再关心存储格式（SQL 还是 JSON 还是别的），只做「参数 ↔ 存储接口」的适配和「业务语义方法 → 存储调用」的转发。

### 6.2 存储侧需要提供的能力

存储（例如 Storage，背后是 SQLite 或其它引擎）需要**单独为「进度」提供一块数据与接口**，与「结果（threads/images）」并列，而不是混在结果表里。  
**结论**：用**单独的 checkpoints 表**，不复用 threads/images。原因：进度（「爬到哪了」）与结果（「爬到了什么」）语义不同、字段不同，放在一起会混用且难以扩展；按 (site, board) 一条记录存进度，与按 thread_id 存帖子、按 url 存图片是不同维度。

1. **数据形态**  
   - 用一张表或一个集合表示「检查点」，每条记录对应**一个 (site, board)** 的进度。  
   - 建议字段（或等价结构）：site、board、current_page、last_thread_id、last_thread_url、status、stats（JSON 或序列化）、seen_article_ids（JSON 或序列化）、min_article_id、max_article_id、created_at、updated_at。  
   - 主键或唯一键为 (site, board)，保证一个站点+板块只有一条进度记录。

#### 6.2.1 SQLite 表 schema 与 checkpoint 读写约定

**整体**：SQLite 里共三张业务表，各司其职，**不复用**。

| 表名 | 用途 | 主键/唯一键 |
|------|------|-------------|
| threads | 帖子元数据（爬取结果） | thread_id |
| images | 图片记录（爬取结果） | 自增 id |
| **checkpoints** | 进度（当前页、最后帖子、状态）+ 可选缓存（seen_article_ids 等，非权威） | **(site, board)** |

**checkpoints 表 schema（建议）**：

```sql
CREATE TABLE checkpoints (
    site TEXT NOT NULL,
    board TEXT NOT NULL,
    current_page INTEGER DEFAULT 1,
    last_thread_id TEXT,
    last_thread_url TEXT,
    status TEXT DEFAULT 'running',
    stats TEXT,                  -- JSON，如 {"crawled_count": 10, "images_downloaded": 5}
    seen_article_ids TEXT,       -- JSON 数组，如 ["id1", "id2"]
    min_article_id TEXT,
    max_article_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    PRIMARY KEY (site, board)
);
```

- **save_checkpoint(site, board, data)** 读写什么：  
  - **写**：根据 `data` 写入/更新 **checkpoints 表**中 (site, board) 对应的**那一行**。  
  - 写入字段：current_page、last_thread_id、last_thread_url、status、stats（序列化为 JSON 字符串）、seen_article_ids（序列化为 JSON 字符串）、min_article_id、max_article_id、updated_at（每次保存为当前时间）；created_at 仅在该 (site, board) **首次插入**时写入，之后更新时保留原值。  
  - **不读**：save 只写不读；若需要「保留旧 created_at」，由调用方在 data 里带上或由存储层在 UPDATE 时保留 created_at 列。

- **load_checkpoint(site, board)** 读写什么：  
  - **读**：从 **checkpoints 表**中读出 (site, board) 对应的**那一行**，转成字典返回。  
  - 返回字段：site、board、current_page、last_thread_id、last_thread_url、status、last_update_time（取表中 updated_at）、stats（JSON 反序列化）、seen_article_ids（JSON 反序列化）、min_article_id、max_article_id、created_at、updated_at。  
  - **不写**：load 只读不写。  
  - 若该 (site, board) 不存在，返回 None（或等价空）。

**为何单独 checkpoints 表、不复用 threads/images**：  
- threads 表：按**帖子**维度，一条记录一个 thread_id，表示「这条帖子已爬、内容是什么」。  
- images 表：按**图片**维度，一条记录一次下载，表示「这张图已下、路径与元数据」。  
- checkpoints 表：按**(站点, 板块)**维度，一条记录表示「这个站点+板块当前爬到第几页、状态、本次任务内已见文章 ID 等」。  
- 进度与结果是不同维度、不同生命周期（进度可清空重爬，结果可长期保留），故用**单独表**更清晰；若强行复用 threads（例如在 threads 里加「当前页」列），会混淆「结果」与「进度」，且一个板块只有一条进度却有多条帖子，无法用一张表自然表达。

2. **四个基础接口（存储层实现）**  
   - **保存检查点**：`save_checkpoint(site, board, data)`。  
     - `data` 为字典，包含上述字段；若 (site, board) 已存在则更新，否则插入。  
     - 实现时需处理好 `created_at`（仅首次插入时写入，更新时保留原值）。  
   - **加载检查点**：`load_checkpoint(site, board) -> Optional[dict]`。  
     - 返回该 (site, board) 的完整检查点字典；若不存在则返回 None。  
   - **删除检查点**：`delete_checkpoint(site, board)`。  
     - 用于「清除检查点」语义。  
   - **检查点是否存在**：`checkpoint_exists(site, board) -> bool`。  
     - 用于 `CheckpointManager.exists()` 等。

3. **不要求**  
   - 存储层不需要实现「当前页」「seen_article_ids」等业务语义，只负责按 (site, board) 读写一条结构化记录即可；业务语义全部由 CheckpointManager 在「薄封装」里解释。

### 6.3 CheckpointManager 侧保留与委托关系

- **保留**  
  - 构造时仍接收 `site`、`board`（以及可选参数如 `checkpoint_dir`，仅为兼容保留，不再用于路径计算）。  
  - 对外方法保持现有语义：`get_current_page()` 返回当前页、`get_seen_article_ids()` 返回集合、`mark_completed()` 把状态改为 completed 并可选写入最终 stats，等等。  

- **委托**  
  - `save_checkpoint(current_page=..., last_thread_id=..., ...)`：  
    将参数与「是否需要保留 created_at」等逻辑整理成一条 `data`，调用 `storage.save_checkpoint(self.site, self.board, data)`。  
  - `load_checkpoint()`：  
    直接返回 `storage.load_checkpoint(self.site, self.board)` 的结果（可能为 None）。  
  - `clear_checkpoint()`：  
    调用 `storage.delete_checkpoint(self.site, self.board)`。  
  - `exists()`：  
    返回 `storage.checkpoint_exists(self.site, self.board)`。  
  - `get_current_page()`、`get_last_thread_id()`、`get_status()`、`get_stats()`、`get_seen_article_ids()`、`get_min_article_id()`、`get_max_article_id()`：  
    都先 `load_checkpoint()` 得到字典，再从字典中取对应字段返回；若有「默认值」或「集合化」（如 list → set）在此层完成。  
  - `mark_completed(final_stats=...)`、`mark_error(error_message)`：  
    先 `load_checkpoint()` 得到当前进度，再按业务规则修改 status/stats 等，最后调用 `save_checkpoint(...)` 写回。

- **不再拥有**  
  - 不再维护 `checkpoint_file` 路径、不再打开/写入/读取本地 JSON 文件；`checkpoint_file` 可保留为只读属性，仅用于展示（例如显示为 `"SQLite:<site>_<board>"`），便于日志或 CLI 提示「进度存在哪」。

### 6.4 使用约束与初始化顺序

- **依赖关系**：CheckpointManager 依赖「存储已连接、且存储实现了上述四个检查点接口」。因此：  
  - 使用 CheckpointManager 前，必须先调用 `storage.connect()`（或在应用启动/命令入口处保证存储已连接）。  
  - 若在爬虫流程中使用：通常在爬虫 `init()` 里已调用 `storage.connect()`，之后再创建 CheckpointManager 即可。  
  - 若在单独的命令中使用（例如只执行「查看/清除检查点」）：在该命令入口处显式 `storage.connect()`，并在退出前视情况 `storage.close()`，避免未连接导致 `load_checkpoint` 得到空或保存失败。

- **单进程假设**：当前设计不讨论多进程同时写同一 (site, board) 的并发控制；若未来需要多进程，再在存储层或 CheckpointManager 层加锁/乐观锁等。

### 6.5 与旧实现的对比（小结）

| 维度         | 旧实现（JSON 文件）           | 薄封装（基于存储）                     |
|--------------|-------------------------------|----------------------------------------|
| 进度存哪     | 本地文件 `checkpoints/…`      | 存储中的 checkpoints 表/集合           |
| 谁负责格式   | CheckpointManager 自己读写 JSON | 存储层负责序列化/表结构               |
| CheckpointManager 职责 | 组数据 + 写文件 + 读文件 + 业务语义 | 组数据 + 调存储接口 + 业务语义        |
| 调用方变化   | —                             | 无；API 不变                           |
| 前置条件     | 无（文件系统即可）            | 需先 `storage.connect()`              |

这样，**Checkpoint 变为「基于该存储的薄封装」** 的含义就是：进度只存一份、只从存储读写的单一数据源，CheckpointManager 只做「业务语义 ↔ 存储接口」的薄薄一层适配，不再承担「另一种持久化（JSON 文件）」的职责，从而与「单一持久化层」的设计一致。

---

## 7. DynamicNewsCrawler 的改造（接入 Storage）

当前 **DynamicNewsCrawler** 未接入 `core/storage.py`，仅使用 CheckpointManager 做进度；需纳入同一套「单一持久化层 + Checkpoint 薄封装」设计，与 BBSSpider 一致。

### 7.1 当前状态

| 维度 | 现状 |
|------|------|
| **Storage** | 未导入、未调用；无 `storage.connect()` / `storage.close()`。 |
| **进度** | 仅用 `CheckpointManager(site, board="news")`：save_checkpoint、load_checkpoint、seen_article_ids、min/max_article_id、stats 等。若 CheckpointManager 改为基于 Storage，则必须先 `storage.connect()` 再使用，否则 checkpoint 读写会失败。 |
| **结果持久化** | 无。爬取到的文章列表/详情只存在于内存（`all_articles`）和检查点里的 `seen_article_ids`；没有「文章记录」写入 Storage。 |
| **「已爬文章」判断** | 仅依赖 Checkpoint 的 `seen_article_ids`（本次任务 + 断点恢复）；没有类似 BBS 的 `thread_exists(thread_id)` 的**长期权威**来源。 |

因此：动态新闻爬虫与 BBS 爬虫在「存储/进度」上不一致，且一旦 Checkpoint 改为基于 Storage，DynamicNewsCrawler 必须显式连接 Storage，否则检查点无法工作。

### 7.2 改造目标

- 与 **§2.3 / §6** 的设计一致：进度统一存 Storage 的 checkpoints 表，CheckpointManager 为薄封装；使用 CheckpointManager 前必须先 `storage.connect()`。
- DynamicNewsCrawler 在**初始化时连接 Storage**、**关闭时关闭 Storage**，并在爬取流程中照常使用 CheckpointManager（无需改 CheckpointManager 的调用方式）。

### 7.3 必须改造项

1. **在 `DynamicNewsCrawler.init()` 中**  
   - 调用 `storage.connect()`（与 BBSSpider 一致），保证后续创建的 CheckpointManager 能通过 Storage 读写 checkpoints 表。

2. **在 `DynamicNewsCrawler.close()` 中**  
   - 调用 `storage.close()`，释放连接。

3. **不要求改 CheckpointManager 的用法**  
   - 仍使用 `CheckpointManager(site=site, board="news")` 及 save_checkpoint、load_checkpoint、get_seen_article_ids 等；只要在**第一次使用 checkpoint 之前**已执行过 `storage.connect()` 即可（init 中完成）。

完成以上三点后，DynamicNewsCrawler 即「接入 Storage」：进度与 BBS 共用同一套 Storage（如 SQLite）和 checkpoints 表，CheckpointManager 薄封装可正常生效。

### 7.4 可选改造项（结果持久化与「已爬文章」权威）

若希望动态新闻也具备「已爬文章」的**长期权威**（跨任务、跨重启的跳过），可与 BBS 的 thread 设计对称地扩展 Storage：

- **Storage 增加**（可选）：  
  - 表：`articles`（或与业务约定命名），字段至少包含：article_id、url、title、site、board、详情/图片等元数据、created_at。  
  - 接口：`article_exists(article_id)`、`save_article(article_data)`；必要时 `get_article(article_id)`。  
- **DynamicNewsCrawler 中**（可选）：  
  - 在「决定是否爬该文章」时，先查 `storage.article_exists(article_id)`；若已存在则跳过（与 BBS 的 thread_exists 一致）。  
  - 爬取成功后调用 `storage.save_article(...)`，便于下次运行直接跳过。  
  - 此时 Checkpoint 的 `seen_article_ids` 仍可用于「本次任务内 + 断点恢复」的快速去重，与「长期权威」可并存（先查 article_exists，再查 seen_article_ids 亦可）。

若暂不做结果持久化，仅完成 **§7.3** 的必须改造，即可满足「接入 Storage、Checkpoint 基于存储」的设计要求；「已爬文章」仍仅由 Checkpoint 的 seen_article_ids 提供（本次 + 恢复），无跨任务长期权威。

### 7.5 小结

| 改造项 | 必须/可选 | 说明 |
|--------|-----------|------|
| init 中 `storage.connect()` | 必须 | 使 CheckpointManager（薄封装）能读写 checkpoints 表。 |
| close 中 `storage.close()` | 必须 | 与 BBSSpider 一致，释放连接。 |
| Storage 增加 articles 表 + article_exists / save_article | 已实施 | 提供「已爬文章」长期权威，与 BBS 的 thread_exists / save_thread 对称。 |
| 爬取前 article_exists、发现新文章后 save_article | 已实施 | 与 BBS 统一：**已爬判断以 Storage 为权威**，Checkpoint 的 seen_article_ids 仅作本轮+断点恢复的集合。 |

### 7.6 已爬判断统一（与 BBS 一致）

- **BBS**：`storage.thread_exists(thread_id)` → 已爬则跳过；爬完后 `storage.save_thread(thread_data)`。
- **动态新闻**：`storage.article_exists(article_id)` → 已爬则跳过；发现新文章后 `storage.save_article({...article, site, board: "news"})`。
- **Checkpoint.seen_article_ids**：仍用于「本轮 + 断点恢复」的快速去重（避免每篇都先查 Storage）；若 Storage 已存在则跳过并同步加入 seen_article_ids，逻辑与 BBS 的「Storage 为权威」一致。

将以上内容纳入同一设计文档（本文），与 BBS 的 storage/checkpoint 改造一起评审与实施即可。

---

**文档状态**: 设计讨论稿，供评审与定稿后指导后续实现。
