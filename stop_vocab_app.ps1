$ErrorActionPreference = "SilentlyContinue"

function Stop-PortProcess {
  param([int] $Port)

  Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    Where-Object { $_ -gt 0 } |
    ForEach-Object {
      Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
      taskkill.exe /PID $_ /F | Out-Null
    }
}

Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -like "*Set-Location '*vocab-card\backend'*uvicorn*" -or
    $_.CommandLine -like "*Set-Location '*vocab-card\frontend'*npm run dev*" -or
    $_.CommandLine -like "*uvicorn*main:app*--port 8000*" -or
    $_.CommandLine -like "*vocab-card\frontend\node_modules*" -or
    $_.CommandLine -like "*.edge-vocab-profile*"
  } |
  ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }

Stop-PortProcess -Port 5173
Stop-PortProcess -Port 8000

Write-Host "Vocab Card processes stopped."
