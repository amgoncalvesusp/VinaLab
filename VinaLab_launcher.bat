@echo off
python launcher.py
if %errorlevel% neq 0 (
    echo ERRO: Python nao encontrado. Instale Python 3.10+ em https://www.python.org
    pause
)
