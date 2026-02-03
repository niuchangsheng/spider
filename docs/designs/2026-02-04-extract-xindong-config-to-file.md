# 设计变更：提取心动论坛配置到独立文件

## 基本信息

- **标题**: 提取心动论坛配置到独立文件
- **提出人**: 架构师 Chang
- **日期**: 2026-02-04
- **状态**: 已批准
- **关联Issue**: N/A
- **优先级**: 🟡 中
- **预计工作量**: 45分钟

---

## 1. 变更概述

### 1.1 问题描述

当前心动论坛的配置硬编码在 `config.py` 中：

```python
# config.py
EXAMPLE_CONFIGS = {
    "xindong": Config(...),  # 硬编码
}

XINDONG_BOARDS = {...}  # 硬编码
EXAMPLE_THREADS = [...]  # 硬编码
```

**问题**：
1. 配置与代码耦合
2. 修改配置需要改动 Python 代码
3. 不便于用户自定义配置
4. 无法动态加载多个论坛配置

### 1.2 变更目标

将心动论坛配置提取到独立的配置文件（JSON/YAML），启动时动态加载。

---

## 2. 设计方案

### 2.1 配置文件格式

选择 **JSON** 格式（易读、标准库支持、无需额外依赖）。

**文件结构**：
```
configs/
├── README.md           # 配置文件说明
├── xindong.json        # 心动论坛配置
└── example.json        # 配置模板
```

### 2.2 配置文件内容

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
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1"
  ]
}
```

### 2.3 加载机制

```python
# config.py

def load_forum_config(config_file: str) -> Config:
    """
    从配置文件加载论坛配置
    
    Args:
        config_file: 配置文件路径 (如 "configs/xindong.json")
    
    Returns:
        Config实例
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return Config(
        bbs={
            "name": data["name"],
            "forum_type": data["forum_type"],
            "base_url": data["base_url"],
            "login_url": data.get("login_url"),
            "thread_list_selector": data["selectors"]["thread_list"],
            "thread_link_selector": data["selectors"]["thread_link"],
            "image_selector": data["selectors"]["image"],
            "next_page_selector": data["selectors"]["next_page"],
        },
        crawler=data.get("crawler", {}),
        image=data.get("image", {}),
    )


def load_all_forum_configs(config_dir: str = "configs") -> Dict[str, Config]:
    """加载所有论坛配置"""
    configs = {}
    config_path = Path(config_dir)
    
    if not config_path.exists():
        return configs
    
    for config_file in config_path.glob("*.json"):
        if config_file.name == "example.json":
            continue
        
        name = config_file.stem
        try:
            configs[name] = load_forum_config(config_file)
            logger.info(f"✅ 加载配置: {name}")
        except Exception as e:
            logger.warning(f"⚠️  加载配置失败: {name} - {e}")
    
    return configs


# 启动时自动加载
EXAMPLE_CONFIGS = load_all_forum_configs()
```

---

## 3. 技术方案

### 3.1 文件结构

```
spider/
├── config.py                 # 核心配置（移除硬编码）
├── configs/                  # 配置文件目录（新增）
│   ├── README.md            # 配置说明
│   ├── example.json         # 配置模板
│   └── xindong.json         # 心动论坛配置
└── spider.py                # 主程序
```

### 3.2 代码变更

#### 1. 创建 `configs/xindong.json`

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
    "download_delay": 2.0
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
    "https://bbs.xd.com/forum.php?mod=viewthread&tid=3479145&extra=page%3D1"
  ]
}
```

#### 2. 更新 `config.py`

```python
import json
from pathlib import Path
from typing import Dict

# 配置文件目录
CONFIG_DIR = BASE_DIR / "configs"

def load_forum_config(config_file: Path) -> Dict[str, Any]:
    """加载论坛配置文件"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_config_from_dict(data: Dict[str, Any]) -> Config:
    """从字典创建Config对象"""
    return Config(
        bbs={
            "name": data["name"],
            "forum_type": data["forum_type"],
            "base_url": data["base_url"],
            "login_url": data.get("login_url"),
            "thread_list_selector": data["selectors"]["thread_list"],
            "thread_link_selector": data["selectors"]["thread_link"],
            "image_selector": data["selectors"]["image"],
            "next_page_selector": data["selectors"]["next_page"],
        },
        crawler=data.get("crawler", {}),
        image=data.get("image", {}),
    )

def load_all_forum_configs() -> Dict[str, Config]:
    """自动加载所有论坛配置"""
    configs = {}
    
    if not CONFIG_DIR.exists():
        logger.warning(f"配置目录不存在: {CONFIG_DIR}")
        return configs
    
    for config_file in CONFIG_DIR.glob("*.json"):
        if config_file.name in ["example.json", "template.json"]:
            continue
        
        name = config_file.stem
        try:
            data = load_forum_config(config_file)
            configs[name] = create_config_from_dict(data)
            logger.info(f"✅ 加载配置: {name} ({data['name']})")
        except Exception as e:
            logger.warning(f"⚠️  加载配置失败: {name} - {e}")
    
    return configs

# 自动加载所有配置
EXAMPLE_CONFIGS = load_all_forum_configs()

# 删除硬编码的 XINDONG_BOARDS 和 EXAMPLE_THREADS
# 这些数据现在在 xindong.json 中

def get_example_config(name: str) -> Config:
    """获取示例配置（保持API兼容）"""
    if name not in EXAMPLE_CONFIGS:
        available = ", ".join(EXAMPLE_CONFIGS.keys())
        raise ValueError(f"未知的示例配置: {name}，可用: {available}")
    return EXAMPLE_CONFIGS[name]

def get_forum_boards(config_name: str) -> Dict[str, Any]:
    """获取论坛板块配置"""
    config_file = CONFIG_DIR / f"{config_name}.json"
    if not config_file.exists():
        return {}
    data = load_forum_config(config_file)
    return data.get("boards", {})

def get_example_threads(config_name: str) -> List[str]:
    """获取示例帖子"""
    config_file = CONFIG_DIR / f"{config_name}.json"
    if not config_file.exists():
        return []
    data = load_forum_config(config_file)
    return data.get("example_threads", [])
```

---

## 4. 影响分析

### 4.1 API 兼容性

| API | 旧方式 | 新方式 | 兼容性 |
|-----|--------|--------|--------|
| 获取配置 | `get_example_config("xindong")` | `get_example_config("xindong")` | ✅ 完全兼容 |
| 获取板块 | `XINDONG_BOARDS` | `get_forum_boards("xindong")` | ⚠️ 需更新 |
| 获取示例帖子 | `EXAMPLE_THREADS` | `get_example_threads("xindong")` | ⚠️ 需更新 |

### 4.2 优势

1. **配置与代码分离** - 修改配置不需要改代码
2. **易于扩展** - 添加新论坛只需创建JSON文件
3. **用户友好** - 用户可以轻松自定义配置
4. **动态加载** - 自动发现和加载所有配置
5. **版本控制友好** - 配置变更历史清晰

---

## 5. 实施计划

### 阶段1：创建配置文件
- [ ] 创建 `configs/` 目录
- [ ] 创建 `configs/xindong.json`
- [ ] 创建 `configs/example.json` (模板)
- [ ] 创建 `configs/README.md` (说明文档)

### 阶段2：实现加载机制
- [ ] 实现 `load_forum_config()`
- [ ] 实现 `create_config_from_dict()`
- [ ] 实现 `load_all_forum_configs()`
- [ ] 实现 `get_forum_boards()`
- [ ] 实现 `get_example_threads()`

### 阶段3：更新代码
- [ ] 更新 `config.py` - 移除硬编码
- [ ] 更新 `spider.py` - 使用新API
- [ ] 更新文档

### 阶段4：测试验证
- [ ] 测试配置加载
- [ ] 测试爬虫运行
- [ ] 测试错误处理

---

## 6. 回滚方案

如果出现问题，可以：
1. 恢复 `config.py` 中的硬编码配置
2. Git revert 相关提交

---

## 7. 决策

- [x] ✅ **批准实施** - 配置与代码分离是最佳实践

**批准人**: 架构师 Chang  
**批准日期**: 2026-02-04

---

**文档状态**: 已批准  
**版本**: v1.0
