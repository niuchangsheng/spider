#!/bin/bash
# BBS论坛爬虫启动脚本（v2.0）
# 自动激活虚拟环境并运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================="
echo "BBS论坛爬虫启动脚本 (v2.0)"
echo "=================================="
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
echo "=================================="
echo "启动爬虫..."
echo "=================================="
echo ""

# 默认参数
PRESET="${PRESET:-xindong}"
MODE="${MODE:-1}"

# 支持传入命令行参数
if [ $# -gt 0 ]; then
    # 如果有参数，直接传递给 spider.py
    echo "运行命令: python spider.py $@"
    python spider.py "$@"
else
    # 否则使用默认配置
    echo "运行命令: python spider.py --preset $PRESET --mode $MODE"
    echo "提示: 可以设置环境变量 PRESET 和 MODE 来改变默认行为"
    echo "      或直接传参: ./run_spider.sh --preset xindong --mode 2"
    echo ""
    python spider.py --preset "$PRESET" --mode "$MODE"
fi

# 退出虚拟环境
deactivate

echo ""
echo "=================================="
echo "爬虫运行完成"
echo "=================================="
