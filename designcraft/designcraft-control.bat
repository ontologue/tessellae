@echo off
rem ---------------------------------------------------------------------------
rem  Start DesignCraft with its JSON control channel open.
rem
rem    designcraft-control.bat
rem    designcraft-control.bat 7979
rem    designcraft-control.bat 7979 "C:\path\to\book.idml"
rem
rem  Port defaults to 7979. Set DESIGNCRAFT_EXE to override the search below.
rem  Part of Tessellae - https://github.com/ontologue/tessellae
rem ---------------------------------------------------------------------------

setlocal

rem A first argument made only of digits is the port; anything else is a document.
set "PORT=7979"
set "SHIFTED="
echo %~1| findstr /r "^[0-9][0-9]*$" >nul 2>&1
if not errorlevel 1 (
    set "PORT=%~1"
    set "SHIFTED=yes"
)

rem --- locate the application ------------------------------------------------
set "DC=%DESIGNCRAFT_EXE%"

if not defined DC if exist "%ProgramFiles%\ArtCraft\DesignCraft\designcraft.exe" ^
    set "DC=%ProgramFiles%\ArtCraft\DesignCraft\designcraft.exe"
if not defined DC if exist "%ProgramFiles(x86)%\ArtCraft\DesignCraft\designcraft.exe" ^
    set "DC=%ProgramFiles(x86)%\ArtCraft\DesignCraft\designcraft.exe"
if not defined DC if exist "%LocalAppData%\Programs\ArtCraft\DesignCraft\designcraft.exe" ^
    set "DC=%LocalAppData%\Programs\ArtCraft\DesignCraft\designcraft.exe"

if not defined DC (
    echo DesignCraft was not found in any of the usual locations.
    echo.
    echo Set DESIGNCRAFT_EXE to the full path of designcraft.exe, for example:
    echo     set "DESIGNCRAFT_EXE=D:\Apps\DesignCraft\designcraft.exe"
    echo.
    pause
    exit /b 1
)

if not exist "%DC%" (
    echo DESIGNCRAFT_EXE points at a file that does not exist:
    echo     %DC%
    pause
    exit /b 1
)

rem --- run --------------------------------------------------------------------
if defined SHIFTED shift
start "" "%DC%" --control %PORT% %1 %2 %3 %4 %5 %6 %7 %8

endlocal
