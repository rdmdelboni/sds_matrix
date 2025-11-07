param(
  [string]$TargetPath = "",
  [string]$ShortcutPath = "",
  [string]$IconPath = ""
)

$ErrorActionPreference = "Stop"

# Resolve defaults:
# 1) If dist/fds-reader.exe exists, prefer it
# 2) Else try to find the fds-reader console entry on PATH
if (-not $TargetPath -or -not (Test-Path $TargetPath)) {
  $distExe = Join-Path (Get-Location) "dist/fds-reader.exe"
  if (Test-Path $distExe) {
    $TargetPath = (Resolve-Path $distExe).Path
  } else {
    $cmd = Get-Command fds-reader -ErrorAction SilentlyContinue
    if ($cmd) {
      $TargetPath = $cmd.Source
    } else {
      throw "Nao foi possivel localizar o destino. Informe -TargetPath para o EXE ou garanta que 'fds-reader' esteja no PATH."
    }
  }
}

# Shortcut on Desktop by default
if (-not $ShortcutPath) {
  $desktop = [Environment]::GetFolderPath("Desktop")
  $ShortcutPath = Join-Path $desktop "FDS Reader.lnk"
}

Write-Host "Criando atalho: $ShortcutPath" -ForegroundColor Cyan

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.Arguments = ""
$Shortcut.WorkingDirectory = Split-Path -Path $TargetPath -Parent
if ($IconPath -and (Test-Path $IconPath)) {
  $Shortcut.IconLocation = (Resolve-Path $IconPath).Path
}
$Shortcut.Save()

Write-Host "Atalho criado com sucesso." -ForegroundColor Green
