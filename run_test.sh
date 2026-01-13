#!/bin/bash
echo "========================================"
echo "Genos 多智能体系统 - 快速测试"
echo "========================================"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python 3，请先安装"
    exit 1
fi

echo "[1/3] 检查依赖..."
python3 -c "import yaml, numpy, pandas, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 正在安装依赖..."
    pip3 install pyyaml numpy pandas requests pyarrow
fi

echo ""
echo "[2/3] 运行测试分析..."
python3 main.py --vcf examples/test.vcf --output runs/test_run --sample demo --log-level INFO

echo ""
echo "[3/3] 测试完成！"
echo ""
echo "输出目录: runs/test_run"
echo "查看报告: runs/test_run/report.md"
echo ""
