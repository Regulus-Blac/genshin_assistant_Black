@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在安装 Black 的 Python 依赖...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo 安装失败。请确认 Python 3.10+ 与网络连接正常，然后重试。
) else (
    echo.
    echo 安装完成。双击 启动Black.bat 即可。
)
echo.
pause
