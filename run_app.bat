@echo off
cd /d %~dp0

call .\.venv-runtime\Scripts\activate.bat

REM 追記ログ（毎回消さない）
echo ==== %date% %time% ==== >> run_app.log

REM start を使わず、そのまま実行してリダイレクトを確実に効かせる
.\.venv-runtime\Scripts\pythonw.exe main.py >> run_app.log 2>&1
