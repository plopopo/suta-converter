@echo off
setlocal
cd /d "%~dp0"
python -m PyInstaller --onefile --name "SUTA Converter Console" suta_txt_to_csv.py
echo.
echo If the build succeeded, the EXE is in the dist folder:
echo dist\SUTA Converter Console.exe
pause
