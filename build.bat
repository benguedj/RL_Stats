@echo off
rem Construit dist\RL Stats.exe et dist\RL Stats.zip (exe + notices)
setlocal
cd /d "%~dp0"

if not exist .venv (
    python -m venv .venv || goto :error
)
call .venv\Scripts\activate.bat
python -m pip install --quiet -r requirements.txt -r requirements-build.txt || goto :error

pyinstaller --noconfirm rl_stats.spec || goto :error

copy /y packaging\README.txt dist\ >nul
copy /y packaging\LISEZMOI.txt dist\ >nul
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\RL Stats.exe','dist\README.txt','dist\LISEZMOI.txt' -DestinationPath 'dist\RL Stats.zip'" || goto :error

echo.
echo OK : dist\RL Stats.exe et dist\RL Stats.zip
exit /b 0

:error
echo Echec du build.
exit /b 1
