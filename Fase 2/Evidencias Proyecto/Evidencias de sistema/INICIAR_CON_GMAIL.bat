@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Tienda 3Dedos - Gmail
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 iniciar_gmail.py --port 8767 --abrir
) else (
    python iniciar_gmail.py --port 8767 --abrir
)
pause
