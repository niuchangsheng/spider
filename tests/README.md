# 单元测试说明

## 📋 概述

本项目使用 Python `unittest` 框架进行单元测试，确保代码质量和功能正确性。

## 📁 目录结构

```
tests/
├── __init__.py
├── run_tests.sh          # Shell 测试脚本（支持 .venv/venv）
├── README.md             # 本文件
├── test_config.py        # config 加载、get_example_config、ConfigLoader 等
├── core/                 # core 模块测试
│   ├── __init__.py
│   ├── test_checkpoint.py    # CheckpointManager
│   ├── test_crawl_queue.py   # CrawlQueue / AdaptiveCrawlQueue
│   ├── test_deduplicator.py  # ImageDeduplicator
│   ├── test_downloader.py   # ImageDownloader（mock）
│   └── test_storage.py      # Storage（临时 SQLite）
├── detector/
│   ├── __init__.py
│   └── test_selector_detector.py  # SelectorDetector / auto_detect_selectors
├── parsers/
│   ├── __init__.py
│   ├── test_bbs_parser.py       # BBSParser
│   └── test_dynamic_parser.py  # DynamicPageParser
├── spiders/
│   ├── __init__.py
│   └── test_spider_factory.py  # SpiderFactory
└── cli/
    ├── __init__.py
    ├── test_commands.py   # create_parser / 子命令解析
    └── test_handlers.py   # handle_checkpoint_status
```

## 🚀 运行测试

### 方法1: 使用 Shell 脚本（推荐）

```bash
# 自动激活虚拟环境并运行测试
./tests/run_tests.sh

# 生成覆盖率报告（文本格式）
./tests/run_tests.sh --coverage
# 或使用短参数
./tests/run_tests.sh -c

# 生成覆盖率报告（HTML格式，包含文本格式）
./tests/run_tests.sh --html
# 或使用短参数
./tests/run_tests.sh -h
```

### 方法2: 使用 unittest 自动发现（推荐）

```bash
# 激活虚拟环境（优先 .venv）
source .venv/bin/activate   # 或 source venv/bin/activate

# 必须设置 PYTHONPATH，否则 tests.cli / tests.parsers 等无法正确加载
export PYTHONPATH=.

# 运行所有测试（自动发现所有 test_*.py 文件）
python -m unittest discover -s tests -p "test_*.py" -t . -v

# 退出虚拟环境
deactivate
```

### 方法3: 运行特定测试

```bash
source venv/bin/activate

# 运行特定测试文件
python -m unittest tests.core.test_checkpoint
python -m unittest tests.core.test_crawl_queue
python -m unittest tests.detector.test_selector_detector

# 运行特定测试类
python -m unittest tests.core.test_checkpoint.TestCheckpointManager

# 运行特定测试方法
python -m unittest tests.core.test_checkpoint.TestCheckpointManager.test_save_and_load_checkpoint

# 退出虚拟环境
deactivate
```

## 📝 测试覆盖

### 已实现的测试

1. **CheckpointManager 测试** (`test_checkpoint.py`)
   - ✅ 初始化测试
   - ✅ 保存和加载检查点
   - ✅ 文章ID相关功能
   - ✅ 标记完成/错误
   - ✅ 获取状态和统计信息
   - ✅ 清除检查点

2. **CrawlQueue 测试** (`test_crawl_queue.py`)
   - ✅ 初始化测试
   - ✅ 生产者功能
   - ✅ 消费者功能
   - ✅ 队列运行
   - ✅ 错误处理
   - ✅ 统计信息

3. **AdaptiveCrawlQueue 测试** (`test_crawl_queue.py`)
   - ✅ 初始化测试
   - ✅ 错误率计算
   - ✅ 自适应调整并发数
   - ✅ 统计信息

4. **SelectorDetector 测试** (`test_selector_detector.py`)
   - ✅ 初始化测试
   - ✅ 论坛类型检测
   - ✅ 选择器检测
   - ✅ 图片判断

5. **Storage 文章测试** (`test_storage.py` → `TestStorageArticle`)
   - ✅ 未下载图片不算爬过：`images_downloaded=0` 或未传时 `article_exists` 返回 False
   - ✅ 已下载图片算爬过：`save_article(images_downloaded=True)` 后 `article_exists` 返回 True

6. **DynamicNewsCrawler 检查点与 max_pages** (`test_dynamic_news_spider.py`)
   - ✅ 检查点 current_page > max_pages 时返回 [] 且 `_skipped_checkpoint_over_max_pages=True`
   - ✅ 检查点 current_page <= max_pages 时不设 _skipped，进入爬取逻辑

## 🧪 编写新测试

### 测试文件命名规范

- 测试文件必须以 `test_` 开头
- 测试文件应该放在对应的子目录中（如 `tests/core/`）

### 测试类命名规范

- 测试类必须以 `Test` 开头
- 测试类应该继承 `unittest.TestCase`

### 测试方法命名规范

- 测试方法必须以 `test_` 开头
- 测试方法应该描述测试的功能

### 示例

```python
import unittest
from core.some_module import SomeClass

class TestSomeClass(unittest.TestCase):
    """SomeClass 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.instance = SomeClass()
    
    def tearDown(self):
        """测试后清理"""
        pass
    
    def test_some_method(self):
        """测试某个方法"""
        result = self.instance.some_method()
        self.assertEqual(result, expected_value)
```

## 📊 测试覆盖率

### 使用测试脚本（推荐）

```bash
# 生成文本格式覆盖率报告
./tests/run_tests.sh --coverage

# 生成HTML格式覆盖率报告（推荐，更直观）
./tests/run_tests.sh --html
```

脚本会自动：
- ✅ 检查并安装 `coverage` 包（如果未安装）
- ✅ 运行所有测试并收集覆盖率数据
- ✅ 生成文本格式覆盖率报告（显示在终端）
- ✅ 生成HTML格式覆盖率报告（如果使用 `--html` 选项）
  - HTML报告保存在 `htmlcov/` 目录
  - 打开 `htmlcov/index.html` 查看详细报告

### 手动运行覆盖率检查

项目根目录有 `.coveragerc`，会排除 `tests/*`、`spider.py` 及难以单测的爬虫主流程（bbs_spider、dynamic_news_spider、base）。目标：**覆盖率 90%+**（当前约 61%，持续补充 UT 提升）。

```bash
source .venv/bin/activate
export PYTHONPATH=.

# 安装 coverage（若未安装）
pip install coverage

# 使用项目 .coveragerc 运行测试并收集覆盖率
coverage run -m unittest discover -s tests -p "test_*.py" -t .
coverage report -m    # 文本格式（含缺失行）
coverage html         # 生成 htmlcov/index.html
```

## 手动验证场景（新闻爬虫 sxd）

以下场景用于验证 `crawl --config sxd` 的检查点、max_pages、download_images 行为，需在项目根目录、已激活虚拟环境下执行。

### 场景：`--download-images` + `max-pages=1`

1. **清检查点后跑 1 页并下载图片**

   ```bash
   python spider.py checkpoint-status --site sxd.xd.com --board news --clear
   python spider.py crawl --config sxd --max-pages=1 --download-images
   ```

   - 预期：爬取第 1 页，发现 5 篇新文章，写入 Storage（`images_downloaded=1`），爬取 5 篇详情，下载图片（若有）；检查点保存为 page 2。

2. **再跑无 `--download-images`（清检查点后）**

   ```bash
   python spider.py checkpoint-status --site sxd.xd.com --board news --clear
   python spider.py crawl --config sxd --max-pages=1
   ```

   - 预期：第 1 页 5 篇均视为已爬（`article_exists` 因已下载图片为 True），日志出现「本页 5 篇均重复」，发现 0 篇新文章。

3. **再跑带 `--download-images` 且 `max-pages=1`**

   ```bash
   python spider.py crawl --config sxd --max-pages=1 --download-images
   ```

   - 预期：检查点 page 2 > max_pages=1，本次不爬取，不请求列表页，发现 0 篇；不会再次爬详情/下图片。

## ⚠️ 注意事项

1. **虚拟环境**: 所有测试必须在虚拟环境下运行
2. **测试隔离**: 每个测试应该独立，不依赖其他测试
3. **清理资源**: 使用 `tearDown` 清理测试产生的临时文件
4. **异步测试**: 对于异步函数，使用 `asyncio.run()` 包装

## 🔧 故障排除

### 问题: ModuleNotFoundError 或 tests.cli / tests.parsers 未发现

**解决方案**: 必须设置 `PYTHONPATH=.`，并从项目根目录运行 discover（`-t .`）：

```bash
source .venv/bin/activate
export PYTHONPATH=.
python -m unittest discover -s tests -p "test_*.py" -t . -v
```

### 问题: 测试失败但代码正常

**解决方案**: 检查测试数据是否正确，可能需要更新测试用例

## 📚 参考资源

- [Python unittest 文档](https://docs.python.org/3/library/unittest.html)
- [unittest 最佳实践](https://docs.python.org/3/library/unittest.html#organizing-test-code)
