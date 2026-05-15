$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$logDir = Join-Path $root "logs"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-Port {
  param([int] $Port)

  try {
    $socket = New-Object Net.Sockets.TcpClient
    $socket.Connect("127.0.0.1", $Port)
    $socket.Close()
    return $true
  } catch {
    return $false
  }
}

if (-not (Test-Path -LiteralPath $python)) {
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show(
    "Backend virtual environment was not found.`nExpected: $python",
    "Vocab Card App",
    "OK",
    "Error"
  ) | Out-Null
  exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
  Start-Process -FilePath "npm.cmd" `
    -WorkingDirectory $frontend `
    -Wait `
    -WindowStyle Hidden `
    -ArgumentList @("install") `
    -RedirectStandardOutput (Join-Path $logDir "npm-install-$stamp.out.log") `
    -RedirectStandardError (Join-Path $logDir "npm-install-$stamp.err.log")
}

if (-not (Test-Port -Port 8000)) {
  Start-Process -FilePath $python `
    -WorkingDirectory $backend `
    -WindowStyle Hidden `
    -ArgumentList @("-m", "uvicorn", "main:app", "--reload", "--host", "127.0.0.1", "--port", "8000") `
    -RedirectStandardOutput (Join-Path $logDir "backend-$stamp.out.log") `
    -RedirectStandardError (Join-Path $logDir "backend-$stamp.err.log")
}

if (-not (Test-Port -Port 5173)) {
  Start-Process -FilePath "npm.cmd" `
    -WorkingDirectory $frontend `
    -WindowStyle Hidden `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") `
    -RedirectStandardOutput (Join-Path $logDir "frontend-$stamp.out.log") `
    -RedirectStandardError (Join-Path $logDir "frontend-$stamp.err.log")
}

for ($i = 0; $i -lt 20; $i++) {
  if (Test-Port -Port 5173) {
    break
  }
  Start-Sleep -Milliseconds 500
}

Start-Process "http://127.0.0.1:5173"
