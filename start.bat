@echo off
setlocal

set "ROOT=%~dp0"
set "PORT=5800"
set "HOST=127.0.0.1"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "URL=http://%HOST%:%PORT%"
set "OPEN_URL=%URL%/?v=%RANDOM%%RANDOM%"

if not exist "%PYTHON%" (
  echo [Mylody] Python runtime not found: %PYTHON%
  pause
  exit /b 1
)

echo [Mylody] Stopping existing service on %HOST%:%PORT% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$owners = Get-NetTCPConnection -LocalPort %PORT% -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -ne 0 } | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($owner in $owners) { try { Stop-Process -Id $owner -Force -ErrorAction Stop; Write-Host ('Stopped PID ' + $owner) } catch {} }"

timeout /t 1 /nobreak >nul

echo [Mylody] Starting service...
start "Mylody Service" /min "%PYTHON%" "%ROOT%main.py" --no-tray

echo [Mylody] Waiting for service...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url = '%URL%/api/status'; $ready = $false; for ($i = 0; $i -lt 30; $i++) { try { Invoke-RestMethod -Uri $url -TimeoutSec 1 | Out-Null; $ready = $true; break } catch { Start-Sleep -Milliseconds 500 } }; if (-not $ready) { exit 1 }"

if errorlevel 1 (
  echo [Mylody] Service did not become ready. Check logs in the project folder.
  pause
  exit /b 1
)

echo [Mylody] Opening %OPEN_URL% ...
start "" "%OPEN_URL%"

endlocal
