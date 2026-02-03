# 设计变更：修正心动论坛配置位置

## 基本信息

- **标题**: 修正心动论坛配置位置
- **提出人**: 架构师 Chang
- **日期**: 2026-02-03
- **状态**: 已批准
- **关联Issue**: N/A
- **优先级**: 🟡 中
- **预计工作量**: 30分钟

---

## 1. 变更概述

### 1.1 问题描述

当前 `ForumPresets.xindong()` 将心动论坛作为论坛类型预设，这在架构上是不正确的：

```python
# ❌ 错误：xindong不是论坛类型
class ForumPresets:
    @staticmethod
    def discuz() -> Config:  # ✅ 正确：这是论坛类型
        ...
    
    @staticmethod
    def xindong() -> Config:  # ❌ 错误：这是具体实例，不是类型
        ...
```

**问题**：
- `discuz`、`phpbb`、`vbulletin` 是**论坛系统类型**
- `xindong` 是一个**具体的论坛实例**（使用Discuz系统）
- 混淆了"类型"和"实例"的概念

### 1.2 变更目标

将心动论坛配置从 `ForumPresets` 移到示例配置常量中。

---

## 2. 设计方案

### 2.1 新架构

```python
# config.py

class ForumPresets:
    """论坛类型预设（通用配置）"""
    
    @staticmethod
    def discuz() -> Config:
        """Discuz论坛通用配置"""
        ...
    
    @staticmethod
    def phpbb() -> Config:
        """phpBB论坛通用配置"""
        ...


# 示例配置（具体实例）
EXAMPLE_CONFIGS = {
    "xindong": Config(
        bbs={
            "name": "心动论坛",
            "forum_type": "discuz",
            "base_url": "https://bbs.xd.com",
            ...
        }
    ),
}


# 便捷函数
def get_example_config(name: str) -> Config:
    """获取示例配置"""
    return EXAMPLE_CONFIGS.get(name)
```

### 2.2 使用方式

```python
# 旧方式（类型和实例混淆）
spider = SpiderFactory.create(preset="xindong")  # ❌

# 新方式1：使用论坛类型 + 自定义URL
config = ForumPresets.discuz()
config.bbs.base_url = "https://bbs.xd.com"
spider = SpiderFactory.create(config=config)  # ✅

# 新方式2：使用示例配置
from config import EXAMPLE_CONFIGS
config = EXAMPLE_CONFIGS["xindong"]
spider = SpiderFactory.create(config=config)  # ✅

# 新方式3：快捷方法
from config import get_example_config
config = get_example_config("xindong")
spider = SpiderFactory.create(config=config)  # ✅
```

---

## 3. 技术方案

### 3.1 代码变更

#### config.py

```python
class ForumPresets:
    """论坛类型预设 - 只包含论坛系统的通用配置"""
    
    @staticmethod
    def discuz() -> Config:
        """Discuz论坛通用配置"""
        return Config(...)
    
    @staticmethod
    def phpbb() -> Config:
        """phpBB论坛通用配置"""
        return Config(...)
    
    @staticmethod
    def vbulletin() -> Config:
        """vBulletin论坛通用配置"""
        return Config(...)
    
    # ❌ 删除 xindong() 方法


# 示例配置常量 - 具体论坛实例
EXAMPLE_CONFIGS = {
    "xindong": Config(
        bbs={
            "name": "心动论坛",
            "forum_type": "discuz",
            "base_url": "https://bbs.xd.com",
            "login_url": "https://bbs.xd.com/member.php?mod=logging&action=login",
            "thread_list_selector": "tbody[id^='normalthread'], tbody[id^='stickthread']",
            "thread_link_selector": "a.s.xst, a.xst",
            "image_selector": "img.zoom,img[file],img[aid],div.pattl img,div.pcb img",
            "next_page_selector": "a.nxt, div.pg a.nxt",
        },
        crawler={
            "max_concurrent_requests": 3,
            "download_delay": 2.0,
        },
        image={
            "min_width": 300,
            "min_height": 300,
            "min_size": 30000,
        }
    ),
}


def get_example_config(name: str) -> Config:
    """
    获取示例配置
    
    Args:
        name: 示例名称 (xindong)
    
    Returns:
        Config实例
    """
    if name not in EXAMPLE_CONFIGS:
        raise ValueError(f"未知的示例配置: {name}，可用: {list(EXAMPLE_CONFIGS.keys())}")
    return EXAMPLE_CONFIGS[name]
```

#### ConfigLoader 更新

```python
class ConfigLoader:
    @staticmethod
    def load(preset: str = "default") -> Config:
        """
        加载配置
        
        Args:
            preset: 预设名称 (discuz/phpbb/vbulletin)
        """
        preset = preset.lower()
        
        if preset == "discuz":
            return ForumPresets.discuz()
        elif preset == "phpbb":
            return ForumPresets.phpbb()
        elif preset == "vbulletin":
            return ForumPresets.vbulletin()
        else:
            return load_config_from_env()
```

---

## 4. 影响分析

### 4.1 API变更

| 场景 | 旧API | 新API |
|------|-------|-------|
| 使用心动论坛 | `SpiderFactory.create(preset="xindong")` | `SpiderFactory.create(config=get_example_config("xindong"))` |
| 使用Discuz类型 | `SpiderFactory.create(preset="discuz")` | `SpiderFactory.create(preset="discuz")` ✅ 不变 |

### 4.2 文档更新

需要更新：
- README.md - 示例代码
- spider.py - main() 函数
- 其他引用 `preset="xindong"` 的地方

---

## 5. 实施计划

- [ ] 更新 config.py
  - [ ] 删除 `ForumPresets.xindong()`
  - [ ] 添加 `EXAMPLE_CONFIGS`
  - [ ] 添加 `get_example_config()`
  
- [ ] 更新 spider.py
  - [ ] 更新示例代码
  
- [ ] 更新 README.md
  - [ ] 更新使用示例
  
- [ ] 测试验证

---

## 6. 决策

- [x] ✅ **批准实施** - 架构设计更合理

**批准人**: 架构师 Chang  
**批准日期**: 2026-02-03

---

**文档状态**: 已批准  
**版本**: v1.0
