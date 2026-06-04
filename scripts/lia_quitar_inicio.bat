@echo off
title Lia — Quitar del inicio
chcp 65001 >nul

set "SCRIPT=%~dp0lia_quitar_inicio.py"

where py >nul 2>&1
if %errorlevel%==0 (
    py "%SCRIPT%"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        python "%SCRIPT%"
    ) else (
        echo ERROR: No se encontro Python en el PATH.
        pause
        exit /b 1
    )
)

pause
