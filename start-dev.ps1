$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Start-Process powershell -WindowStyle Hidden -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\backend'; .\.venv\Scripts\python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
)

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\frontend'; npm run dev -- --host 127.0.0.1 --port 5173"
)

Start-Sleep -Seconds 5
Start-Process "http://127.0.0.1:5173"

Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host "Frontend: http://localhost:5173"
