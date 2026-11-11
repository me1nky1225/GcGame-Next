@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [GCM Next] 未找到虚拟环境，正在创建...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
)
".venv\Scripts\python.exe" main.py %*
goto :eof

:fail
echo [GCM Next] 启动失败，请检查上面的错误信息。
pause
