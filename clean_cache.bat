@echo off
echo 清理 Python 缓存...
echo.

REM 删除所有 __pycache__ 目录
for /d /r %%i in (__pycache__) do (
    if exist "%%i" (
        echo 删除: %%i
        rmdir /s /q "%%i"
    )
)

REM 删除所有 .pyc 文件
del /s /q *.pyc 2>nul

echo.
echo 缓存清理完成！
echo.
pause
