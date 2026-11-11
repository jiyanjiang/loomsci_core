# loomsci_core installer (Windows PowerShell).
param(
  [string]$Package = "",
  [string]$Destination = "$env:USERPROFILE\.loomsci",
  [string]$PythonExe = "",
  [string]$ReleaseBase = "https://raw.githubusercontent.com/jiyanjiang/loomsci_core/main",
  [switch]$FromRelease,
  [switch]$DryRun,
  [switch]$NoDeps
)

$ErrorActionPreference = "Stop"
$temp = Join-Path $env:TEMP ("loomsci-install-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

try {
  if ($FromRelease -and $Package) {
    throw "use either -Package or -FromRelease"
  }
  if ($FromRelease) {
    $manifestUrl = "$($ReleaseBase.TrimEnd('/'))/release-manifest.json"
    $release = Invoke-RestMethod -Uri $manifestUrl
    if ($DryRun) {
      Write-Output "version: $($release.version)"
      Write-Output "url:     $($ReleaseBase.TrimEnd('/'))/releases/$($release.file)"
      Write-Output "sha256:  $($release.sha256)"
      return
    }
    $downloaded = Join-Path $temp "package.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "$($ReleaseBase.TrimEnd('/'))/releases/$($release.file)" -OutFile $downloaded
    $actual = (Get-FileHash -Algorithm SHA256 -Path $downloaded).Hash.ToLower()
    if ($actual -ne $release.sha256.ToLower()) {
      throw "package SHA256 mismatch: expected $($release.sha256), got $actual"
    }
    $Package = $downloaded
  }
  if ($DryRun) {
    Write-Output "package: $Package"
    return
  }
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
    if ($PythonExe) {
      & $PythonExe -m venv $venv
    } elseif (Get-Command "py" -ErrorAction SilentlyContinue) {
      & py -3.12 -m venv $venv
    } elseif (Get-Command "python" -ErrorAction SilentlyContinue) {
      & python -m venv $venv
    } elseif (Get-Command "python3.12" -ErrorAction SilentlyContinue) {
      & python3.12 -m venv $venv
    } else {
      throw "Python 3.12 not found; install Python 3.12 or rerun with -Python <path-to-python.exe>"
    }
  }
  $python = Join-Path $venv "Scripts\python.exe"
  if (-not (Test-Path $python)) {
    throw "virtualenv creation failed: $python"
  }

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
