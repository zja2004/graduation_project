@echo off
REM 快速激活 uv 虚拟环境的便捷脚本

echo.
echo ========================================
echo   Genos 多智能体基因组分析系统
echo   激活虚拟环境...
echo ========================================
echo.

REM 激活虚拟环境
call .venv\Scripts\activate.bat

echo ✓ 虚拟环境已激活！
echo.
echo 快速开始:
echo   python test_system.py              # 测试系统
echo   python main.py --vcf examples/test.vcf --sample demo  # 运行示例
echo.
echo 查看帮助:
echo   python main.py --help
echo.
