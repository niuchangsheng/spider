# 安装指南

## 📦 系统要求

- Python 3.7+
- pip (Python包管理器)
- 网络连接

## 🚀 快速安装

### 步骤1：检查Python版本

```bash
python3 --version
```

应该显示 Python 3.7 或更高版本。

### 步骤2：安装pip

如果提示"pip not found"，需要先安装：

```bash
sudo apt update
sudo apt install python3-pip
```

### 步骤3：安装依赖

```bash
cd /home/chang/spider
pip3 install -r requirements.txt
```

## 🔧 其他安装方式

### 方式A：使用虚拟环境（推荐）

```bash
# 1. 创建虚拟环境
cd /home/chang/spider
python3 -m venv venv

# 2. 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行爬虫
python crawl_xindong.py

# 5. 退出虚拟环境（完成后）
deactivate
```

### 方式B：最小依赖安装

如果完整安装失败，可以只安装核心依赖：

```bash
pip3 install requests beautifulsoup4 lxml Pillow aiohttp aiofiles loguru fake-useragent tenacity tqdm pydantic python-dotenv imagehash
```

### 方式C：国内镜像加速

如果下载速度慢，使用清华镜像：

```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## ✅ 验证安装

### 测试1：运行演示版本（无需依赖）

```bash
python3 test_xindong_demo.py
```

应该能看到提取的图片链接。

### 测试2：检查依赖是否安装成功

```bash
python3 -c "import requests, bs4, aiohttp, PIL; print('✓ 核心依赖安装成功！')"
```

### 测试3：运行完整爬虫

```bash
python3 crawl_xindong.py
```

## 🐛 常见问题

### Q1: 提示"pip not found"

```bash
sudo apt install python3-pip
```

### Q2: 提示"Permission denied"

使用 `--user` 参数：

```bash
pip3 install --user -r requirements.txt
```

### Q3: 某些包安装失败

跳过可选依赖，只安装核心包：

```bash
pip3 install requests beautifulsoup4 lxml Pillow aiohttp
```

### Q4: MongoDB/Redis连接失败

数据库是**可选的**，不影响基本功能。如果不需要，可以忽略这些错误。

### Q5: 网络连接超时

使用国内镜像：

```bash
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

## 📊 依赖说明

### 核心依赖（必需）

- `requests` - HTTP请求
- `aiohttp` - 异步HTTP
- `beautifulsoup4` - HTML解析
- `lxml` - XML/HTML解析器
- `Pillow` - 图片处理

### 工具依赖（推荐）

- `loguru` - 日志记录
- `fake-useragent` - UA轮换
- `tenacity` - 重试机制
- `tqdm` - 进度条
- `imagehash` - 图片去重

### 数据库依赖（可选）

- `pymongo` - MongoDB
- `redis` - Redis

如果不需要数据库功能，可以不安装这些。

## 🎯 安装成功后

运行爬虫：

```bash
python3 crawl_xindong.py
```

选择功能1，开始爬取示例帖子！
