@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem The old script pointed straight at run_black.pyw.  If that file ever went
rem missing (sync tools, antivirus, a partial copy) the launcher failed
rem silently because pythonw has no console.  Resolve the entry point first and
rem fall back to app.py, then report a real error instead of doing nothing.
set "ENTRY=%~dp0run_black.pyw"
if not exist "%ENTRY%" set "ENTRY=%~dp0app.py"
if not exist "%ENTRY%" (
    echo [Black] 找不到启动文件 run_black.pyw / app.py。
    echo [Black] 请确认软件目录是完整的，或重新解压一次压缩包。
    pause
    exit /b 1
)

where pythonw.exe >nul 2>nul
if errorlevel 1 goto fallback
start "" pythonw.exe "%ENTRY%"
exit /b 0

:fallback
where python.exe >nul 2>nul
if errorlevel 1 goto missing
echo [Black] 没有找到 pythonw.exe，改用 python.exe 启动（会保留这个窗口）。
python.exe "%ENTRY%"
if errorlevel 1 pause
exit /b %errorlevel%

:missing
echo [Black] 没有找到 Python。请先安装 Python 3.10 或更高版本，再运行「安装依赖.bat」。
pause
exit /b 1
