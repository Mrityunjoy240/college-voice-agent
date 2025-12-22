@echo off
echo ========================================
echo Starting College Voice Agent
echo ========================================
echo.

echo Starting Backend Server...
start "Backend Server" cmd /k "%~dp0start-backend.bat"

timeout /t 5 /nobreak > nul

echo Starting Frontend Server...
start "Frontend Server" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak > nul

echo.
echo ========================================
echo Servers Starting!
echo ========================================
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Opening browser in 5 seconds...
timeout /t 5 /nobreak > nul

start http://localhost:5173

echo.
echo To stop the servers, close the terminal windows.
echo.
