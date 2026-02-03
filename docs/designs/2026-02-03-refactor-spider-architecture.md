# 设计变更提案：爬虫架构重构

## 基本信息

- **标题**: 爬虫架构优化与代码整合
- **提出人**: 架构师 Chang
- **日期**: 2026-02-03
- **状态**: 已批准
- **关联Issue**: N/A
- **优先级**: 🔴 高
- **预计工作量**: 4小时

---

## 1. 变更概述

### 1.1 变更目标

1. **合并爬虫实现** - 将 `bbs_spider.py` 和 `crawl_xindong.py` 合并为统一架构
2. **合并配置文件** - 将 `config.py` 和 `config_xindong.py` 整合为多配置支持
3. **集成选择器检测** - 将 `detect_selectors` 功能集成到爬虫主流程

### 1.2 变更原因

**当前问题**：
- ❌ 代码重复：`XindongSpider` 继承 `BBSSpider` 但大量重写方法
- ❌ 配置分散：两个配置文件，维护成本高
- ❌ 功能独立：选择器检测是独立工具，无法在爬虫中直接使用

### 1.3 预期收益

- ✅ 减少30%代码重复
- ✅ 统一配置管理，支持多论坛配置
- ✅ 自动化选择器检测，降低配置门槛
- ✅ 更清晰的架构分层

---

## 2. 现状分析

### 2.1 当前架构

```
bbs_spider.py (320行)
├── BBSSpider (基类)
└── main() (示例)

crawl_xindong.py (211行)
├── XindongSpider(BBSSpider) (继承)
├── process_discuz_images() (Discuz特殊处理)
├── crawl_single_thread()
├── crawl_board()
└── main()

config.py
├── BBSConfig
├── CrawlerConfig
├── ImageConfig
└── config (全局实例)

config_xindong.py
├── XindongBBSConfig (继承BBSConfig)
├── xindong_config (实例)
├── XINDONG_BOARDS (常量)
└── EXAMPLE_THREADS (常量)

detect_selectors.py
└── main() (独立工具)
```

### 2.2 存在问题

1. **代码重复**：
   - `crawl_xindong.py` 重写了 `crawl_thread()` 方法，90%代码相同
   - 配置字段重复定义

2. **耦合问题**：
   - `crawl_xindong.py` 通过全局修改 `config_module.config` 来切换配置
   - 不支持多配置并存

3. **功能割裂**：
   - 选择器检测是独立工具，用户需手动运行
   - 无法在爬虫初始化时自动检测

---

## 3. 设计方案

### 3.1 整体架构

```
spider.py (主入口，400行)
├── BBSSpider (基类，通用逻辑)
├── DiscuzSpider(BBSSpider) (Discuz策略)
├── PhpBBSpider(BBSSpider) (phpBB策略)
└── SpiderFactory (工厂模式)

config.py (统一配置，200行)
├── BBSConfig (基础配置)
├── ForumPresets (论坛预设)
│   ├── DISCUZ_PRESET
│   ├── PHPBB_PRESET
│   └── VBULLETIN_PRESET
└── ConfigLoader (配置加载器)

core/selector_detector.py (选择器检测)
└── SelectorDetector (集成到爬虫)
```

### 3.2 模块设计

#### 3.2.1 统一爬虫架构

```python
class BBSSpider:
    """BBS爬虫基类 - 通用逻辑"""
    
    def __init__(self, config: BBSConfig):
        self.config = config
        self.forum_type = config.forum_type
        # ...
    
    async def crawl_thread(self, thread_info: Dict):
        """通用爬取逻辑"""
        # 1. 获取页面
        html = await self.fetch_page(thread_url)
        
        # 2. 解析
        thread_data = self.parser.parse_thread_page(html, thread_url)
        
        # 3. 论坛特定处理（策略模式）
        thread_data['images'] = await self.process_images(thread_data['images'])
        
        # 4. 下载
        await self.download_thread_images(thread_data)
    
    async def process_images(self, images: List[str]) -> List[str]:
        """图片处理 - 子类可重写"""
        return images


class DiscuzSpider(BBSSpider):
    """Discuz论坛专用处理"""
    
    async def process_images(self, images: List[str]) -> List[str]:
        """Discuz特殊处理：附件链接、原图参数"""
        processed = []
        for img_url in images:
            # 处理相对路径
            if img_url.startswith('forum.php'):
                img_url = f"{self.config.base_url}/{img_url}"
            
            # 添加原图参数
            if 'mod=attachment' in img_url and 'nothumb' not in img_url:
                img_url += '&nothumb=yes'
            
            processed.append(img_url)
        return processed


class SpiderFactory:
    """爬虫工厂 - 根据配置创建合适的爬虫"""
    
    @staticmethod
    def create_spider(config: BBSConfig) -> BBSSpider:
        forum_type = config.forum_type.lower()
        
        if forum_type == 'discuz':
            return DiscuzSpider(config)
        elif forum_type == 'phpbb':
            return PhpBBSpider(config)
        else:
            return BBSSpider(config)
```

#### 3.2.2 统一配置管理

```python
# config.py

class BBSConfig(BaseModel):
    """基础配置"""
    name: str = "default"
    forum_type: str = "generic"  # discuz, phpbb, vbulletin, generic
    base_url: str = ""
    
    # 选择器
    thread_list_selector: str = "div.thread-item"
    thread_link_selector: str = "a.thread-link"
    image_selector: str = "img"
    next_page_selector: str = "a.next-page"
    
    # 爬虫参数
    max_concurrent_requests: int = 5
    download_delay: float = 1.0
    # ...


class ForumPresets:
    """论坛预设配置"""
    
    DISCUZ = BBSConfig(
        name="Discuz",
        forum_type="discuz",
        thread_list_selector="tbody[id^='normalthread'], tbody[id^='stickthread']",
        thread_link_selector="a.s.xst, a.xst",
        image_selector="img.zoom, img[file], img[aid]",
        next_page_selector="a.nxt, div.pg a.nxt",
        max_concurrent_requests=3,
        download_delay=2.0,
    )
    
    PHPBB = BBSConfig(
        name="phpBB",
        forum_type="phpbb",
        thread_list_selector="li.row",
        thread_link_selector="a.topictitle",
        image_selector="dl.attachbox img, div.content img",
        next_page_selector="a.next",
    )
    
    # 心动论坛（Discuz的实例配置）
    XINDONG = BBSConfig(
        **DISCUZ.dict(),
        name="心动论坛",
        base_url="https://bbs.xd.com",
    )


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load(config_name: str = "default") -> BBSConfig:
        """加载配置"""
        if config_name == "xindong":
            return ForumPresets.XINDONG
        elif config_name == "discuz":
            return ForumPresets.DISCUZ
        else:
            return BBSConfig()
    
    @staticmethod
    def auto_detect(url: str) -> BBSConfig:
        """自动检测配置"""
        from core.selector_detector import SelectorDetector
        
        detector = SelectorDetector(url)
        asyncio.run(detector.detect_all())
        
        # 根据检测结果创建配置
        config = BBSConfig(
            base_url=extract_base_url(url),
            forum_type=detector.forum_type,
            thread_list_selector=detector.detected_selectors['thread_list_selector'],
            thread_link_selector=detector.detected_selectors['thread_link_selector'],
            image_selector=detector.detected_selectors['image_selector'],
            next_page_selector=detector.detected_selectors['next_page_selector'],
        )
        
        return config
```

#### 3.2.3 集成选择器检测

```python
# spider.py

class BBSSpider:
    def __init__(self, config: Optional[BBSConfig] = None, url: Optional[str] = None):
        """
        初始化爬虫
        
        Args:
            config: 手动配置（优先）
            url: 论坛URL，如果未提供config则自动检测
        """
        if config:
            self.config = config
        elif url:
            logger.info(f"自动检测论坛配置: {url}")
            self.config = ConfigLoader.auto_detect(url)
        else:
            raise ValueError("必须提供 config 或 url")
        
        # ...


# 使用示例
async def main():
    # 方式1：使用预设配置
    spider = SpiderFactory.create_spider(ForumPresets.XINDONG)
    
    # 方式2：自动检测配置
    spider = BBSSpider(url="https://example.com/forum")
    
    # 方式3：手动配置
    config = BBSConfig(base_url="...", ...)
    spider = BBSSpider(config=config)
```

### 3.3 数据流程

```
用户输入
    ↓
方式1: 指定预设 → ForumPresets.XINDONG
方式2: 提供URL → ConfigLoader.auto_detect(url)
方式3: 手动配置 → BBSConfig(...)
    ↓
SpiderFactory.create_spider(config)
    ↓
根据 forum_type 创建对应 Spider
    ↓
    ├── forum_type='discuz' → DiscuzSpider
    ├── forum_type='phpbb' → PhpBBSpider
    └── 其他 → BBSSpider
    ↓
执行爬取
```

---

## 4. 技术方案

### 4.1 核心算法

#### 策略模式 - 论坛特定处理

```python
# 基类定义钩子方法
class BBSSpider:
    async def process_images(self, images: List[str]) -> List[str]:
        """图片处理钩子 - 子类重写"""
        return images
    
    async def process_thread_url(self, url: str) -> str:
        """URL处理钩子"""
        return url

# 子类实现特定策略
class DiscuzSpider(BBSSpider):
    async def process_images(self, images: List[str]) -> List[str]:
        # Discuz特定逻辑
        pass
```

#### 工厂模式 - 爬虫创建

```python
class SpiderFactory:
    _registry = {
        'discuz': DiscuzSpider,
        'phpbb': PhpBBSpider,
        'vbulletin': VBulletinSpider,
    }
    
    @classmethod
    def register(cls, forum_type: str, spider_class: Type[BBSSpider]):
        """注册新的爬虫类型"""
        cls._registry[forum_type] = spider_class
    
    @classmethod
    def create_spider(cls, config: BBSConfig) -> BBSSpider:
        spider_class = cls._registry.get(config.forum_type, BBSSpider)
        return spider_class(config)
```

### 4.2 依赖变更

**无新增依赖**

### 4.3 配置变更

**新配置结构**:

```python
# 支持多配置文件
configs/
├── default.json
├── xindong.json
├── phpbb.json
└── custom.json
```

或使用预设：

```python
from config import ForumPresets

config = ForumPresets.XINDONG
config = ForumPresets.DISCUZ
config = ForumPresets.PHPBB
```

---

## 5. 影响分析

### 5.1 性能影响

| 指标 | 变更前 | 变更后 | 变化 |
|------|-------|-------|------|
| 代码行数 | 531行(2文件) | ~400行(1文件) | -25% |
| 配置复杂度 | 2个文件 | 1个文件+预设 | 简化 |
| 初始化时间 | <1ms | <1ms (自动检测+5s) | 可选 |

**性能评估**:
- ✅ 代码量减少，维护成本降低
- ✅ 自动检测是可选功能，不影响性能
- ✅ 策略模式性能开销可忽略

### 5.2 兼容性影响

- [x] **向后兼容** - 保留原有配置方式
- [ ] **需要迁移** - 使用 `crawl_xindong.py` 的脚本需要调整
- [ ] **Breaking Change** - API基本不变

**迁移指南**:

```python
# 旧方式
from config_xindong import xindong_config
from crawl_xindong import XindongSpider
spider = XindongSpider()

# 新方式1（推荐）
from config import ForumPresets
from spider import SpiderFactory
spider = SpiderFactory.create_spider(ForumPresets.XINDONG)

# 新方式2（自动检测）
from spider import BBSSpider
spider = BBSSpider(url="https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21")
```

### 5.3 安全性影响

**无新增安全风险**

---

## 6. 实施计划

### 6.1 开发任务

- [ ] **任务1**: 重构 `spider.py` (预计: 2小时)
  - [ ] 整合 `BBSSpider` 和 `XindongSpider`
  - [ ] 实现策略模式和工厂模式
  - [ ] 集成选择器自动检测

- [ ] **任务2**: 重构 `config.py` (预计: 1小时)
  - [ ] 合并配置类
  - [ ] 添加 `ForumPresets`
  - [ ] 实现 `ConfigLoader`

- [ ] **任务3**: 更新文档和示例 (预计: 1小时)
  - [ ] 更新 README.md
  - [ ] 更新 ARCHITECTURE.md
  - [ ] 添加迁移指南

**总计**: 4小时

### 6.2 测试计划

- [ ] **单元测试**
  - [ ] 测试 `SpiderFactory` 创建逻辑
  - [ ] 测试 `ConfigLoader` 加载逻辑
  - [ ] 测试策略模式（Discuz处理）

- [ ] **集成测试**
  - [ ] 测试心动论坛爬取（预设配置）
  - [ ] 测试自动检测配置
  - [ ] 测试多配置切换

- [ ] **回归测试**
  - [ ] 验证原有功能正常
  - [ ] 验证性能无退化

### 6.3 文档计划

- [ ] 更新 `ARCHITECTURE.md`
  - [ ] 更新架构图
  - [ ] 说明策略模式和工厂模式

- [ ] 更新 `README.md`
  - [ ] 更新快速开始示例
  - [ ] 添加多配置使用说明

- [ ] 创建 `MIGRATION.md`
  - [ ] 提供迁移指南
  - [ ] 新旧API对比

---

## 7. 风险与对策

### 风险1: 破坏现有功能
- **概率**: 低
- **影响**: 高
- **对策**: 
  - 完整的回归测试
  - 保留旧文件作为备份
  - 分步骤提交，便于回滚

### 风险2: 用户适应成本
- **概率**: 中
- **影响**: 中
- **对策**:
  - 提供详细的迁移指南
  - 保留向后兼容的API
  - 在README中突出说明变更

### 风险3: 自动检测不准确
- **概率**: 中
- **影响**: 中
- **对策**:
  - 自动检测是可选功能
  - 用户可以手动指定配置
  - 提供预设配置作为fallback

---

## 8. 评审意见

| 评审人 | 角色 | 意见 | 日期 |
|--------|------|------|------|
| Chang | 架构师 | 批准，设计合理 | 2026-02-03 |

---

## 9. 决策

- [x] ✅ **批准实施** - 架构优化合理，收益明显

**批准人**: 架构师 Chang  
**批准日期**: 2026-02-03

**实施说明**:
1. 立即开始重构
2. 优先完成核心功能
3. 确保测试通过后再删除旧文件

---

## 10. 实施记录

**开始日期**: 2026-02-03  
**预计完成**: 2026-02-03  
**实施人**: Chang

---

**文档状态**: 已批准  
**版本**: v1.0  
**维护者**: 架构师 Chang
