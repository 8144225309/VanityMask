@echo off
REM ============================================================================
REM VanityMask Full Test Suite
REM ============================================================================
REM Runs comprehensive tests (~90 minutes) for full verification
REM Includes 40-bit difficulty tests and full GPU monitoring
REM
REM Requirements:
REM   - Python 3.10+
REM   - pip install ecdsa
REM   - NVIDIA GPU with nvidia-smi
REM   - VanitySearch.exe built in x64\Release
REM   - ~2 hours of uninterrupted GPU time
REM ============================================================================

setlocal enabledelayedexpansion

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Set VanitySearch executable path
set "VANITYSEARCH=%PROJECT_ROOT%\x64\Release\VanitySearch.exe"

REM Output directory for results
set "RESULTS_DIR=%SCRIPT_DIR%results"
if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

REM Timestamp for result files
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "DATETIME=%%I"
set "TIMESTAMP=%DATETIME:~0,8%_%DATETIME:~8,6%"
set "RESULT_FILE=%RESULTS_DIR%\full_test_%TIMESTAMP%.json"

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
    echo ERROR: nvidia-smi not found
    echo Full test suite requires GPU monitoring
    echo Ensure NVIDIA drivers are installed
    exit /b 1
)

REM Display GPU info
echo ============================================================================
echo GPU Information
echo ============================================================================
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo.

echo ============================================================================
echo VanityMask Full Test Suite
echo ============================================================================
echo.
echo Executable:   %VANITYSEARCH%
echo Test Mode:    Full (~90 minutes)
echo Results:      %RESULT_FILE%
echo.
echo Tests included:
echo.
echo   MASK MODE:
echo     - 8, 16, 24, 32-bit prefixes (quick)
echo     - 40-bit prefix (~41 seconds)
echo     - Custom mask patterns
echo     - Edge cases (00000000, FFFFFFFF)
echo.
echo   ECDSA SIGNATURE MODE:
echo     - 8, 16, 32-bit R.x prefixes (quick)
echo     - 40-bit R.x prefix (~41 seconds)
echo     - Full s-value verification
echo     - Low-s normalization (BIP-146)
echo.
echo   SCHNORR SIGNATURE MODE:
echo     - 8, 16, 32-bit R.x prefixes (quick)
echo     - 40-bit R.x prefix (~41 seconds)
echo     - BIP-340 challenge verification
echo.
echo   TXID MODE:
echo     - 8, 16-bit prefixes (quick)
echo     - 24-bit prefix (~27 seconds)
echo     - Custom nonce offset/length
echo.
echo   GPU VERIFICATION:
echo     - Continuous utilization monitoring
echo     - Target: 95%% for EC ops, 62%% for TXID
echo     - Performance regression detection
echo.
echo   ERROR HANDLING:
echo     - Invalid input validation
echo     - Boundary condition testing
echo.
echo ============================================================================
echo.
echo WARNING: This test suite takes ~90 minutes to complete.
echo          Ensure GPU is not in use by other applications.
echo.
echo Press Ctrl+C to cancel, or
pause

REM Change to tests directory
cd /d "%SCRIPT_DIR%"

REM Record start time
set "START_TIME=%TIME%"
echo.
echo ============================================================================
echo Starting full tests at %START_TIME%
echo ============================================================================
echo.

REM Run full tests with JSON output
python comprehensive_test_suite.py --full --exe "%VANITYSEARCH%" --output "%RESULT_FILE%"
set "TEST_EXIT_CODE=%ERRORLEVEL%"

REM Record end time
set "END_TIME=%TIME%"

echo.
echo ============================================================================
echo Full tests completed
echo ============================================================================
echo.
echo Start time:  %START_TIME%
echo End time:    %END_TIME%
echo Exit code:   %TEST_EXIT_CODE%
echo Results:     %RESULT_FILE%
echo.

if %TEST_EXIT_CODE% equ 0 (
    echo ============================================================================
    echo                         ALL TESTS PASSED
    echo ============================================================================
    echo.
    echo GPU utilization targets met:
    echo   - EC operations: 95%%+ average utilization
    echo   - TXID operations: 55%%+ average utilization
    echo.
    echo All cryptographic verifications passed:
    echo   - Mask mode: pubkey X prefix matching
    echo   - ECDSA: r = R.x, s = k^-1*(z+r*d) mod N, low-s normalized
    echo   - Schnorr: r = R.x, s = k + e*d mod N
    echo   - TXID: SHA256(SHA256(tx)) prefix matching
) else (
    echo ============================================================================
    echo                        SOME TESTS FAILED
    echo ============================================================================
    echo.
    echo Check the results file for details:
    echo   %RESULT_FILE%
    echo.
    echo Common issues:
    echo   - GPU utilization below target (thermal throttling?)
    echo   - Cryptographic verification failed (bug in output)
    echo   - Timeout (GPU slower than expected)
)

echo.
exit /b %TEST_EXIT_CODE%
