@echo off
echo ============================================================
echo Genos 多智能体基因组分析系统 - 测试运行
echo ============================================================
echo.

echo [1/3] 清理 Python 缓存...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc >nul 2>&1

echo [2/3] 运行分析流程...
python main.py --vcf examples\test.vcf --output runs\test --sample demo

echo.
echo [3/3] 检查输出文件...
if exist runs\test\report.md (
    echo ✓ 分析报告已生成: runs\test\report.md
    echo.
    echo 查看报告内容:
    type runs\test\report.md
) else (
    echo ✗ 报告生成失败
)

echo.
echo ============================================================
echo 测试完成
echo ============================================================
pause
