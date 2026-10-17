@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ================================================================
rem External-folder WIPI Runner Windows builder
rem - Always captures stdout + stderr.
rem - last_build.log is overwritten on every build.
rem - last_build(YYYYMMDD-HHMMSS).log is kept as a timestamped copy.
rem - Both logs are written beside this BAT and the output ROM.
rem ================================================================

if /I "%~1"=="__BUILD_CORE" goto :BUILD_CORE

set "STAMP="
for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss" 2^>nul') do set "STAMP=%%I"
if not defined STAMP (
    set "STAMP=%DATE%_%TIME%"
    set "STAMP=!STAMP:/=-!"
    set "STAMP=!STAMP::=-!"
    set "STAMP=!STAMP:.=-!"
    set "STAMP=!STAMP: =0!"
    set "STAMP=!STAMP:,=-!"
)

set "TMPLOG=%TEMP%\ZLOM_build_%RANDOM%_%RANDOM%.log"
call "%~f0" __BUILD_CORE >"%TMPLOG%" 2>&1
set "RC=%ERRORLEVEL%"

type "%TMPLOG%"
copy /y "%TMPLOG%" "%~dp0last_build.log" >nul
copy /y "%TMPLOG%" "%~dp0last_build(%STAMP%).log" >nul

echo.
echo [LOG] %~dp0last_build.log
echo [LOG] %~dp0last_build(%STAMP%).log
if "%RC%"=="0" (
    echo [BUILD RESULT] SUCCESS
) else (
    echo [BUILD RESULT] FAILED - errorlevel %RC%
)

del /q "%TMPLOG%" >nul 2>&1
exit /b %RC%

:BUILD_CORE
setlocal EnableExtensions
cd /d "%~dp0"

if "%DEVKITPRO%"=="" set "DEVKITPRO=C:\devkitPro"
if "%DEVKITARM%"=="" set "DEVKITARM=%DEVKITPRO%\devkitARM"
set "PATH=%DEVKITARM%\bin;%DEVKITPRO%\tools\bin;%PATH%"

echo ================================================================
echo Zenonia 2 DS Runner - external /zenonia2nds/
echo ================================================================
echo [TIME] %DATE% %TIME%
echo [DIR]  %CD%
echo [DEVKITPRO] %DEVKITPRO%
echo [DEVKITARM] %DEVKITARM%
echo.

where make >nul 2>&1
if errorlevel 1 (
    echo [ERROR] make not found in PATH
    exit /b 10
)
where arm-none-eabi-g++ >nul 2>&1
if errorlevel 1 (
    echo [ERROR] arm-none-eabi-g++ / devkitARM not found in PATH
    exit /b 11
)
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 12
)

echo [TOOLCHAIN]
arm-none-eabi-g++ --version
echo.

echo [1/4] make clean
make clean
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo [FAIL] make clean returned %RC%
    exit /b %RC%
)

echo.
echo [2/4] make -j2
make -j2
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo [FAIL] compiler/linker returned %RC%
    exit /b %RC%
)

if not exist "Zenonia 2 DS Runner.nds" (
    echo [ERROR] Build returned success but Zenonia 2 DS Runner.nds was not created
    exit /b 20
)

echo.
echo [3/4] patch NDS header
python tools\patch_nds_header.py "Zenonia 2 DS Runner.nds"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo [FAIL] patch_nds_header.py returned %RC%
    exit /b %RC%
)

echo.
echo [4/4] output ROM ready
for %%F in ("Zenonia 2 DS Runner.nds") do echo [ROM] %%~fF  [%%~zF bytes]
echo [OK] Zenonia 2 DS Runner.nds  [ID: #### / FAT ZKR1.sav]
echo [SUCCESS] Build completed with no errors.
exit /b 0
