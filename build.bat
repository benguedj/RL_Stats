@echo off
rem Construit dist\RL Overlay.exe et dist\RL Overlay.zip (exe + notices)
setlocal
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat
python -m pip install --quiet -r requirements.txt pyinstaller==6.22.3 || goto :error

pyinstaller --noconfirm rl_overlay.spec || goto :error

copy /y packaging\README.txt dist\ >nul
copy /y packaging\LISEZMOI.txt dist\ >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\RL Overlay.exe','dist\README.txt','dist\LISEZMOI.txt' -DestinationPath 'dist\RL Overlay.zip'" || goto :error

echo.
echo OK : dist\RL Overlay.exe et dist\RL Overlay.zip
exit /b 0

:error
echo Echec du build.
exit /b 1
