@echo off
cd /d "%~dp0frontend"
if not exist ".next\BUILD_ID" (
  echo Run setup-windows.cmd first.
  pause
  exit /b 1
)
call npm.cmd run start
pause
