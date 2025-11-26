@echo off
set NODE_OPTIONS=--max-old-space-size=5120 --openssl-legacy-provider
set CI=false

echo Building React frontend...
cd /d "%~dp0"
call npx yarn generate
if errorlevel 1 exit /b 1

call npx vite build
if errorlevel 1 exit /b 1

echo Build completed successfully!
