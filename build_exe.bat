@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pyinstaller --noconfirm --clean --windowed --name LAN-Toolkit --add-data "data\oui.csv;data" --add-data "data\mam.csv;data" --add-data "data\oui36.csv;data" main.py
echo EXE 已生成到 dist\LAN-Toolkit\

