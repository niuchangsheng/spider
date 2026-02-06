#!/bin/bash
# BBS论坛爬虫启动脚本（v2.3 - 文件结构重构）
# 自动激活虚拟环境并运行
#
# 使用示例:
#   ./run_spider.sh                                    # 默认: crawl-urls --config xindong
#   ./run_spider.sh crawl-boards --config xindong     # 爬取所有板块
#   ./run_spider.sh crawl-url "https://..." --auto-detect  # 爬取单个URL
#   ./run_spider.sh crawl-news "https://sxd.xd.com/" --download-images  # 爬取动态新闻页面
#   CONFIG=xindong SUBCOMMAND=crawl-boards ./run_spider.sh # 使用环境变量
#
# 环境变量:
#   CONFIG      - 配置文件名 (默认: xindong)
#   SUBCOMMAND  - 子命令 (默认: crawl-urls)
#
# v2.3 子命令:
#   crawl-url       - 爬取单个URL (BBS帖子)
#   crawl-urls      - 爬取配置中的URL列表
#   crawl-board     - 爬取单个板块
#   crawl-boards    - 爬取配置中的所有板块
#   crawl-news      - 爬取动态新闻/公告页面

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "🕷️  BBS论坛爬虫启动脚本 (v2.3 - 文件结构重构)"
echo "=========================================="
echo ""

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "⚠️  虚拟环境不存在，开始创建..."
    
    # 检查 python3-venv 是否安装
    if ! python3 -m venv --help &> /dev/null; then
        echo ""
        echo "❌ python3-venv 未安装"
        echo ""
        echo "请先运行以下命令："
        echo "  sudo apt install python3.12-venv"
        echo ""
        exit 1
    fi
    
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
    echo ""
fi

# 激活虚拟环境
echo "正在激活虚拟环境..."
source venv/bin/activate

# 检查依赖是否安装
if ! python -c "import requests" 2>/dev/null; then
    echo ""
    echo "⚠️  依赖包未安装，开始安装..."
    echo ""
    pip install -r requirements.txt
    echo ""
    echo "✓ 依赖安装完成"
    echo ""
fi

# 运行爬虫
echo "=========================================="
echo "🚀 启动爬虫..."
echo "=========================================="
echo ""

# 默认参数（v2.1 子命令模式）
CONFIG="${CONFIG:-xindong}"
SUBCOMMAND="${SUBCOMMAND:-crawl-urls}"  # 默认子命令

# 支持传入命令行参数
if [ $# -gt 0 ]; then
    # 如果有参数，直接传递给 spider.py
    echo "▶️  运行命令: python spider.py $@"
    echo ""
    python spider.py "$@"
else
    # 否则使用默认配置（v2.1 子命令模式）
    echo "▶️  运行命令: python spider.py $SUBCOMMAND --config $CONFIG"
    echo ""
    echo "💡 提示:"
    echo "   • 使用环境变量: CONFIG=xindong SUBCOMMAND=crawl-boards ./run_spider.sh"
    echo "   • 直接传参: ./run_spider.sh crawl-boards --config xindong --max-pages 5"
    echo "   • 动态页面: ./run_spider.sh crawl-news \"https://sxd.xd.com/\" --download-images"
    echo "   • 查看帮助: ./run_spider.sh --help"
    echo ""
    python spider.py "$SUBCOMMAND" --config "$CONFIG"
fi

# 退出虚拟环境
deactivate

echo ""
echo "=========================================="
echo "✅ 爬虫运行完成"
echo "=========================================="
