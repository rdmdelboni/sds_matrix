param(
    [switch]$Clean
)

# Build a single-file Windows EXE for FDS Reader
Write-Host "Building standalone EXE (PyInstaller)..."

$ErrorActionPreference = "Stop"

if ($Clean) {
  if (Test-Path dist) { Remove-Item dist -Recurse -Force }
  if (Test-Path build) { Remove-Item build -Recurse -Force }
}

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

# Onefile, windowed (no console), name fds-reader
pyinstaller --noconfirm --onefile --windowed --name fds-reader main.py

Write-Host "Done. Output: dist/fds-reader.exe"
