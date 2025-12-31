@echo off
REM ============================================================================
REM VanityMask Quick Test Suite
REM ============================================================================
REM Runs fast tests (~2-3 minutes) for CI/development verification
REM Tests 8-32 bit difficulty across all modes
REM
REM Requirements:
REM   - Python 3.10+
REM   - pip install ecdsa
REM   - NVIDIA GPU with nvidia-smi
REM   - VanitySearch.exe built in x64\Release
REM ============================================================================

setlocal enabledelayedexpansion

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Set VanitySearch executable path
set "VANITYSEARCH=%PROJECT_ROOT%\x64\Release\VanitySearch.exe"

REM Check if VanitySearch exists
if not exist "%VANITYSEARCH%" (
    echo ERROR: VanitySearch.exe not found at:
    echo   %VANITYSEARCH%
    echo.
    echo Please build the project first:
    echo   1. Open VanityMask.sln in Visual Studio
    echo   2. Build in Release x64 configuration
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Install Python 3.10+ and add to PATH
    exit /b 1
)

REM Check ecdsa module
python -c "import ecdsa" >nul 2>&1
if errorlevel 1 (
    echo WARNING: ecdsa module not found, installing...
    pip install ecdsa
    if errorlevel 1 (
        echo ERROR: Failed to install ecdsa module
        exit /b 1
    )
)

REM Check nvidia-smi
nvidia-smi --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: nvidia-smi not found - GPU monitoring disabled
    set "NO_GPU_MONITOR=1"
)

echo ============================================================================
echo VanityMask Quick Test Suite
echo ============================================================================
echo.
echo Executable: %VANITYSEARCH%
echo Test Mode:  Quick (~2-3 minutes)
echo.
echo Tests included:
echo   - MASK mode: 8, 16, 24, 32-bit prefixes
echo   - ECDSA sig mode: 8, 16, 32-bit R.x prefixes
echo   - Schnorr sig mode: 8, 16, 32-bit R.x prefixes
echo   - TXID mode: 8, 16-bit prefixes
echo   - Error handling validation
echo   - GPU utilization spot checks
echo.
echo ============================================================================
echo.

REM Change to tests directory
cd /d "%SCRIPT_DIR%"

REM Run quick tests
echo Starting quick tests at %TIME%
echo.

python comprehensive_test_suite.py --quick --exe "%VANITYSEARCH%"
set "TEST_EXIT_CODE=%ERRORLEVEL%"

echo.
echo ============================================================================
echo Quick tests completed at %TIME%
echo Exit code: %TEST_EXIT_CODE%
echo ============================================================================

if %TEST_EXIT_CODE% equ 0 (
    echo.
    echo ALL TESTS PASSED
) else (
    echo.
    echo SOME TESTS FAILED - Check output above for details
)

exit /b %TEST_EXIT_CODE%
