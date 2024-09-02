@echo off
setlocal

set PID=%1

if "%PID%"=="" (
    echo No PID provided.
    exit /b 1
)

net session >nul 2>&1
if errorlevel 1 (
    powershell -Command "Start-Process cmd -ArgumentList '/c %~s0 %PID%' -Verb RunAs -Wait"
)


tasklist | findstr %PID% >nul
if errorlevel 1 (
    echo The process with PID %PID% does not exist.
    exit /b 1
)

set "OUTPUT="
for /f "tokens=*" %%i in ('wmic process where "ProcessId=%PID%" get ExecutablePath ^| findstr /v "^$"') do (
    set "OUTPUT=%%i"
)

if defined OUTPUT (
    echo Executable Path: %OUTPUT%
) else (
    echo No executable path found for PID %PID%.
)

exit /b 0
