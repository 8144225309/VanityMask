@echo off
REM VanityMask Quick Benchmark Suite
REM Runs ~5 minutes of benchmarks to verify performance
REM

echo ============================================================
echo VanityMask Quick Benchmark Suite
echo ============================================================
echo.

cd /d "%~dp0"

python benchmark_suite.py --quick

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo *** BENCHMARK FAILED - Performance regression detected! ***
    exit /b 1
)

echo.
echo *** Benchmarks completed successfully ***
exit /b 0
