# Minimal uv runtime bootstrap prototype. Not product code.
# Usage: .\bootstrap.ps1 [-Home DIR] [-Uv PATH] [-Offline]

param(
  [string]$TargetHome = "$env:USERPROFILE\.loomsci",
  [string]$Uv = "",
  [switch]$Offline
)

$ErrorActionPreference = "Stop"

if (-not $Uv) {
  $cmd = Get-Command uv -ErrorAction SilentlyContinue
  if ($cmd) { $Uv = $cmd.Source }
}
if (-not $Uv -or -not (Test-Path $Uv)) {
  if ($Offline) { throw "uv_missing: offline mode requires -Uv" }
  throw "uv_missing: production installer must download a pinned uv binary; prototype uses existing uv"
}

$HomeDir = $TargetHome
$runtimeDir = Join-Path $HomeDir "runtime\python"
$venvDir = Join-Path $HomeDir "venv"
New-Item -ItemType Directory -Force -Path $runtimeDir, $venvDir | Out-Null
$env:UV_PYTHON_INSTALL_DIR = $runtimeDir
if ($Offline) { $env:UV_PYTHON_DOWNLOADS = "never" }

& $Uv python install 3.12 --managed-python --install-dir $runtimeDir
if ($LASTEXITCODE -ne 0) { throw "python_install_failed" }
& $Uv venv --allow-existing --managed-python --python 3.12 $venvDir
if ($LASTEXITCODE -ne 0) { throw "venv_create_failed" }

$py = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $py)) { throw "venv_python_missing: $py" }
$version = ((& $py --version) -replace "^Python ", "").Trim()
$uvVersion = ((& $Uv --version) -split " ")[1]
$record = [ordered]@{
  runtime = "python"
  python = $py
  version = $version
  uv = $uvVersion
  home = $HomeDir
  offline = [bool]$Offline
}
$record | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $HomeDir "runtime.json")
Write-Output "runtime: $version"
Write-Output "python:  $py"
Write-Output "uv:      $uvVersion"
