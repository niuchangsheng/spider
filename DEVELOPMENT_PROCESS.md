# 开发流程规范

**版本**: v1.0  
**发布日期**: 2026-02-03  
**适用范围**: 所有开发人员  
**强制执行**: ✅ 必须遵守

---

## 🎯 核心原则

###  **设计先行原则**

> **所有代码变更必须先更新设计文档，再编写代码。**

**禁止事项**：
- ❌ 直接修改代码without设计文档
- ❌ 先写代码再补文档
- ❌ 口头约定without文档记录

**必须做**：
- ✅ 先在ARCHITECTURE.md中更新设计
- ✅ 设计评审通过后再编码
- ✅ 代码与文档保持同步

---

## 📋 标准开发流程

### 流程图

```
需求分析
    ↓
①设计文档更新 ← 【必须第一步】
    ↓
设计评审（强制）
    ↓
②编写代码
    ↓
③代码审查（强制）
    ↓
④测试验证（强制）
    ↓
⑤文档完善
    ↓
发布上线
```

---

## 1️⃣ 设计文档更新（必须第一步）

### 1.1 何时需要更新设计文档？

#### 必须更新的情况：
- ✅ 添加新功能或模块
- ✅ 修改现有模块的接口
- ✅ 改变数据流程或架构
- ✅ 性能优化方案
- ✅ 安全性改进
- ✅ 数据模型变更

#### 可以跳过的情况：
- 📝 仅修复typo或注释
- 📝 代码格式调整
- 📝 日志信息优化

### 1.2 设计文档更新流程

#### Step 1: 创建设计变更提案

在 `docs/designs/` 目录创建设计文档：

```bash
# 文件命名规范
docs/designs/YYYY-MM-DD-功能简述.md

# 示例
docs/designs/2026-02-03-add-proxy-pool.md
docs/designs/2026-02-04-optimize-image-dedup.md
```

#### Step 2: 设计文档模板

```markdown
# 设计变更提案

## 基本信息
- **标题**: [功能名称]
- **提出人**: [姓名]
- **日期**: [YYYY-MM-DD]
- **状态**: [草稿/评审中/已批准/已实施]
- **关联Issue**: #[issue编号]

## 1. 变更概述
简述要做什么变更，为什么需要这个变更。

## 2. 现状分析
当前的设计是怎样的？存在什么问题？

## 3. 设计方案

### 3.1 架构变更
如果涉及架构变更，画出变更前后的架构图。

### 3.2 接口设计
```python
# 新增/修改的接口
class NewFeature:
    def new_method(self, param: str) -> Dict:
        """接口说明"""
        pass
```

### 3.3 数据模型
如有数据模型变更，说明新旧模型。

### 3.4 流程设计
如有流程变更，画出流程图。

## 4. 技术方案

### 4.1 核心算法
说明关键算法逻辑。

### 4.2 依赖变更
新增/移除哪些依赖？

### 4.3 配置变更
需要哪些新配置项？

## 5. 影响分析

### 5.1 性能影响
- 预期性能提升/下降: XX%
- 内存占用变化: XX MB
- 并发能力变化: XX

### 5.2 兼容性影响
- [ ] 向后兼容
- [ ] 需要迁移
- [ ] Breaking Change

### 5.3 安全性影响
是否引入新的安全风险？如何规避？

## 6. 实施计划

### 6.1 开发任务
- [ ] 任务1: XXX (预计: 2小时)
- [ ] 任务2: YYY (预计: 4小时)

### 6.2 测试计划
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能测试

### 6.3 文档计划
- [ ] 更新ARCHITECTURE.md
- [ ] 更新API文档
- [ ] 更新用户文档

## 7. 风险与对策
列出可能的风险及应对措施。

## 8. 评审意见

| 评审人 | 角色 | 意见 | 日期 |
|--------|------|------|------|
| - | 架构师 | - | - |
| - | Tech Lead | - | - |

## 9. 决策
- [ ] 批准实施
- [ ] 需要修改
- [ ] 拒绝

## 10. 实施记录
- 开始日期: YYYY-MM-DD
- 完成日期: YYYY-MM-DD
- 实施人: XXX
```

#### Step 3: 提交设计评审

```bash
# 1. 创建feature分支
git checkout -b feature/proxy-pool

# 2. 添加设计文档
git add docs/designs/2026-02-03-add-proxy-pool.md

# 3. 提交
git commit -m "docs: 添加代理池设计文档"

# 4. 推送并创建PR
git push origin feature/proxy-pool

# 5. 创建Pull Request，标记为 [DESIGN REVIEW]
```

#### Step 4: 设计评审会议

**评审参与者**:
- 必须: 架构师
- 必须: Tech Lead
- 可选: 相关开发人员
- 可选: QA负责人

**评审检查项**:
- [ ] 设计是否完整？
- [ ] 接口定义是否清晰？
- [ ] 性能影响是否可接受？
- [ ] 安全性是否考虑？
- [ ] 是否符合现有架构？
- [ ] 是否遵循SOLID原则？
- [ ] 测试计划是否完善？

**评审结果**:
- ✅ **批准**: 可以开始编码
- 🔄 **需修改**: 修改后重新评审
- ❌ **拒绝**: 说明理由，关闭提案

#### Step 5: 更新ARCHITECTURE.md

设计评审通过后，将设计内容同步到 `ARCHITECTURE.md`：

```bash
# 更新主架构文档
vim ARCHITECTURE.md

# 在相应章节添加新设计
# 更新版本历史

git add ARCHITECTURE.md
git commit -m "docs: 更新架构文档 - 添加代理池设计"
```

---

## 2️⃣ 编写代码

### 2.1 编码规范

#### 命名规范
```python
# 类名: 大驼峰
class ImageDownloader:
    pass

# 函数名: 小写+下划线
def download_image():
    pass

# 常量: 全大写
MAX_RETRY_COUNT = 3

# 私有方法: 下划线前缀
def _internal_method():
    pass
```

#### 类型注解（强制）
```python
# 必须添加类型注解
def process_data(
    url: str, 
    options: Optional[Dict[str, Any]] = None
) -> Tuple[bool, str]:
    """
    处理数据
    
    Args:
        url: 数据URL
        options: 可选配置
        
    Returns:
        (成功标志, 结果消息)
    """
    pass
```

#### 文档字符串（强制）
```python
class Spider:
    """
    爬虫基类
    
    提供通用的爬虫功能，包括：
    - 页面获取
    - 内容解析
    - 数据存储
    
    Attributes:
        config: 配置对象
        session: HTTP会话
    
    Examples:
        >>> spider = Spider(config)
        >>> await spider.crawl("https://example.com")
    """
    
    def crawl(self, url: str) -> Dict:
        """
        爬取指定URL
        
        Args:
            url: 目标URL
            
        Returns:
            爬取结果字典
            
        Raises:
            ValueError: URL格式错误
            NetworkError: 网络请求失败
        """
        pass
```

#### 错误处理
```python
# 必须处理异常
try:
    result = await dangerous_operation()
except SpecificError as e:
    logger.error(f"Specific error: {e}")
    # 特定处理逻辑
except Exception as e:
    logger.exception("Unexpected error")
    # 通用处理
finally:
    # 资源清理
    await cleanup()
```

#### 日志记录
```python
# 使用结构化日志
logger.info(f"Starting download: {url}")
logger.debug(f"Config: {config}")
logger.warning(f"Retry attempt {retry_count}")
logger.error(f"Download failed: {error}")
```

### 2.2 代码提交规范

#### Commit Message格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档变更
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具变更

**示例**:
```bash
feat(downloader): 添加代理池支持

- 实现代理池管理类
- 支持自动切换代理
- 添加代理健康检查

Closes #123
```

#### Commit原则
- 一个commit只做一件事
- commit message清晰描述改动
- 关联相应的issue编号
- 频繁commit，避免大量改动

---

## 3️⃣ 代码审查（强制）

### 3.1 代码审查流程

#### Step 1: 创建Pull Request

```bash
# 1. 推送代码
git push origin feature/proxy-pool

# 2. 创建PR，使用模板
```

**PR模板**:
```markdown
## 变更说明
简述本次改动的内容和目的。

## 关联设计文档
- 设计文档: docs/designs/2026-02-03-add-proxy-pool.md
- 架构文档章节: ARCHITECTURE.md#代理池模块

## 变更类型
- [ ] 新功能
- [ ] Bug修复
- [ ] 重构
- [ ] 文档更新

## 测试
- [ ] 已添加单元测试
- [ ] 已添加集成测试
- [ ] 手动测试通过

## 检查清单
- [ ] 代码符合规范
- [ ] 已添加类型注解
- [ ] 已添加文档字符串
- [ ] 已更新相关文档
- [ ] 无linter错误
- [ ] 测试覆盖率达标

## 截图/日志
如有UI变更或运行结果，请提供截图或日志。
```

#### Step 2: 自动检查

```yaml
# .github/workflows/pr-check.yml
name: PR Check
on: [pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: Lint检查
        run: |
          flake8 .
          mypy .
          
  test:
    runs-on: ubuntu-latest
    steps:
      - name: 运行测试
        run: |
          pytest tests/
          
  coverage:
    runs-on: ubuntu-latest
    steps:
      - name: 检查覆盖率
        run: |
          pytest --cov=. --cov-report=xml
          # 要求覆盖率 >= 70%
```

#### Step 3: 人工审查

**审查者**: Tech Lead或资深开发

**审查检查项**:

##### 设计层面
- [ ] 是否符合设计文档？
- [ ] 是否遵循架构原则？
- [ ] 是否使用合适的设计模式？
- [ ] 模块职责是否清晰？

##### 代码质量
- [ ] 代码可读性
- [ ] 命名是否恰当？
- [ ] 逻辑是否清晰？
- [ ] 是否有重复代码？
- [ ] 是否有magic number？

##### 功能正确性
- [ ] 是否实现了所有功能？
- [ ] 边界条件是否处理？
- [ ] 错误处理是否完善？
- [ ] 是否有潜在bug？

##### 性能与安全
- [ ] 是否有性能问题？
- [ ] 是否有内存泄漏？
- [ ] 是否有安全隐患？
- [ ] 输入是否验证？

##### 测试
- [ ] 测试是否充分？
- [ ] 测试用例是否合理？
- [ ] 是否有集成测试？

##### 文档
- [ ] 类型注解是否完整？
- [ ] 文档字符串是否清晰？
- [ ] 是否更新了用户文档？

**审查意见示例**:
```markdown
# 代码审查意见

## 总体评价
代码整体质量良好，实现了设计文档中的功能。

## 必须修改 (Blocking)
1. L45: 缺少类型注解 (高优先级)
2. L78: 未处理网络异常 (高优先级)

## 建议修改 (Non-blocking)
1. L123: 可以使用列表推导式简化代码
2. L200: 建议添加单元测试

## 优点
1. 代码结构清晰
2. 命名规范
3. 注释完善

## 决策
- [ ] Approve (批准合并)
- [ ] Request Changes (要求修改)
- [ ] Comment (仅评论)
```

#### Step 4: 修改与复审

```bash
# 根据审查意见修改代码
vim core/proxy_pool.py

# 提交修改
git add .
git commit -m "fix: 根据code review修改"

# 推送
git push origin feature/proxy-pool

# 自动触发复审
```

#### Step 5: 合并代码

审查通过后：

```bash
# Squash合并（推荐）
# 将多个commit合并为一个

# Merge合并
# 保留所有commit历史

# 删除feature分支
git branch -d feature/proxy-pool
```

---

## 4️⃣ 测试验证（强制）

### 4.1 测试类型

#### 单元测试（必须）
```python
# tests/test_downloader.py
import pytest
from core.downloader import ImageDownloader

@pytest.mark.asyncio
async def test_download_image_success():
    """测试图片下载成功场景"""
    downloader = ImageDownloader()
    result = await downloader.download_image(
        "https://example.com/image.jpg",
        Path("/tmp/test.jpg")
    )
    assert result['success'] == True
    assert result['file_size'] > 0

@pytest.mark.asyncio
async def test_download_image_network_error():
    """测试网络错误场景"""
    downloader = ImageDownloader()
    with pytest.raises(NetworkError):
        await downloader.download_image(
            "https://invalid-url/image.jpg",
            Path("/tmp/test.jpg")
        )
```

#### 集成测试（必须）
```python
# tests/integration/test_spider_workflow.py
@pytest.mark.asyncio
async def test_full_crawl_workflow():
    """测试完整爬取流程"""
    async with BBSSpider() as spider:
        result = await spider.crawl_thread({
            'url': TEST_THREAD_URL,
            'thread_id': '123'
        })
        
        assert result['images_found'] > 0
        assert result['images_downloaded'] > 0
        assert Path(result['save_dir']).exists()
```

#### 性能测试（重要功能）
```python
# tests/performance/test_download_speed.py
def test_download_speed():
    """测试下载速度"""
    urls = ["url1", "url2", ...]  # 100个URL
    
    start_time = time.time()
    results = await download_batch(urls)
    duration = time.time() - start_time
    
    # 要求: > 100图/分钟
    speed = len(urls) / (duration / 60)
    assert speed > 100
```

### 4.2 测试覆盖率要求

| 模块类型 | 最低覆盖率 |
|---------|-----------|
| 核心模块 | 80% |
| 业务模块 | 70% |
| 工具模块 | 60% |
| 总体覆盖率 | 75% |

### 4.3 测试执行

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_downloader.py

# 检查覆盖率
pytest --cov=. --cov-report=html

# 性能测试
pytest tests/performance/ --benchmark
```

---

## 5️⃣ 文档完善

### 5.1 必须更新的文档

#### 代码文档
- ✅ 类型注解
- ✅ Docstring
- ✅ 行内注释（复杂逻辑）

#### 架构文档
- ✅ ARCHITECTURE.md（重大变更）
- ✅ 模块接口定义
- ✅ 数据流程图

#### 用户文档
- ✅ README.md（新功能）
- ✅ QUICKSTART.md（使用方式变更）
- ✅ 配置说明（新增配置项）

#### API文档
- ✅ 接口说明
- ✅ 参数说明
- ✅ 返回值说明
- ✅ 示例代码

### 5.2 文档审查

**检查项**:
- [ ] 文档是否完整？
- [ ] 示例是否可运行？
- [ ] 是否有typo？
- [ ] 格式是否规范？

---

## 6️⃣ 发布流程

### 6.1 发布前检查

**检查清单**:
- [ ] 所有测试通过
- [ ] 代码审查已批准
- [ ] 文档已更新
- [ ] 版本号已更新
- [ ] CHANGELOG已更新
- [ ] 无已知critical bug

### 6.2 版本号规范

使用语义化版本：`MAJOR.MINOR.PATCH`

```
v1.2.3
│ │ │
│ │ └─ PATCH: bug修复
│ └─── MINOR: 新功能（向后兼容）
└───── MAJOR: Breaking Change

示例：
v1.0.0 → v1.1.0  (新功能)
v1.1.0 → v1.1.1  (bug修复)
v1.1.1 → v2.0.0  (Breaking Change)
```

### 6.3 发布步骤

```bash
# 1. 更新版本号
vim setup.py  # 或 pyproject.toml

# 2. 更新CHANGELOG
vim CHANGELOG.md

# 3. 提交
git add .
git commit -m "chore: 发布 v1.2.0"

# 4. 打标签
git tag -a v1.2.0 -m "Release v1.2.0"

# 5. 推送
git push origin main --tags

# 6. 创建Release（GitHub）
# 附上CHANGELOG内容
```

---

## 📊 流程监控

### 检查点

| 阶段 | 负责人 | 检查内容 | 通过标准 |
|------|--------|---------|---------|
| 设计评审 | 架构师 | 设计文档完整性 | 评审通过 |
| 代码审查 | Tech Lead | 代码质量 | Approve |
| 测试验证 | QA | 测试通过率 | 100% |
| 文档审查 | Tech Writer | 文档完整性 | 无遗漏 |

### 质量指标

```
代码质量:
- Lint通过率: 100%
- 类型检查通过率: 100%
- 测试覆盖率: ≥75%
- 代码重复率: <5%

流程合规性:
- 设计文档先行率: 100%
- 代码审查率: 100%
- 测试通过率: 100%
```

---

## ⚠️ 违规处理

### 违规行为

- ❌ 未经设计评审直接编码
- ❌ 未经代码审查直接合并
- ❌ 未添加测试
- ❌ 绕过CI检查强制合并

### 处理措施

**第一次违规**: 口头警告，要求整改

**第二次违规**: 书面警告，代码回滚

**第三次违规**: 取消merge权限

---

## 📞 流程咨询

**问题反馈**:
- 技术问题: Tech Lead
- 流程问题: PM
- 工具问题: DevOps

**流程优化建议**:
- 提交Issue到项目管理系统
- 在team meeting讨论
- 每季度流程回顾会

---

## 📚 相关文档

- **ARCHITECTURE.md** - 系统架构设计
- **TEAM_ROLES.md** - 团队角色定义
- **CODE_REVIEW_GUIDELINE.md** - 代码审查指南

---

**流程版本**: v1.0  
**强制执行**: ✅ 是  
**适用范围**: 所有开发人员  
**最后更新**: 2026-02-03
