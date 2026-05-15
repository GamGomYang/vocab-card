$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"
$logDir = Join-Path $root "logs"
$edgeProfile = Join-Path $root ".edge-vocab-profile"
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

function Stop-AppProcesses {
  Get-CimInstance Win32_Process -Filter "name = 'powershell.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -like "*Set-Location '*vocab-card\backend'*uvicorn*" -or
      $_.CommandLine -like "*Set-Location '*vocab-card\frontend'*npm run dev*"
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

  Stop-PortProcess -Port 5173
  Stop-PortProcess -Port 8000

  Get-CimInstance Win32_Process -Filter "name = 'node.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -like "*vocab-card\frontend*" -or
      $_.CommandLine -like "*npm-cli.js*run dev*"
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

  Get-CimInstance Win32_Process -Filter "name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -like "*uvicorn*main:app*" -and
      $_.CommandLine -like "*--port 8000*"
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

  Get-CimInstance Win32_Process -Filter "name = 'esbuild.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -like "*vocab-card\frontend*"
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Get-EdgePath {
  $candidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
  )

  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }

  return $null
}

function Get-EdgeAppProcesses {
  Get-CimInstance Win32_Process -Filter "name = 'msedge.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.CommandLine -like "*$edgeProfile*"
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

try {
New-Item -ItemType Directory -Force -Path $edgeProfile | Out-Null

Stop-AppProcesses
Start-Sleep -Milliseconds 500

if (-not (Test-Port -Port 8000)) {
  Start-Process -FilePath $python `
    -WorkingDirectory $backend `
    -WindowStyle Hidden `
    -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000") `
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

$edge = Get-EdgePath
if ($edge) {
  Start-Process -FilePath $edge `
    -ArgumentList @(
      "--app=http://127.0.0.1:5173",
      "--user-data-dir=$edgeProfile",
      "--no-first-run",
      "--disable-extensions"
    )

  for ($i = 0; $i -lt 20; $i++) {
    if (Get-EdgeAppProcesses) {
      break
    }
    Start-Sleep -Milliseconds 500
  }

  while (Get-EdgeAppProcesses) {
    Start-Sleep -Seconds 1
  }
} else {
  Start-Process "http://127.0.0.1:5173"
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show(
    "Close this message after you close the browser to stop Vocab Card servers.",
    "Vocab Card App",
    "OK",
    "Information"
  ) | Out-Null
}
} finally {
  Stop-AppProcesses
}
