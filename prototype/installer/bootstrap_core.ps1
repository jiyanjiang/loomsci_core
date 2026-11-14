# No-Python bootstrap for a signed Core package. Not product code.
param(
  [Parameter(Mandatory=$true)][string]$Package,
  [Parameter(Mandatory=$true)][string]$TargetHome,
  [Parameter(Mandatory=$true)][string]$Trust,
  [Parameter(Mandatory=$true)][string]$Uv,
  [Parameter(Mandatory=$true)][string]$Sha256,
  [string]$PythonDir = ""
)
$ErrorActionPreference = "Stop"
$expected = ((Get-Content $Sha256 -TotalCount 1) -split "\s+")[0].ToLower()
$actual = (Get-FileHash -Algorithm SHA256 $Uv).Hash.ToLower()
if ($expected -ne $actual) { throw "uv_checksum_mismatch" }

$work = "$TargetHome.bootstrap-$PID"
try {
  New-Item -ItemType Directory -Force -Path $work | Out-Null
  if ($PythonDir) {
    $env:UV_PYTHON_INSTALL_DIR = $PythonDir
  } else {
    $persistentPython = Join-Path $TargetHome "runtime\python"
    New-Item -ItemType Directory -Force -Path $persistentPython | Out-Null
    $env:UV_PYTHON_INSTALL_DIR = $persistentPython
    & $Uv python install 3.12 --managed-python --install-dir $env:UV_PYTHON_INSTALL_DIR
    if ($LASTEXITCODE -ne 0) { throw "python_install_failed" }
  }
  & $Uv venv --managed-python --python 3.12 (Join-Path $work "venv")
  if ($LASTEXITCODE -ne 0) { throw "venv_failed" }
  $py = Join-Path $work "venv\Scripts\python.exe"
  & $Uv pip install --python $py cryptography | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "cryptography_install_failed" }
  & $py (Join-Path $PSScriptRoot "install_core.py") `
    --package $Package --home $TargetHome --trust $Trust --uv $Uv
  if ($LASTEXITCODE -ne 0) { throw "install_core_failed" }
} finally {
  Remove-Item -Recurse -Force $work -ErrorAction SilentlyContinue
}
