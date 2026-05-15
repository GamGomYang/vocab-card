$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = Join-Path $root "dist\VocabCardDesktop.exe"
$icon = $target
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutName = [string]::Concat([char]0xB2E8, [char]0xC5B4, " ", [char]0xD14C, [char]0xC2A4, [char]0xD2B8, ".lnk")
$shortcutPath = Join-Path $desktop $shortcutName

if (-not (Test-Path -LiteralPath $target)) {
  throw "Launcher was not found: $target"
}

if (-not (Test-Path -LiteralPath $icon)) {
  throw "Icon was not found: $icon"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.Arguments = ""
$shortcut.WorkingDirectory = $root
$shortcut.WindowStyle = 7
$shortcut.Description = "Start the word test app"
$shortcut.IconLocation = "$icon,0"
$shortcut.Save()

Write-Host "Created desktop shortcut: $shortcutPath"
