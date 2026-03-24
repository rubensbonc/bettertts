@echo off
setlocal enabledelayedexpansion

REM Always run from the folder where this script lives
cd /d "%~dp0"

echo ============================================
echo   BetterTTS - Local Build
echo ============================================
echo.

REM ── Ask for build mode ──
echo Build mode:
echo   [1] Release  — copies app\ into dist (for distribution)
echo   [2] Dev      — symlinks app\ into dist (edit files live, no rebuild)
echo.
set /p "BUILD_MODE=Choose mode (1 or 2, default=1): "
if "!BUILD_MODE!"=="" set "BUILD_MODE=1"
if "!BUILD_MODE!"=="2" (
    echo.
    echo   DEV MODE — app\ will be symlinked into dist\BetterTTS\
    echo   Changes to app\ files take effect immediately without rebuilding.
    echo.
    set "IS_DEV=1"
) else (
    set "IS_DEV=0"
)

REM ── Check venv exists ──
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Please run setup.bat first!
    echo.
    pause
    exit /b 1
)

REM ── Check Python version in venv ──
echo Checking Python version...
for /f "tokens=2 delims= " %%v in ('venv\Scripts\python.exe --version 2^>^&1') do set "PYVER=%%v"
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if "!PY_MAJOR!" neq "3" (
    echo ERROR: Python 3.10-3.12 required, found !PYVER!
    pause
    exit /b 1
)
if !PY_MINOR! GTR 12 (
    echo ERROR: Python 3.10-3.12 required, found !PYVER!
    echo Please recreate your venv with Python 3.12.
    pause
    exit /b 1
)
echo   Found Python !PYVER! - OK
echo.

REM ── Check icon exists ──
if not exist "icon.ico" (
    echo WARNING: icon.ico not found in project root.
    echo The exe will be built without a custom icon.
    echo.
    set "ICON_FLAG="
) else (
    set "ICON_FLAG=--icon=icon.ico"
)

REM ── Check required files exist ──
if not exist "profiles.json" (
    echo ERROR: profiles.json not found.
    pause
    exit /b 1
)
if not exist "app\launcher.py" (
    echo ERROR: app\launcher.py not found.
    pause
    exit /b 1
)
if not exist "app\update_helper.py" (
    echo ERROR: app\update_helper.py not found.
    pause
    exit /b 1
)
if not exist "requirements_build.txt" (
    echo ERROR: requirements_build.txt not found.
    pause
    exit /b 1
)

REM ── Ask for version (release mode only) ──
if "!IS_DEV!"=="0" (
    echo.
    set /p "VERSION=Enter version number (e.g. 1.0.0) or press Enter to skip: "
    if "!VERSION!"=="" (
        echo Skipping version file.
    ) else (
        echo !VERSION!> version.txt
        echo   Written version.txt = !VERSION!
    )
    echo.
)

REM ── Clean previous build ──
echo [1/5] Cleaning previous build...
if exist "dist" (
    echo   Removing dist\...
    rmdir /s /q "dist" 2>nul
    if exist "dist" (
        echo ERROR: Could not remove dist\ - is BetterTTS.exe still running?
        pause
        exit /b 1
    )
)
if exist "build" rmdir /s /q "build"
echo   Done.
echo.

REM ── Install build-only dependencies ──
echo [2/5] Installing build dependencies (lightweight — no PyTorch)...
venv\Scripts\pip.exe install -r requirements_build.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install build dependencies.
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Build main exe ──
echo [3/5] Building BetterTTS.exe...
venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name BetterTTS ^
    !ICON_FLAG! ^
    --collect-all=customtkinter ^
    app\launcher.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed building BetterTTS.exe
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Build update helper ──
echo [4/5] Building update_helper.exe...
venv\Scripts\python.exe -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name update_helper ^
    --collect-all=customtkinter ^
    app\update_helper.py

if errorlevel 1 (
    echo ERROR: PyInstaller failed building update_helper.exe
    pause
    exit /b 1
)
echo   Done.
echo.

REM ── Create output folder and copy/link files ──
echo [5/5] Setting up runtime files...
if not exist "dist\BetterTTS" mkdir "dist\BetterTTS"
if exist "dist\BetterTTS.exe" move /y "dist\BetterTTS.exe" "dist\BetterTTS\" >nul
copy /y "dist\update_helper.exe"               "dist\BetterTTS\" >nul
copy /y "profiles.json"                        "dist\BetterTTS\" >nul
copy /y "requirements.txt"                     "dist\BetterTTS\" >nul
if exist "icon.ico"                            copy /y "icon.ico"                         "dist\BetterTTS\" >nul
if exist "version.txt"                         copy /y "version.txt"                      "dist\BetterTTS\" >nul
if exist "BetterTTS_Streamerbot_Import.txt"    copy /y "BetterTTS_Streamerbot_Import.txt" "dist\BetterTTS\" >nul
if not exist "dist\BetterTTS\voices"           mkdir "dist\BetterTTS\voices"

if "!IS_DEV!"=="1" (
    REM ── DEV MODE: symlink app\ so edits are reflected immediately ──
    echo   Creating symlink: dist\BetterTTS\app -> %CD%\app
    REM Remove any existing app folder/link in dist first
    if exist "dist\BetterTTS\app" (
        REM Check if it's already a symlink
        fsutil reparsepoint query "dist\BetterTTS\app" >nul 2>&1
        if !errorlevel! equ 0 (
            rmdir "dist\BetterTTS\app" >nul 2>&1
        ) else (
            rmdir /s /q "dist\BetterTTS\app" >nul 2>&1
        )
    )
    mklink /J "dist\BetterTTS\app" "%CD%\app"
    if errorlevel 1 (
        echo.
        echo WARNING: Could not create symlink.
        echo Junction points should work without elevation — try running build.bat as Administrator.
        echo Falling back to copying app\ instead...
        echo.
        xcopy /e /i /y "app" "dist\BetterTTS\app\" >nul
    ) else (
        echo   Symlink created successfully.
        echo   Any changes to app\ files are now live immediately.
    )

    REM Also symlink venv from project root into dist so app can find it
    if not exist "dist\BetterTTS\venv" (
        echo   Creating symlink: dist\BetterTTS\venv -> %CD%\venv
        mklink /J "dist\BetterTTS\venv" "%CD%\venv" >nul 2>&1
        if errorlevel 1 (
            echo   NOTE: Could not symlink venv\, it will need to be set up separately in dist\.
        ) else (
            echo   Symlink venv created.
        )
    )
) else (
    REM ── RELEASE MODE: copy app\ normally ──
    xcopy /e /i /y "app" "dist\BetterTTS\app\" >nul

    REM Remove __pycache__ — not needed for distribution
    for /d /r "dist\BetterTTS" %%d in (__pycache__) do (
        if exist "%%d" rmdir /s /q "%%d"
    )
)

REM ── Clean up PyInstaller junk ──
if exist "dist\BetterTTS\.git"          rmdir /s /q "dist\BetterTTS\.git"
if exist "dist\BetterTTS\build"         rmdir /s /q "dist\BetterTTS\build"
if exist "dist\BetterTTS\.gpu_type"     del /q "dist\BetterTTS\.gpu_type"
if exist "dist\BetterTTS\.startup_in_progress" del /q "dist\BetterTTS\.startup_in_progress"

REM ── Copy any other loose exes from dist\ into BetterTTS\ ──
for %%f in (dist\*.exe) do (
    copy /y "%%f" "dist\BetterTTS\" >nul
)
echo   Done.
echo.

REM ── Zip (release mode only) ──
if "!IS_DEV!"=="0" (
    set /p "DO_ZIP=Zip the output? (Y/N): "
    if /i "!DO_ZIP!"=="Y" (
        if "!VERSION!"=="" (
            set "ZIP_NAME=BetterTTS-windows.zip"
        ) else (
            set "ZIP_NAME=BetterTTS-windows-!VERSION!.zip"
        )
        if exist "!ZIP_NAME!" del "!ZIP_NAME!"
        echo Zipping to !ZIP_NAME!...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "Compress-Archive -Path 'dist\BetterTTS\*' -DestinationPath '!ZIP_NAME!'"
        if errorlevel 1 (
            echo WARNING: Zip failed.
        ) else (
            echo   Created !ZIP_NAME!
        )
    )
    echo.
)

echo ============================================
if "!IS_DEV!"=="1" (
    echo   DEV BUILD complete!
    echo   Output: dist\BetterTTS\BetterTTS.exe
    echo.
    echo   app\ is symlinked — edit files directly and
    echo   relaunch BetterTTS.exe to see changes instantly.
    echo   No rebuild needed for Python file changes.
) else (
    echo   RELEASE BUILD complete!
    echo   Output: dist\BetterTTS\BetterTTS.exe
    echo.
    echo   NOTE: PyTorch is NOT bundled in the exe.
    echo   The setup wizard installs it at first launch.
)
echo ============================================
echo.

REM ── Open output folder ──
explorer "dist\BetterTTS"

pause