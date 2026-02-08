#!/bin/bash
# 运行单元测试脚本（确保在虚拟环境下运行）
# 支持生成覆盖率报告

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# 解析命令行参数
GENERATE_COVERAGE=false
COVERAGE_HTML=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage|-c)
            GENERATE_COVERAGE=true
            shift
            ;;
        --html|-h)
            GENERATE_COVERAGE=true
            COVERAGE_HTML=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            echo "用法: $0 [--coverage|-c] [--html|-h]"
            echo "  --coverage, -c  生成覆盖率报告（文本格式）"
            echo "  --html, -h      生成覆盖率报告（HTML格式，包含文本格式）"
            exit 1
            ;;
    esac
done

# 检查 venv，不存在则创建
if [ ! -d "venv" ]; then
    echo "⚠️  venv 不存在，正在创建..."
    if ! python3 -m venv --help &>/dev/null; then
        echo "❌ 请先安装: sudo apt install python3.12-venv"
        exit 1
    fi
    python3 -m venv venv
    echo "✓ 已创建 venv"
fi

echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ 错误: 未能激活虚拟环境"
    exit 1
fi

echo "✅ 虚拟环境已激活: $VIRTUAL_ENV"
echo ""

# 若缺少依赖则安装（便于刚创建 venv 后直接跑测试）
if ! python -c "import pydantic" 2>/dev/null; then
    echo "📦 安装依赖..."
    pip install -q -r requirements.txt
    echo "✓ 依赖安装完成"
    echo ""
fi

# 如果启用覆盖率，检查并安装 coverage
if [ "$GENERATE_COVERAGE" = true ]; then
    if ! python -c "import coverage" 2>/dev/null; then
        echo "📦 安装 coverage 包..."
        pip install -q coverage
    fi
    echo "📊 启用覆盖率分析..."
    echo ""
fi

# 确保项目根目录在 Python 路径中
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

# 运行测试
echo "🧪 运行单元测试..."
cd "$PROJECT_ROOT"

if [ "$GENERATE_COVERAGE" = true ]; then
    # 使用 coverage 运行测试
    coverage run -m unittest discover -s tests -p "test_*.py" -v -t "$PROJECT_ROOT"
    TEST_EXIT_CODE=$?
    
    echo ""
    echo "============================================================"
    echo "📊 生成覆盖率报告"
    echo "============================================================"
    echo ""
    
    # 生成文本格式覆盖率报告
    echo "📄 文本格式覆盖率报告:"
    echo "------------------------------------------------------------"
    coverage report --show-missing
    echo ""
    
    # 如果启用HTML报告，生成HTML格式
    if [ "$COVERAGE_HTML" = true ]; then
        HTML_DIR="${PROJECT_ROOT}/htmlcov"
        echo "🌐 生成HTML格式覆盖率报告..."
        coverage html -d "$HTML_DIR"
        echo "✅ HTML报告已生成: file://${HTML_DIR}/index.html"
        echo ""
    fi
    
    # 保存退出码
    EXIT_CODE=$TEST_EXIT_CODE
else
    # 不使用覆盖率，直接运行测试
    python -m unittest discover -s tests -p "test_*.py" -v -t "$PROJECT_ROOT"
    EXIT_CODE=$?
fi

# 退出虚拟环境
deactivate

exit $EXIT_CODE
