@echo off
REM VanityMask Full Benchmark Suite
REM Runs ~30 minutes of comprehensive benchmarks
REM

echo ============================================================
echo VanityMask Full Benchmark Suite
echo ============================================================
echo WARNING: This will take approximately 30 minutes
echo.
echo Press Ctrl+C to cancel, or
pause

cd /d "%~dp0"

python benchmark_suite.py --full

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo *** BENCHMARK FAILED - Performance regression detected! ***
    exit /b 1
)

echo.
echo *** All benchmarks completed successfully ***
exit /b 0
