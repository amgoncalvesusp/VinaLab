@echo off
setlocal enabledelayedexpansion
echo ============================================
echo  VinaLab Build Pipeline
echo  Autor: Adriano Marques Goncalves - UNIARA
echo ============================================

set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" set "PYTHON_EXE=.venv\Scripts\python.exe"

:: Step 1 - Generate logo if missing
if not exist "ui\icon.ico" (
    echo [1/4] Gerando logotipo - molecula de cafeina 3D...
    "%PYTHON_EXE%" ui\generate_logo.py
    if errorlevel 1 (
        echo ERRO: Falha ao gerar o logotipo. Verifique matplotlib e Pillow.
        pause & exit /b 1
    )
    echo       Logo gerado com sucesso.
) else (
    echo [1/4] Logotipo ja existe - ignorando geracao.
)

:: Step 2 - Run unit tests
echo [2/4] Executando testes...
if exist "tests" (
    "%PYTHON_EXE%" -m pytest --version >nul 2>nul
    if errorlevel 1 (
        echo      Pytest nao instalado - etapa de testes ignorada.
    ) else (
        "%PYTHON_EXE%" -m pytest tests/ -q --tb=short
        if errorlevel 1 (
            echo AVISO: Alguns testes falharam. Continuando o build...
        )
    )
) else (
    echo      Pasta tests nao encontrada - etapa de testes ignorada.
)

:: Step 3 - Compile translations (future .qm support placeholder)
echo [3/4] Compilando recursos de interface...
"%PYTHON_EXE%" -c "from core.i18n import I18n; I18n.validate_all_keys(); print('  Todas as chaves i18n validadas.')"
if errorlevel 1 (
    echo ERRO: Falha na validacao das traducoes.
    pause & exit /b 1
)

:: Step 4 - PyInstaller
echo [4/4] Empacotando com PyInstaller...
"%PYTHON_EXE%" -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo      Instalando PyInstaller no ambiente local...
    "%PYTHON_EXE%" -m pip install pyinstaller
    if errorlevel 1 (
        echo ERRO: Falha ao instalar PyInstaller no ambiente local.
        pause & exit /b 1
    )
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean VinaLab.spec

if errorlevel 1 (
    echo ERRO: PyInstaller falhou. Verifique os logs acima.
    pause & exit /b 1
)

echo.
echo ============================================
echo  BUILD CONCLUIDO COM SUCESSO
echo  Arquivo: dist\VinaLab.exe
echo  Autor  : Adriano Marques Goncalves - UNIARA
echo ============================================
pause
