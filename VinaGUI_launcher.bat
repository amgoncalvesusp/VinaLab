@echo off
python launcher.py
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python 3.10+ from https://www.python.org
    pause
)
