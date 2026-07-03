@echo off
:: Windows Test Runner for PythonAnywhere CWA Crawler
:: Executes the standalone script and displays its log output

set LOCAL_PATH=%~dp0
cd /d %LOCAL_PATH%

echo ==================================================
echo       Testing: cwa_crawler_pa.py
echo ==================================================
echo.
echo [*] Preparing to run cwa_crawler_pa.py ...

if not exist cwa_crawler_pa.py (
    echo [!] Error: cwa_crawler_pa.py not found!
    goto error
)

if not exist config.json (
    echo [!] Warning: config.json not found.
    echo [*] The script will create a template config.json.
)

echo [*] Running Python crawler script...
echo --------------------------------------------------
python cwa_crawler_pa.py
echo --------------------------------------------------
echo.
echo [+] Execution finished.
goto end

:error
echo.
echo [!] Execution failed. Please check the project directory.

:end
echo.
pause
