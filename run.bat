@echo off
REM 全能办公工具箱 - 启动脚本
REM Uses Anaconda Python (required for PySide6 DLL compatibility)

set ANACONDA_PYTHON=D:\ruanjian\ANACONDA\python.exe

if not exist "%ANACONDA_PYTHON%" (
    echo [ERROR] Anaconda Python not found at %ANACONDA_PYTHON%
    echo Please update ANACONDA_PYTHON path in run.bat
    pause
    exit /b 1
)

cd /d "%~dp0"
"%ANACONDA_PYTHON%" main.py
pause
