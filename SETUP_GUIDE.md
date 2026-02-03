# 环境设置指南

您遇到了 `externally-managed-environment` 错误，这是 Python 3.12+ 的保护机制。

## 🎯 解决方案（推荐：使用虚拟环境）

### 步骤1：安装 python3-venv

```bash
sudo apt install python3.12-venv
```

### 步骤2：创建虚拟环境

```bash
cd /home/chang/spider
python3 -m venv venv
```

### 步骤3：激活虚拟环境

```bash
source venv/bin/activate
```

激活后，命令行前面会显示 `(venv)`

### 步骤4：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤5：运行爬虫

```bash
python crawl_xindong.py
```

### 步骤6：退出虚拟环境（完成后）

```bash
deactivate
```

---

## 📋 完整命令（复制执行）

```bash
# 1. 安装venv包（需要密码）
sudo apt install python3.12-venv

# 2. 创建并激活虚拟环境
cd /home/chang/spider
python3 -m venv venv
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行爬虫
python crawl_xindong.py
```

---

## 🔧 其他解决方案

### 方案A：使用 pipx（简单）

```bash
# 安装 pipx
sudo apt install pipx

# 使用 pipx 运行（会自动管理虚拟环境）
pipx run crawl_xindong.py
```

### 方案B：使用 --user 参数（不推荐）

```bash
pip3 install --user -r requirements.txt
```

### 方案C：最小依赖安装（临时方案）

如果以上都不行，可以先用演示版本：

```bash
# 演示版本不需要安装依赖
python3 test_xindong_demo.py
```

然后手动安装最少的包：

```bash
sudo apt install python3-requests python3-bs4 python3-pil python3-aiohttp
```

---

## ⚠️ 不推荐的方案

**使用 --break-system-packages**（可能破坏系统）：

```bash
# ❌ 不推荐！可能导致系统问题
pip3 install --break-system-packages -r requirements.txt
```

---

## 🎯 推荐流程（虚拟环境）

虚拟环境的优点：
- ✅ 不污染系统 Python
- ✅ 可以安装任意版本的包
- ✅ 多个项目互不影响
- ✅ 可以随时删除重建

### 创建一次，每次使用前激活即可

```bash
# 第一次创建（只需一次）
cd /home/chang/spider
sudo apt install python3.12-venv
python3 -m venv venv

# 以后每次使用前激活
source venv/bin/activate

# 使用完毕后退出
deactivate
```

---

## 📝 快速启动脚本

为了方便，我创建了一个启动脚本：

```bash
# 使用启动脚本（自动激活虚拟环境）
./run_spider.sh
```

---

## 🐛 故障排查

### Q: 提示 "python3-venv not found"

```bash
sudo apt update
sudo apt install python3.12-venv
```

### Q: 虚拟环境激活后没有显示 (venv)

没关系，检查 Python 路径：

```bash
which python
# 应该显示: /home/chang/spider/venv/bin/python
```

### Q: 安装某个包失败

跳过失败的包，只安装核心依赖：

```bash
pip install requests beautifulsoup4 lxml Pillow aiohttp aiofiles loguru fake-useragent
```

---

## ✅ 验证安装

```bash
# 在虚拟环境中
python -c "import requests, bs4, aiohttp; print('✓ 安装成功！')"
```

---

## 🎉 开始使用

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 运行爬虫
python crawl_xindong.py

# 3. 选择功能1
```

图片会自动下载到 `downloads/` 目录！
