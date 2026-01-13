@echo off
chcp 65001 > nul
echo ============================================================
echo Genos Pipeline - Custom Test Runner
echo ============================================================

if "%~1"=="" (
    echo Usage: run_custom_test.bat [vcf_file_path]
    echo Example: run_custom_test.bat examples/subset_test.vcf
    exit /b 1
)

set INPUT_VCF=%~1
set RUN_NAME=%~n1_test

echo.
echo [1/3] Cleaning cache...
if exist "runs\%RUN_NAME%" rmdir /s /q "runs\%RUN_NAME%" > nul 2>&1

echo [2/3] Running analysis on %INPUT_VCF%...
python main.py ^
    --vcf "%INPUT_VCF%" ^
    --output "runs/%RUN_NAME%" ^
    --sample "custom_test" 

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo Test Failed
    echo ============================================================
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Analysis Complete!
echo Output Directory: runs\%RUN_NAME%
echo Report File: runs\%RUN_NAME%\report.html
echo.
echo ============================================================
pause
