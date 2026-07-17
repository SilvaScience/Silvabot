@echo off
setlocal

REM Get the directory where this batch file is located
set "BASEDIR=%~dp0"

REM Activate the virtual environment
call "%BASEDIR%.venv\Scripts\activate.bat"

REM Run the Python script
python "%BASEDIR%src\main.py"

REM Optional: keep window open
pause