@echo off
title Lia — Agregar al inicio
chcp 65001 >nul

:: Ejecutar el script Python con el mismo intérprete que tiene Lia
:: %~dp0 = directorio de este .bat (scripts/)
set "SCRIPT=%~dp0lia_agregar_inicio.py"

:: Buscar Python (py launcher primero, luego python directo)
where py >nul 2>&1
if %errorlevel%==0 (
    py "%SCRIPT%"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        python "%SCRIPT%"
    ) else (
        echo ERROR: No se encontro Python en el PATH.
        echo Instala Python desde https://python.org
        pause
        exit /b 1
    )
)

pause
