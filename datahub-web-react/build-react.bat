@echo off
echo Building React frontend...
cd /d "%~dp0"
call yarn install
if errorlevel 1 exit /b 1

call yarn build
if errorlevel 1 exit /b 1

echo Build completed successfully!
