$ErrorActionPreference = "Stop"

Write-Host "== Build (Excel -> JSON) =="
.\.venv-build\Scripts\python -m tools.build_final_tags_json

Write-Host "== Run (runtime) =="
.\.venv-runtime\Scripts\python main.py
