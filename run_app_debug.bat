@echo off
cd /d %~dp0

call .\.venv-runtime\Scripts\activate.bat

set "POKER_DEBUG_LOG=run_app_debug.log"

echo ==== %date% %time% ==== >> run_app_debug.log

.\.venv-runtime\Scripts\pythonw.exe main.py


echo [debug.bat] exit code=%ERRORLEVEL% >> run_app_debug.log
pause
