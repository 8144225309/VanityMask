@echo off
setlocal enabledelayedexpansion

REM VanityMask Comprehensive Test Suite
REM Tests all grinding modes and verifies cryptographic correctness

set SCRIPT_DIR=%~dp0
set VANITY=%SCRIPT_DIR%..\x64\Release\VanitySearch.exe
set VERIFY=python "%SCRIPT_DIR%verify_results.py"
set PASSED=0
set FAILED=0
set TOTAL=0

echo ============================================
echo   VanityMask Test Suite v1.20
echo ============================================
echo.

REM Check if VanitySearch exists
if not exist "%VANITY%" (
    echo ERROR: VanitySearch.exe not found at %VANITY%
    echo Please build the project first.
    exit /b 1
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.
    exit /b 1
)

echo [PREP] Running Python verification self-tests...
%VERIFY% test
if errorlevel 1 (
    echo ERROR: Python verification self-tests failed!
    exit /b 1
)
echo.

REM ===========================================
REM MASK MODE TESTS
REM ===========================================
echo ============================================
echo   MASK MODE TESTS
echo ============================================
echo.

REM Test MASK-01: 1-byte prefix
set /a TOTAL+=1
echo [MASK-01] Testing 1-byte prefix (00)...
%VANITY% -gpu -mask -tx 00 --prefix 1 -stop > mask01_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    type mask01_output.txt
    set /a FAILED+=1
) else (
    REM Extract private key from output
    for /f "tokens=3" %%a in ('findstr /c:"Priv (HEX):" mask01_output.txt') do set PRIVKEY=%%a
    if defined PRIVKEY (
        set PRIVKEY=!PRIVKEY:0x=!
        echo   Found privkey: !PRIVKEY:~0,16!...
        %VERIFY% mask !PRIVKEY! 00
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract private key
        type mask01_output.txt
        set /a FAILED+=1
    )
)
echo.

REM Test MASK-02: 2-byte prefix
set /a TOTAL+=1
echo [MASK-02] Testing 2-byte prefix (dead)...
%VANITY% -gpu -mask -tx dead --prefix 2 -stop > mask02_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    set /a FAILED+=1
) else (
    for /f "tokens=3" %%a in ('findstr /c:"Priv (HEX):" mask02_output.txt') do set PRIVKEY=%%a
    if defined PRIVKEY (
        set PRIVKEY=!PRIVKEY:0x=!
        echo   Found privkey: !PRIVKEY:~0,16!...
        %VERIFY% mask !PRIVKEY! dead
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract private key
        set /a FAILED+=1
    )
)
echo.

REM Test MASK-03: 4-byte prefix (takes longer, ~0.16 sec expected)
set /a TOTAL+=1
echo [MASK-03] Testing 4-byte prefix (deadbeef) - may take a moment...
%VANITY% -gpu -mask -tx deadbeef --prefix 4 -stop > mask03_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    set /a FAILED+=1
) else (
    for /f "tokens=3" %%a in ('findstr /c:"Priv (HEX):" mask03_output.txt') do set PRIVKEY=%%a
    if defined PRIVKEY (
        set PRIVKEY=!PRIVKEY:0x=!
        echo   Found privkey: !PRIVKEY:~0,16!...
        %VERIFY% mask !PRIVKEY! deadbeef
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract private key
        set /a FAILED+=1
    )
)
echo.

REM ===========================================
REM SIGNATURE MODE TESTS
REM ===========================================
echo ============================================
echo   SIGNATURE MODE TESTS
echo ============================================
echo.

set MSG_HASH=0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20
set SIGN_KEY=0000000000000000000000000000000000000000000000000000000000000001

REM Test SIG-01: ECDSA 1-byte prefix
set /a TOTAL+=1
echo [SIG-01] Testing ECDSA signature with 1-byte R.x prefix (00)...
%VANITY% -gpu -sig -tx 00 --prefix 1 -z %MSG_HASH% -d %SIGN_KEY% -stop > sig01_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    type sig01_output.txt
    set /a FAILED+=1
) else (
    REM Extract nonce, r, s from output
    for /f "tokens=2" %%a in ('findstr /c:"Nonce (k):" sig01_output.txt') do set NONCE=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.r:" sig01_output.txt') do set SIG_R=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.s:" sig01_output.txt') do set SIG_S=%%a
    if defined NONCE if defined SIG_R if defined SIG_S (
        echo   Found nonce: !NONCE:~0,16!...
        echo   Found r:     !SIG_R:~0,16!...
        echo   Found s:     !SIG_S:~0,16!...
        %VERIFY% sig !NONCE! %MSG_HASH% %SIGN_KEY% !SIG_R! !SIG_S!
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract signature values
        type sig01_output.txt
        set /a FAILED+=1
    )
)
echo.

REM Test SIG-02: ECDSA 2-byte prefix
set /a TOTAL+=1
echo [SIG-02] Testing ECDSA signature with 2-byte R.x prefix (dead)...
%VANITY% -gpu -sig -tx dead --prefix 2 -z %MSG_HASH% -d %SIGN_KEY% -stop > sig02_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    set /a FAILED+=1
) else (
    for /f "tokens=2" %%a in ('findstr /c:"Nonce (k):" sig02_output.txt') do set NONCE=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.r:" sig02_output.txt') do set SIG_R=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.s:" sig02_output.txt') do set SIG_S=%%a
    if defined NONCE if defined SIG_R if defined SIG_S (
        echo   Found nonce: !NONCE:~0,16!...
        %VERIFY% sig !NONCE! %MSG_HASH% %SIGN_KEY% !SIG_R! !SIG_S!
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract signature values
        set /a FAILED+=1
    )
)
echo.

REM Test SIG-03: Schnorr 1-byte prefix
set /a TOTAL+=1
echo [SIG-03] Testing Schnorr signature with 1-byte R.x prefix (00)...
%VANITY% -gpu -sig -tx 00 --prefix 1 -z %MSG_HASH% -d %SIGN_KEY% --schnorr -stop > sig03_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    type sig03_output.txt
    set /a FAILED+=1
) else (
    for /f "tokens=2" %%a in ('findstr /c:"Nonce (k):" sig03_output.txt') do set NONCE=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.r:" sig03_output.txt') do set SIG_R=%%a
    for /f "tokens=2" %%a in ('findstr /c:"sig.s:" sig03_output.txt') do set SIG_S=%%a
    if defined NONCE if defined SIG_R (
        echo   Found nonce: !NONCE:~0,16!...
        echo   Found r:     !SIG_R:~0,16!...
        %VERIFY% sig !NONCE! %MSG_HASH% %SIGN_KEY% !SIG_R! !SIG_S! --schnorr
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract signature values
        type sig03_output.txt
        set /a FAILED+=1
    )
)
echo.

REM ===========================================
REM TXID MODE TESTS
REM ===========================================
echo ============================================
echo   TXID MODE TESTS
echo ============================================
echo.

REM Minimal valid transaction structure (59 bytes, nLockTime at bytes 55-58)
set RAW_TX=0100000001000000000000000000000000000000000000000000000000000000000000000000000000ffffffff0100000000000000000000000000

REM Test TXID-01: 1-byte prefix
set /a TOTAL+=1
echo [TXID-01] Testing TXID mode with 1-byte prefix (00)...
%VANITY% -gpu -txid -raw %RAW_TX% -tx 00 --prefix 1 -stop > txid01_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    type txid01_output.txt
    set /a FAILED+=1
) else (
    REM Extract nonce from output
    for /f "tokens=2" %%a in ('findstr /c:"Nonce:" txid01_output.txt') do set TXNONCE=%%a
    for /f "tokens=2" %%a in ('findstr /c:"TXID:" txid01_output.txt') do set TXID=%%a
    if defined TXNONCE (
        set TXNONCE=!TXNONCE:0x=!
        echo   Found nonce: !TXNONCE!
        echo   Found TXID:  !TXID:~0,16!...
        REM Default nonce position is last 4 bytes (offset 55, len 4)
        %VERIFY% txid %RAW_TX% !TXNONCE! 55 4 00
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract nonce
        type txid01_output.txt
        set /a FAILED+=1
    )
)
echo.

REM Test TXID-02: 2-byte prefix
set /a TOTAL+=1
echo [TXID-02] Testing TXID mode with 2-byte prefix (00)...
%VANITY% -gpu -txid -raw %RAW_TX% -tx 0000 --prefix 2 -stop > txid02_output.txt 2>&1
if errorlevel 1 (
    echo   SKIP: VanitySearch returned error
    set /a FAILED+=1
) else (
    for /f "tokens=2" %%a in ('findstr /c:"Nonce:" txid02_output.txt') do set TXNONCE=%%a
    for /f "tokens=2" %%a in ('findstr /c:"TXID:" txid02_output.txt') do set TXID=%%a
    if defined TXNONCE (
        set TXNONCE=!TXNONCE:0x=!
        echo   Found nonce: !TXNONCE!
        echo   Found TXID:  !TXID:~0,16!...
        %VERIFY% txid %RAW_TX% !TXNONCE! 55 4 0000
        if errorlevel 1 (
            echo   FAILED: Verification failed
            set /a FAILED+=1
        ) else (
            echo   PASSED
            set /a PASSED+=1
        )
    ) else (
        echo   FAILED: Could not extract nonce
        set /a FAILED+=1
    )
)
echo.

REM ===========================================
REM BUILT-IN CHECK
REM ===========================================
echo ============================================
echo   BUILT-IN EC VERIFICATION
echo ============================================
echo.

set /a TOTAL+=1
echo [CHECK] Running built-in -check flag...
%VANITY% -check > check_output.txt 2>&1
findstr /c:"Check ok" check_output.txt >nul
if errorlevel 1 (
    echo   FAILED: Built-in check failed
    type check_output.txt
    set /a FAILED+=1
) else (
    echo   PASSED: Built-in EC verification passed
    set /a PASSED+=1
)
echo.

REM ===========================================
REM SUMMARY
REM ===========================================
echo ============================================
echo   TEST SUMMARY
echo ============================================
echo.
echo   Total:  %TOTAL%
echo   Passed: %PASSED%
echo   Failed: %FAILED%
echo.

if %FAILED% equ 0 (
    echo   ALL TESTS PASSED!
    exit /b 0
) else (
    echo   SOME TESTS FAILED - Review output above
    exit /b 1
)
