@echo off
echo Starting Silvabot ...

call "%~dp0\.venv_new\Scripts\activate.bat" 
python "%~dp0\src\main.py"

pause