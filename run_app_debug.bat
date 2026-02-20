@echo off
cd /d %~dp0

call .\.venv-runtime\Scripts\activate.bat

set "POKER_DEBUG_LOG=run_app_debug.log"
set "POKER_LOG_LEVEL=DEBUG"

echo. > "%POKER_DEBUG_LOG%"
echo ==== %date% %time% ==== >> "%POKER_DEBUG_LOG%"

.\.venv-runtime\Scripts\python.exe -u main.py 1>>"%POKER_DEBUG_LOG%" 2>>&1


set "EC=%ERRORLEVEL%"
echo [debug.bat] exit code=%EC% >> "%POKER_DEBUG_LOG%"
type "%POKER_DEBUG_LOG%" | clip || echo [warn] failed to copy log to clipboard
echo [debug.bat] log copied to clipboard
pause
