# uv-less installer prototype. Not product code.
# Usage: .\install.ps1 -TargetHome DIR -Uv PATH -Sha256 FILE [-Offline]
# Requires no uv/python on PATH; uses the explicit uv binary.

param(
  [string]$TargetHome = "$env:USERPROFILE\.loomsci",
  [Parameter(Mandatory=$true)][string]$Uv,
  [Parameter(Mandatory=$true)][string]$Sha256,
  [switch]$Offline
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $Uv)) { throw "uv_missing: $Uv" }
if (-not (Test-Path $Sha256)) { throw "sha256_file_missing: $Sha256" }
$expected = ((Get-Content $Sha256 -TotalCount 1) -split "\s+")[0].ToLower()
$actual = (Get-FileHash -Algorithm SHA256 $Uv).Hash.ToLower()
if ($expected -ne $actual) { throw "uv_checksum_mismatch" }

$runtimeDir = Join-Path $TargetHome "runtime\python"
$venvDir = Join-Path $TargetHome "venv"
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
  format = "loomsci-install/1"
  home = $TargetHome
  python = $py
  python_version = $version
  uv = $uvVersion
  uv_sha256 = $actual
  offline = [bool]$Offline
}
$record | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $TargetHome "install.json")
Write-Output "install: $version"
Write-Output "python:  $py"
Write-Output "uv:      $uvVersion"
