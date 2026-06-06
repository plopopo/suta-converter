@echo off
setlocal
cd /d "%~dp0"
python "%~dp0suta_txt_to_csv.py" --guided
echo.
pause
