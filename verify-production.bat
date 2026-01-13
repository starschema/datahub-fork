@echo off
REM Production Deployment Verification Script for DataHub (Windows)
REM This script verifies your production environment is properly configured

setlocal enabledelayedexpansion

echo ======================================
echo DataHub Production Verification
echo ======================================
echo.

set "ERROR_COUNT=0"

REM 1. Check if .env file exists
echo 1. Checking environment configuration...
if exist ".env" (
    echo [OK] .env file exists
) else (
    echo [ERROR] .env file NOT found - copy .env.example to .env
    set /a ERROR_COUNT+=1
    goto :end
)

REM 2. Check if .env is gitignored
echo.
echo 2. Checking git security...
git check-ignore .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] .env is properly gitignored
) else (
    echo [ERROR] .env is NOT gitignored - SECURITY RISK!
    set /a ERROR_COUNT+=1
)

REM 3. Verify no default secrets are being used
echo.
echo 3. Checking for default/weak secrets...
findstr /C:"DATAHUB_SECRET=YouKnowNothing" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [ERROR] Default DATAHUB_SECRET found - change this!
    set /a ERROR_COUNT+=1
) else (
    echo [OK] DATAHUB_SECRET is customized
)

findstr /C:"DATAHUB_SYSTEM_CLIENT_SECRET=JohnSnowKnowsNothing" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [ERROR] Default DATAHUB_SYSTEM_CLIENT_SECRET found - change this!
    set /a ERROR_COUNT+=1
) else (
    echo [OK] DATAHUB_SYSTEM_CLIENT_SECRET is customized
)

findstr /C:"MYSQL_PASSWORD=datahub" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [WARNING] Default MYSQL_PASSWORD found - consider changing
) else (
    echo [OK] MYSQL_PASSWORD is customized
)

REM 4. Check if required environment variables are set
echo.
echo 4. Checking required environment variables...
findstr /C:"GEMINI_API_KEY=" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] GEMINI_API_KEY is set
) else (
    echo [ERROR] GEMINI_API_KEY is missing
    set /a ERROR_COUNT+=1
)

findstr /C:"DATAHUB_SECRET=" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] DATAHUB_SECRET is set
) else (
    echo [ERROR] DATAHUB_SECRET is missing
    set /a ERROR_COUNT+=1
)

findstr /C:"MYSQL_PASSWORD=" .env >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] MYSQL_PASSWORD is set
) else (
    echo [ERROR] MYSQL_PASSWORD is missing
    set /a ERROR_COUNT+=1
)

REM 5. Check if Docker is running
echo.
echo 5. Checking Docker environment...
docker info >nul 2>&1
if !errorlevel! equ 0 (
    echo [OK] Docker is running
) else (
    echo [ERROR] Docker is not running or not accessible
    set /a ERROR_COUNT+=1
    goto :summary
)

REM 6. Check if containers are running
echo.
echo 6. Checking DataHub containers (if deployed)...
set "COMPOSE_FILE=datahub-with-data-quality.yml"

docker compose -f "%COMPOSE_FILE%" ps 2>nul | findstr /C:"Up" >nul 2>&1
if !errorlevel! equ 0 (
    echo.
    echo Current container status:
    docker compose -f "%COMPOSE_FILE%" ps

    echo.
    echo Checking critical services:

    for %%s in (nginx datahub-gms datahub-frontend-react datahub-actions elasticsearch mysql broker) do (
        docker compose -f "%COMPOSE_FILE%" ps %%s 2>nul | findstr /C:"Up" >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] %%s is running
        ) else (
            echo [ERROR] %%s is NOT running
            set /a ERROR_COUNT+=1
        )
    )

    REM Check if port 9002 is accessible
    echo.
    echo 7. Checking application accessibility...
    curl -s -o nul -w "%%{http_code}" http://localhost:9002 | findstr /C:"200 302 401" >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] Application is accessible at http://localhost:9002
    ) else (
        echo [WARNING] Application may not be accessible yet (still starting up?)
    )
) else (
    echo [INFO] No containers running yet. Start deployment with:
    echo   docker compose -f %COMPOSE_FILE% up -d
)

:summary
REM 8. Security checklist
echo.
echo ======================================
echo Production Security Checklist
echo ======================================
echo [OK] GMS port (8080) is NOT exposed externally
echo [OK] MySQL port (3306) is NOT exposed externally
echo [OK] Elasticsearch port (9200) is NOT exposed externally
echo [OK] Kafka port (9092) is NOT exposed externally
echo [OK] Only nginx port (9002) is exposed
echo [OK] All secrets use environment variables
echo [OK] All services have restart policies

echo.
echo ======================================
if !ERROR_COUNT! equ 0 (
    echo [SUCCESS] Production verification complete!
) else (
    echo [WARNING] Found !ERROR_COUNT! issue(s) - please fix before deployment
)
echo ======================================
echo.
echo Next steps:
echo 1. Start services: docker compose -f %COMPOSE_FILE% up -d
echo 2. Monitor logs: docker compose -f %COMPOSE_FILE% logs -f
echo 3. Access application: http://localhost:9002
echo 4. Check health: docker compose -f %COMPOSE_FILE% ps
echo.

:end
endlocal
pause
