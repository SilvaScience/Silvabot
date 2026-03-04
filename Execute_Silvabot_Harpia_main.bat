@echo off
echo Starting Silvabot ...
call "%~dp0\.venv_new\Scripts\activate.bat" 
python "%~dp0src\main_Harpia_PC.py"


pause