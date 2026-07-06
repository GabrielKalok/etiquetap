@echo off
title EtiqueTAP - Instalando dependencias
cd /d "%~dp0"

echo Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Python nao encontrado.
    echo Baixe em: https://www.python.org/downloads/
    echo Marque "Add Python to PATH" na instalacao!
    pause
    exit /b
)

echo Instalando dependencias...
pip install pywin32 --quiet
pip install psycopg2-binary --quiet

echo Iniciando EtiqueTAP...
python etiqueta_gestaoclick.py
