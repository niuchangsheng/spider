#!/bin/bash
# BBS论坛爬虫启动脚本（v2.4 - CLI 精简）
# 自动激活虚拟环境并运行
#
# 使用示例:
#   ./run_spider.sh                                    # 默认: crawl --config xindong
#   ./run_spider.sh crawl --config xindong --max-pages 5
#   ./run_spider.sh crawl --config sxd --download-images
#   ./run_spider.sh crawl-bbs "https://bbs.xd.com/forum.php?mod=viewthread&tid=123" --type thread --config xindong
#   ./run_spider.sh crawl-bbs "https://bbs.xd.com/forum.php?mod=forumdisplay&fid=21" --type board --config xindong --max-pages 5
#   ./run_spider.sh crawl-news "https://sxd.xd.com/" --download-images --max-pages 5
#   ./run_spider.sh checkpoint-status --site sxd.xd.com --board all
#   CONFIG=xindong SUBCOMMAND=crawl ./run_spider.sh    # 使用环境变量
#
# 环境变量:
#   CONFIG      - 配置文件名 (默认: xindong)
#   SUBCOMMAND  - 子命令 (默认: crawl)
#
# v2.4 子命令:
#   crawl             - 按 config 爬取全部 urls（BBS/新闻由 config 决定）
#   crawl-bbs         - BBS 单帖或单板块（位置参数 URL + --type thread|board）
#   crawl-news        - 动态新闻单页（位置参数 URL；全量用 crawl --config sxd）
#   checkpoint-status - 查看/清除检查点（--site 必填）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 优先使用 .venv，其次 venv
VENV_DIR=
if [ -d ".venv" ]; then
    VENV_DIR=".venv"
elif [ -d "venv" ]; then
    VENV_DIR="venv"
fi

if [ -z "$VENV_DIR" ]; then
    echo "⚠️  虚拟环境不存在，开始创建..."
    if ! python3 -m venv --help &> /dev/null; then
        echo ""
        echo "❌ python3-venv 未安装"
        echo "请先运行: sudo apt install python3.12-venv"
        echo ""
        exit 1
    fi
    echo "正在创建虚拟环境 (.venv)..."
    python3 -m venv .venv
    VENV_DIR=".venv"
    echo "✓ 虚拟环境创建成功"
    echo ""
fi

echo "=========================================="
echo "🕷️  BBS论坛爬虫启动脚本 (v2.4 - CLI 精简)"
echo "=========================================="
echo ""

# 激活虚拟环境
echo "正在激活虚拟环境 ($VENV_DIR)..."
source "$VENV_DIR/bin/activate"

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

# 默认参数（v2.4）
CONFIG="${CONFIG:-xindong}"
SUBCOMMAND="${SUBCOMMAND:-crawl}"

# 支持传入命令行参数
if [ $# -gt 0 ]; then
    echo "▶️  运行命令: python spider.py $@"
    echo ""
    python spider.py "$@"
else
    echo "▶️  运行命令: python spider.py $SUBCOMMAND --config $CONFIG"
    echo ""
    echo "💡 提示:"
    echo "   • 环境变量: CONFIG=xindong SUBCOMMAND=crawl ./run_spider.sh"
    echo "   • 直接传参: ./run_spider.sh crawl --config xindong --max-pages 5"
    echo "   • BBS 单帖: ./run_spider.sh crawl-bbs \"URL\" --type thread --config xindong"
    echo "   • BBS 板块: ./run_spider.sh crawl-bbs \"URL\" --type board --config xindong --max-pages 5"
    echo "   • 新闻: ./run_spider.sh crawl --config sxd --download-images"
    echo "   • 检查点: ./run_spider.sh checkpoint-status --site sxd.xd.com --board all"
    echo "   • 帮助: ./run_spider.sh --help"
    echo ""
    python spider.py "$SUBCOMMAND" --config "$CONFIG"
fi

# 退出虚拟环境
deactivate

echo ""
echo "=========================================="
echo "✅ 爬虫运行完成"
echo "=========================================="
