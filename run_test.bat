@echo off
echo ========================================
echo Genos 多智能体系统 - 快速测试
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
python -c "import yaml, numpy, pandas, requests" 2>nul
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install pyyaml numpy pandas requests pyarrow
)

echo.
echo [2/3] 运行测试分析...
python main.py --vcf examples\test.vcf --output runs\test_run --sample demo --log-level INFO

echo.
echo [3/3] 测试完成！
echo.
echo 输出目录: runs\test_run
echo 查看报告: runs\test_run\report.md
echo.
pause
