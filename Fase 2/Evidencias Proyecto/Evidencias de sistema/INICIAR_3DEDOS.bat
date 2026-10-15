@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Tienda 3Dedos - Mantener abierta esta ventana
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 servidor.py --port 8767 --abrir
) else (
    python servidor.py --port 8767 --abrir
)
if errorlevel 1 (
    echo.
    echo No se pudo iniciar. Revisa el mensaje anterior.
)
pause
