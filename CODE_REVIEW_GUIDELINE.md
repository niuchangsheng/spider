# 代码审查指南

**版本**: v1.0  
**发布日期**: 2026-02-03  
**适用范围**: 所有代码审查者

---

## 🎯 代码审查目标

代码审查不仅仅是找bug，更重要的是：
- ✅ 确保代码质量
- ✅ 知识共享和团队成长
- ✅ 保持架构一致性
- ✅ 发现潜在问题
- ✅ 促进最佳实践

---

## 📋 代码审查检查清单

### 1️⃣ 设计与架构 (⭐⭐⭐⭐⭐)

**必须检查**:
- [ ] **设计文档一致性**: 代码是否严格按照设计文档实现？
- [ ] **架构符合性**: 是否符合ARCHITECTURE.md中的设计原则？
- [ ] **模块职责**: 是否遵循单一职责原则？
- [ ] **依赖方向**: 依赖关系是否合理？（高层→低层）
- [ ] **扩展性**: 是否易于扩展？是否遵循开闭原则？

**审查示例**:
```python
# ❌ 不符合设计
class Downloader:
    def download_and_parse(self, url):
        # 违反单一职责，混合了下载和解析
        pass

# ✅ 符合设计
class Downloader:
    def download(self, url):
        # 只负责下载
        pass

class Parser:
    def parse(self, html):
        # 只负责解析
        pass
```

---

### 2️⃣ 代码质量 (⭐⭐⭐⭐⭐)

#### 可读性
- [ ] **命名**: 变量、函数、类名是否清晰表意？
- [ ] **长度**: 函数是否过长？（建议<50行）
- [ ] **复杂度**: 是否有过于复杂的逻辑？
- [ ] **注释**: 复杂逻辑是否有注释？

**审查示例**:
```python
# ❌ 命名不清晰
def f(x, y):
    return x + y

# ✅ 命名清晰
def calculate_total_price(price: float, quantity: int) -> float:
    """计算总价"""
    return price * quantity

# ❌ 函数过长
def process_data(data):
    # 100+ lines...
    pass

# ✅ 拆分为小函数
def process_data(data):
    validated_data = validate(data)
    cleaned_data = clean(validated_data)
    return transform(cleaned_data)
```

#### 类型安全
- [ ] **类型注解**: 是否完整？
- [ ] **类型正确**: 类型是否合理？
- [ ] **Optional处理**: 是否正确处理None？

**审查示例**:
```python
# ❌ 缺少类型注解
def download(url):
    pass

# ✅ 完整类型注解
def download(url: str) -> Optional[bytes]:
    """下载文件，返回内容或None"""
    pass

# ❌ 未处理None
def get_title(data: Optional[Dict]) -> str:
    return data['title']  # 可能抛出异常

# ✅ 正确处理Optional
def get_title(data: Optional[Dict]) -> Optional[str]:
    if data is None:
        return None
    return data.get('title')
```

#### 文档字符串
- [ ] **Docstring完整**: 是否包含说明、参数、返回值？
- [ ] **示例代码**: 复杂功能是否有示例？
- [ ] **异常说明**: 是否说明可能抛出的异常？

**审查示例**:
```python
# ❌ 缺少文档
def process(data, mode):
    pass

# ✅ 完整文档
def process(data: Dict, mode: str = "fast") -> List[Dict]:
    """
    处理数据
    
    Args:
        data: 输入数据字典
        mode: 处理模式，可选 "fast" 或 "accurate"
        
    Returns:
        处理后的数据列表
        
    Raises:
        ValueError: 当mode参数无效时
        
    Examples:
        >>> process({'key': 'value'}, mode='fast')
        [{'processed': True}]
    """
    pass
```

---

### 3️⃣ 功能正确性 (⭐⭐⭐⭐⭐)

- [ ] **功能完整**: 是否实现了所有功能？
- [ ] **边界条件**: 是否处理空值、零值、负值等？
- [ ] **错误处理**: 是否妥善处理异常？
- [ ] **资源管理**: 是否正确释放资源？

**审查示例**:
```python
# ❌ 未处理边界条件
def divide(a, b):
    return a / b  # b=0时崩溃

# ✅ 处理边界条件
def divide(a: float, b: float) -> Optional[float]:
    """除法运算"""
    if b == 0:
        logger.warning("Division by zero")
        return None
    return a / b

# ❌ 未释放资源
def process_file(path):
    f = open(path)
    data = f.read()
    return process(data)
    # 文件未关闭

# ✅ 正确管理资源
async def process_file(path: Path) -> str:
    """处理文件"""
    async with aiofiles.open(path) as f:
        data = await f.read()
        return await process(data)
```

---

### 4️⃣ 性能与效率 (⭐⭐⭐⭐)

- [ ] **算法复杂度**: 是否使用高效算法？
- [ ] **数据结构**: 是否使用合适的数据结构？
- [ ] **重复计算**: 是否有不必要的重复计算？
- [ ] **数据库查询**: 是否有N+1查询问题？
- [ ] **内存占用**: 是否有内存泄漏风险？

**审查示例**:
```python
# ❌ 低效算法 O(n²)
def has_duplicate(items):
    for i in range(len(items)):
        for j in range(i+1, len(items)):
            if items[i] == items[j]:
                return True
    return False

# ✅ 高效算法 O(n)
def has_duplicate(items: List) -> bool:
    """检查是否有重复项"""
    return len(items) != len(set(items))

# ❌ N+1查询问题
async def get_thread_images(thread_ids):
    results = []
    for tid in thread_ids:
        images = await db.get_images(tid)  # N次查询
        results.extend(images)
    return results

# ✅ 批量查询
async def get_thread_images(thread_ids: List[str]) -> List[Dict]:
    """批量获取帖子图片"""
    return await db.get_images_batch(thread_ids)  # 1次查询
```

---

### 5️⃣ 安全性 (⭐⭐⭐⭐⭐)

- [ ] **输入验证**: 是否验证所有外部输入？
- [ ] **SQL注入**: 是否使用参数化查询？
- [ ] **路径遍历**: 文件路径是否安全？
- [ ] **敏感信息**: 是否泄露敏感信息？
- [ ] **权限检查**: 是否进行权限验证？

**审查示例**:
```python
# ❌ 未验证输入
def download(url):
    return requests.get(url)  # 可能是恶意URL

# ✅ 验证输入
def download(url: str) -> Optional[bytes]:
    """安全下载"""
    parsed = urlparse(url)
    if parsed.scheme not in ['http', 'https']:
        raise ValueError("Invalid URL scheme")
    if not is_allowed_domain(parsed.netloc):
        raise ValueError("Domain not allowed")
    return requests.get(url).content

# ❌ 路径遍历漏洞
def save_file(filename, data):
    with open(f"/data/{filename}", 'wb') as f:
        f.write(data)
    # filename="../../../etc/passwd" 危险！

# ✅ 安全路径处理
def save_file(filename: str, data: bytes, base_dir: Path) -> Path:
    """安全保存文件"""
    # 清理文件名
    safe_name = re.sub(r'[^\w\.-]', '_', filename)
    safe_name = safe_name[:255]
    
    # 确保在基础目录内
    save_path = (base_dir / safe_name).resolve()
    if not save_path.is_relative_to(base_dir):
        raise ValueError("Invalid file path")
    
    save_path.write_bytes(data)
    return save_path
```

---

### 6️⃣ 测试 (⭐⭐⭐⭐⭐)

- [ ] **测试覆盖**: 新增代码是否有测试？
- [ ] **测试质量**: 测试是否覆盖关键场景？
- [ ] **边界测试**: 是否测试边界条件？
- [ ] **异常测试**: 是否测试异常场景？
- [ ] **测试可维护性**: 测试代码是否清晰？

**审查示例**:
```python
# ❌ 测试不充分
def test_divide():
    assert divide(10, 2) == 5

# ✅ 充分的测试
def test_divide():
    """测试除法功能"""
    # 正常情况
    assert divide(10, 2) == 5
    assert divide(7, 3) == pytest.approx(2.333, 0.01)
    
    # 边界情况
    assert divide(0, 5) == 0
    assert divide(10, 0) is None  # 除数为零
    
    # 负数
    assert divide(-10, 2) == -5
    assert divide(10, -2) == -5

@pytest.mark.asyncio
async def test_download_with_retry():
    """测试下载重试机制"""
    with pytest.raises(MaxRetriesExceeded):
        await download("https://invalid-url")
```

---

### 7️⃣ 代码风格 (⭐⭐⭐)

- [ ] **PEP 8遵循**: 是否符合Python风格指南？
- [ ] **一致性**: 与现有代码风格是否一致？
- [ ] **格式化**: 是否通过black/flake8？
- [ ] **导入顺序**: 导入是否规范？

**审查示例**:
```python
# ❌ 不符合PEP 8
import sys,os
from mymodule import *

def myFunction( x,y ):
    if x==y:
        return True
    else:return False

# ✅ 符合PEP 8
import os
import sys
from typing import Any

from mymodule import specific_function


def my_function(x: Any, y: Any) -> bool:
    """比较两个值"""
    return x == y
```

---

## 🔍 审查流程

### Step 1: 宏观审查 (5分钟)
- 浏览PR描述和关联设计文档
- 理解变更目的和范围
- 查看改动的文件列表
- 评估变更规模和影响

### Step 2: 设计审查 (10分钟)
- 验证是否符合设计文档
- 检查架构一致性
- 评估模块职责
- 确认接口设计合理性

### Step 3: 代码审查 (20-30分钟)
- 逐行检查代码
- 关注上述检查清单
- 记录问题和建议
- 给出优先级（Blocking/Non-blocking）

### Step 4: 测试审查 (10分钟)
- 检查测试覆盖率
- 评估测试质量
- 验证测试是否能运行

### Step 5: 给出反馈 (5-10分钟)
- 总结审查意见
- 区分必须修改和建议修改
- 肯定优点
- 给出明确决策

---

## 💬 审查意见模板

```markdown
## 代码审查意见

### 总体评价
[简述代码整体质量，是否符合设计文档]

### 必须修改 (Blocking) ⛔
这些问题必须修改才能合并：

1. **文件名:行号** - 问题描述
   ```python
   # 问题代码
   ```
   **建议**: 如何修改
   **原因**: 为什么必须修改

### 建议修改 (Non-blocking) 💡
这些是优化建议，可以后续改进：

1. **文件名:行号** - 建议内容
   **收益**: 改进后的好处

### 优点 👍
值得肯定的地方：

1. 代码结构清晰
2. 命名规范
3. 文档完善

### 问题统计
- 必须修改: X个
- 建议修改: Y个
- 优点: Z个

### 决策
- [ ] ✅ Approve（批准合并）
- [ ] 🔄 Request Changes（要求修改）
- [ ] 💬 Comment（仅评论，不阻塞）

### 其他说明
[其他需要说明的内容]
```

---

## 📊 审查质量标准

### 优秀的代码审查
- ✅ 发现了潜在bug
- ✅ 提出了架构改进建议
- ✅ 帮助作者提升代码质量
- ✅ 意见清晰、有建设性
- ✅ 及时响应（24小时内）

### 不合格的代码审查
- ❌ 流于形式，仅回复"LGTM"
- ❌ 只挑毛病，不给建议
- ❌ 意见模糊，不清楚如何改进
- ❌ 过于关注细节，忽视重要问题
- ❌ 拖延时间，影响进度

---

## 🎓 审查技巧

### 1. 建设性反馈
```
# ❌ 不好的反馈
"这段代码太烂了"

# ✅ 好的反馈
"这段代码可以通过使用字典推导式简化：
```python
result = {k: v for k, v in items if v > 0}
```
这样可以提高可读性和性能。"
```

### 2. 提问而非命令
```
# ❌ 命令式
"把这个改成异步函数"

# ✅ 提问式
"这个函数会进行网络请求，是否考虑改成异步函数以提高并发性能？"
```

### 3. 肯定优点
```
"这个错误处理逻辑写得很好，考虑了各种边界情况。
不过在L45行，建议添加日志记录以便排查问题。"
```

### 4. 分享知识
```
"这里可以使用Python 3.10+的match-case语法，
会比多个if-elif更清晰：
```python
match status:
    case 'success': handle_success()
    case 'error': handle_error()
    case _: handle_unknown()
```
参考: https://peps.python.org/pep-0634/"
```

---

## 📚 参考资源

- **Google Code Review Guidelines**: https://google.github.io/eng-practices/review/
- **PEP 8 -- Style Guide**: https://peps.python.org/pep-0008/
- **Clean Code**: Robert C. Martin
- **The Pragmatic Programmer**: Andrew Hunt & David Thomas

---

## ⏱️ 审查时间建议

| PR规模 | 代码行数 | 建议审查时间 |
|--------|---------|------------|
| 小 | < 100行 | 15-30分钟 |
| 中 | 100-500行 | 30-60分钟 |
| 大 | 500-1000行 | 1-2小时 |
| 超大 | > 1000行 | 建议拆分 |

**建议**: 每次审查最多2小时，超过则需休息或分批审查。

---

**文档版本**: v1.0  
**最后更新**: 2026-02-03  
**维护者**: Tech Lead
