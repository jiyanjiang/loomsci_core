# loomsci_core installer (Windows PowerShell).
param(
  [string]$Package = "",
  [string]$Destination = "$env:USERPROFILE\.loomsci",
  [switch]$NoDeps
)

$ErrorActionPreference = "Stop"
$temp = Join-Path $env:TEMP ("loomsci-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

try {
  if ($Package) {
    if (-not (Test-Path $Package)) { throw "package not found: $Package" }
    Expand-Archive -Path $Package -DestinationPath $temp -Force
    $manifest = Get-ChildItem -Path $temp -Recurse -Filter "pyproject.toml" |
      Select-Object -First 1
    if (-not $manifest) { throw "package root not found" }
    $source = $manifest.DirectoryName
  } else {
    $source = $PSScriptRoot
  }
  if (-not (Test-Path (Join-Path $source "pyproject.toml"))) {
    throw "package root not found: $source"
  }

  foreach ($dir in @("bin", "data", "agents", "packs", "logs", "runtime")) {
    New-Item -ItemType Directory -Path (Join-Path $Destination $dir) -Force | Out-Null
  }

  $venv = Join-Path $Destination "venv"
  $python = Join-Path $venv "Scripts\python.exe"
  if (-not (Test-Path $python)) {
    $versioned = Get-Command "py" -ErrorAction SilentlyContinue
    if ($versioned) {
      & py -3.12 -m venv $venv
    } else {
      & python -m venv $venv
    }
  }
  $python = Join-Path $venv "Scripts\python.exe"

  $newCore = Join-Path $Destination "core.new"
  Remove-Item -Recurse -Force $newCore -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Path $newCore | Out-Null
  $items = @(
    "core", "cli", "presets", "addons", "docs", "scripts",
    "pyproject.toml", "requirements.txt", "VERSION",
    "README.md", "README.zh-CN.md", "LICENSE", "NOTICE",
    "SECURITY.md", "CONTRIBUTING.md", "AGENTS.md",
    "BUILD_INFO.json", "upgrade-manifest.json"
  )
  foreach ($item in $items) {
    $path = Join-Path $source $item
    if (Test-Path $path) {
      Copy-Item -Path $path -Destination $newCore -Recurse -Force
    }
  }

  if (-not $NoDeps) {
    & $python -m pip install --disable-pip-version-check -r (Join-Path $newCore "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "dependency install failed" }
  }

  $core = Join-Path $Destination "core"
  $previous = Join-Path $Destination "core.prev"
  if (Test-Path $core) {
    Remove-Item -Recurse -Force $previous -ErrorAction SilentlyContinue
    Move-Item -Path $core -Destination $previous
  }
  Move-Item -Path $newCore -Destination $core

  $launcher = Join-Path $Destination "bin\loomsci.cmd"
  $lines = @(
    "@echo off",
    "set ""PYTHONPATH=$core""",
    "set ""PYTHONSAFEPATH=1""",
    "set ""LOOMSCI_HOME=$Destination""",
    "`"$python`" -m cli.loomsci %*"
  )
  Set-Content -Path $launcher -Value $lines -Encoding ASCII

  Write-Host "installed: $core"
  Write-Host "launcher:  $launcher"
  Write-Host "next:      $launcher alice init --owner <name>"
  Write-Host "then:      $launcher doctor"
  Write-Host "start:     $launcher up"
} finally {
  Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
}
