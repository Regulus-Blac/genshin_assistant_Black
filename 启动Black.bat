@echo off
setlocal
cd /d "%~dp0"
where pythonw.exe >nul 2>nul
if errorlevel 1 goto fallback
start "" pythonw.exe "%~dp0run_black.pyw"
exit /b 0

:fallback
where python.exe >nul 2>nul
if errorlevel 1 goto missing
python.exe "%~dp0run_black.pyw"
exit /b %errorlevel%

:missing
echo Python was not found. Please install Python 3.10+ first.
pause
exit /b 1
